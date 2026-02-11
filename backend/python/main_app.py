"""
Professional Screen Print Color Separation API - Pro Edition
Advanced algorithms with color adjustment tools and Pantone matching
"""

import uvicorn
import base64
import json
import asyncio
import hashlib
import io
import tempfile
import warnings
warnings.filterwarnings('ignore')

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime
from pathlib import Path

import numpy as np
import cv2
from fastapi import FastAPI, Body, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from scipy.spatial.distance import cdist
from scipy.ndimage import gaussian_filter, median_filter, distance_transform_edt
import colorsys

# Pillow for better image handling
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

# scikit-image for advanced segmentation
from skimage import color, filters, morphology, segmentation, exposure
from skimage.filters import threshold_otsu, threshold_local, sobel, gaussian
from skimage.feature import canny
from skimage.segmentation import felzenszwalb, slic, watershed
from skimage.restoration import denoise_bilateral
from skimage.color import rgb2hed, hed2rgb

# ============ MODELS & ENUMS ============

class SeparationMethod(str, Enum):
    GRADIENT_AWARE = "gradient_aware"
    MEDIAN_CUT = "median_cut"
    WATERSHED = "watershed"
    SIMULATED_PROCESS = "simulated_process"  # Fixed spot colors for dark garments
    OCTREE = "octree"

class ChannelType(str, Enum):
    UNDERBASE = "underbase"
    HIGHLIGHT_WHITE = "highlight_white"
    SPOT_COLOR = "spot_color"
    PROCESS_COLOR = "process_color"
    GRADIENT = "gradient"
    HALFTONE = "halftone"

class InkType(str, Enum):
    PLASTISOL = "plastisol"
    WATER_BASED = "water_based"
    DISCHARGE = "discharge"
    PVC = "pvc"

class FabricType(str, Enum):
    COTTON = "cotton"
    POLYESTER = "polyester"
    BLEND = "blend"
    DARK = "dark"
    LIGHT = "light"

class ColorAdjustment(BaseModel):
    """Color adjustment parameters"""
    brightness: float = Field(0.0, ge=-100, le=100)
    contrast: float = Field(0.0, ge=-100, le=100)
    hue: float = Field(0.0, ge=-180, le=180)
    saturation: float = Field(0.0, ge=-100, le=100)
    lightness: float = Field(0.0, ge=-100, le=100)
    gamma: float = Field(1.0, ge=0.1, le=3.0)
    input_black: int = Field(0, ge=0, le=255)
    input_white: int = Field(255, ge=0, le=255)
    cyan_red: float = Field(0.0, ge=-100, le=100)
    magenta_green: float = Field(0.0, ge=-100, le=100)
    yellow_blue: float = Field(0.0, ge=-100, le=100)
    curves: Optional[List[Tuple[int, int]]] = None  # Control points for curves

class ProcessRequest(BaseModel):
    image_base64: str
    separation_method: SeparationMethod = SeparationMethod.GRADIENT_AWARE
    max_colors: int = Field(8, ge=2, le=20)
    use_underbase: bool = True
    use_highlight_white: bool = False
    softness: float = Field(0.6, ge=0.0, le=1.0)
    ink_type: InkType = InkType.PLASTISOL
    fabric_type: FabricType = FabricType.COTTON
    fabric_color: str = Field("#000000", pattern="^#[0-9a-fA-F]{6}$")
    optimize_ink_usage: bool = True
    halftone_frequency: float = Field(45.0, ge=20.0, le=85.0)
    preserve_details: bool = True
    min_ink_coverage: float = Field(0.02, ge=0.001, le=0.1)
    choke_spread: float = Field(0.5, ge=0.0, le=5.0)
    min_dot: int = Field(5, ge=3, le=10)
    color_adjustment: Optional[ColorAdjustment] = None
    custom_colors: Optional[List[str]] = None  # For manual color selection
    match_pantone: bool = False

class ColorChannel(BaseModel):
    name: str
    color: str  # Hex color
    pantone: Optional[str] = None  # Pantone code if matched
    type: ChannelType
    image: str  # Base64 mask
    opacity: float = 1.0
    blend_mode: str = "normal"
    printable: bool = True
    order: int
    ink_volume: float = Field(1.0, ge=0.5, le=1.5)
    halftone_pattern: Optional[str] = None
    coverage_percent: float = 0.0
    locked: bool = False

class SeparationResult(BaseModel):
    channels: List[ColorChannel]
    preview: Optional[str] = None
    metadata: Dict[str, Any]
    palette: List[str]
    pantone_matches: Optional[List[Dict[str, str]]] = None
    ink_estimate: Dict[str, float]
    separation_quality: float
    recommendations: List[str]
    histogram: Optional[Dict[str, List[int]]] = None

# ============ PANTONE MATCHING SERVICE ============

class PantoneMatchingService:
    """Match colors to Pantone coated library"""
    
    def __init__(self, pantone_json_path='pantone-coated.json'):
        self.pantones = []
        self.pantone_lab = []
        
        try:
            with open(pantone_json_path, 'r') as f:
                self.pantones = json.load(f)
            
            # Pre-convert all Pantone colors to Lab for fast matching
            for p in self.pantones:
                hex_color = p['hex'].lstrip('#')
                rgb = np.array([int(hex_color[i:i+2], 16) for i in (0, 2, 4)])
                lab = color.rgb2lab(rgb.reshape(1, 1, 3) / 255.0)[0, 0]
                self.pantone_lab.append({
                    'pantone': p['pantone'],
                    'hex': p['hex'],
                    'lab': lab
                })
        except FileNotFoundError:
            print("Warning: pantone-coated.json not found. Pantone matching disabled.")
    
    def find_closest_pantone(self, color_lab: np.ndarray, max_distance: float = 20.0) -> Optional[dict]:
        """Find closest Pantone match using Delta E (CIE76)"""
        if not self.pantone_lab:
            return None
        
        min_distance = float('inf')
        closest = None
        
        for p in self.pantone_lab:
            # Calculate Delta E (CIE76 - simple but effective)
            distance = np.sqrt(np.sum((color_lab - p['lab']) ** 2))
            
            if distance < min_distance:
                min_distance = distance
                closest = p
        
        # Only return match if distance is reasonable
        if min_distance <= max_distance:
            return {
                'pantone': closest['pantone'],
                'hex': closest['hex'],
                'distance': float(min_distance)
            }
        
        return None
    
    def match_palette(self, colors_lab: List[np.ndarray]) -> List[Dict[str, Any]]:
        """Match a list of colors to Pantone"""
        matches = []
        for color_lab in colors_lab:
            match = self.find_closest_pantone(color_lab)
            if match:
                matches.append(match)
        return matches

# ============ COLOR ADJUSTMENT ENGINE ============

class ColorAdjustmentEngine:
    """Professional color adjustment tools"""
    
    @staticmethod
    def apply_brightness_contrast(img: np.ndarray, brightness: float, contrast: float) -> np.ndarray:
        """Apply brightness and contrast adjustments"""
        # Normalize to -1 to 1 range
        brightness = brightness / 100.0
        contrast = contrast / 100.0
        
        # Convert to float
        img_float = img.astype(np.float32) / 255.0
        
        # Apply brightness
        img_float = img_float + brightness
        
        # Apply contrast
        factor = (259 * (contrast + 1)) / (259 - contrast)
        img_float = factor * (img_float - 0.5) + 0.5
        
        # Clip and convert back
        img_float = np.clip(img_float * 255, 0, 255).astype(np.uint8)
        return img_float
    
    @staticmethod
    def apply_hsl(img_rgb: np.ndarray, hue: float, saturation: float, lightness: float) -> np.ndarray:
        """Apply HSL adjustments"""
        # Convert to HSV (easier to work with)
        img_hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
        
        # Adjust hue (-180 to 180 degrees)
        img_hsv[:, :, 0] = (img_hsv[:, :, 0] + hue) % 180
        
        # Adjust saturation
        sat_factor = 1.0 + (saturation / 100.0)
        img_hsv[:, :, 1] = np.clip(img_hsv[:, :, 1] * sat_factor, 0, 255)
        
        # Adjust value (lightness)
        light_factor = 1.0 + (lightness / 100.0)
        img_hsv[:, :, 2] = np.clip(img_hsv[:, :, 2] * light_factor, 0, 255)
        
        # Convert back to RGB
        img_hsv = img_hsv.astype(np.uint8)
        img_rgb = cv2.cvtColor(img_hsv, cv2.COLOR_HSV2RGB)
        return img_rgb
    
    @staticmethod
    def apply_gamma(img: np.ndarray, gamma: float) -> np.ndarray:
        """Apply gamma correction"""
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 
                         for i in range(256)]).astype(np.uint8)
        return cv2.LUT(img, table)
    
    @staticmethod
    def apply_levels(img: np.ndarray, input_black: int, input_white: int, gamma: float) -> np.ndarray:
        """Apply levels adjustment (like Photoshop)"""
        # Normalize input range
        img_float = img.astype(np.float32)
        
        # Input levels
        img_float = np.clip((img_float - input_black) / (input_white - input_black), 0, 1)
        
        # Gamma
        img_float = np.power(img_float, 1.0 / gamma)
        
        # Scale back to 0-255
        img_float = (img_float * 255).astype(np.uint8)
        return img_float
    
    @staticmethod
    def apply_color_balance(img_rgb: np.ndarray, cyan_red: float, magenta_green: float, yellow_blue: float) -> np.ndarray:
        """Apply color balance adjustments"""
        img_float = img_rgb.astype(np.float32)
        
        # Red channel adjustment
        img_float[:, :, 0] += cyan_red * 2.55  # -100 to 100 -> -255 to 255
        
        # Green channel adjustment
        img_float[:, :, 1] += magenta_green * 2.55
        
        # Blue channel adjustment
        img_float[:, :, 2] += yellow_blue * 2.55
        
        return np.clip(img_float, 0, 255).astype(np.uint8)
    
    @staticmethod
    def apply_curves(img: np.ndarray, control_points: List[Tuple[int, int]]) -> np.ndarray:
        """Apply curves adjustment using control points"""
        if not control_points or len(control_points) < 2:
            return img
        
        # Sort control points by x value
        control_points = sorted(control_points, key=lambda p: p[0])
        
        # Create lookup table using linear interpolation
        lut = np.zeros(256, dtype=np.uint8)
        
        for i in range(256):
            # Find surrounding control points
            for j in range(len(control_points) - 1):
                x1, y1 = control_points[j]
                x2, y2 = control_points[j + 1]
                
                if x1 <= i <= x2:
                    # Linear interpolation
                    t = (i - x1) / (x2 - x1) if x2 != x1 else 0
                    lut[i] = int(y1 + t * (y2 - y1))
                    break
        
        return cv2.LUT(img, lut)
    
    @staticmethod
    def calculate_histogram(img: np.ndarray) -> Dict[str, List[int]]:
        """Calculate RGB histogram"""
        histogram = {
            'red': cv2.calcHist([img], [0], None, [256], [0, 256]).flatten().tolist(),
            'green': cv2.calcHist([img], [1], None, [256], [0, 256]).flatten().tolist(),
            'blue': cv2.calcHist([img], [2], None, [256], [0, 256]).flatten().tolist()
        }
        return histogram
    
    def apply_all_adjustments(self, img_rgb: np.ndarray, adjustments: ColorAdjustment) -> np.ndarray:
        """Apply all color adjustments in order"""
        img = img_rgb.copy()
        
        # 1. Levels
        if adjustments.input_black != 0 or adjustments.input_white != 255 or adjustments.gamma != 1.0:
            img = self.apply_levels(img, adjustments.input_black, adjustments.input_white, adjustments.gamma)
        
        # 2. Curves
        if adjustments.curves:
            img = self.apply_curves(img, adjustments.curves)
        
        # 3. Brightness/Contrast
        if adjustments.brightness != 0 or adjustments.contrast != 0:
            img = self.apply_brightness_contrast(img, adjustments.brightness, adjustments.contrast)
        
        # 4. HSL
        if adjustments.hue != 0 or adjustments.saturation != 0 or adjustments.lightness != 0:
            img = self.apply_hsl(img, adjustments.hue, adjustments.saturation, adjustments.lightness)
        
        # 5. Color Balance
        if adjustments.cyan_red != 0 or adjustments.magenta_green != 0 or adjustments.yellow_blue != 0:
            img = self.apply_color_balance(img, adjustments.cyan_red, adjustments.magenta_green, adjustments.yellow_blue)
        
        return img

# ============ ADVANCED COLOR SEPARATION ALGORITHMS ============

class ColorSeparationAlgorithms:
    """Advanced color separation algorithms optimized for screen printing"""
    
    @staticmethod
    def dominant_colors_watershed(img_rgb: np.ndarray, num_colors: int = 8) -> List[np.ndarray]:
        """Use watershed segmentation for natural color boundaries."""
        img_lab = color.rgb2lab(img_rgb / 255.0)
        gradient = sobel(img_lab[:, :, 0])
        
        from skimage.feature import peak_local_max
        coordinates = peak_local_max(-gradient, min_distance=20, num_peaks=num_colors*3)
        
        markers = np.zeros_like(gradient, dtype=np.uint8)
        for i, (y, x) in enumerate(coordinates[:num_colors]):
            markers[y, x] = i + 1
        
        labels = watershed(gradient, markers)
        
        colors_lab = []
        for label in range(1, np.max(labels) + 1):
            mask = labels == label
            if np.sum(mask) > 100:
                region_color = np.mean(img_lab[mask], axis=0)
                colors_lab.append(region_color)
        
        return colors_lab[:num_colors]
    
    @staticmethod
    def color_quantization_median_cut(img_rgb: np.ndarray, num_colors: int = 8) -> List[np.ndarray]:
        """Median cut algorithm - preserves color relationships."""
        pixels = img_rgb.reshape(-1, 3).astype(np.float32)
        
        def median_cut(pixels, depth=0, max_depth=4):
            if depth >= max_depth or len(pixels) <= 1:
                if len(pixels) > 0:
                    return [np.mean(pixels, axis=0)]
                return []
            
            ranges = np.ptp(pixels, axis=0)
            channel = np.argmax(ranges)
            pixels = pixels[pixels[:, channel].argsort()]
            median_idx = len(pixels) // 2
            
            colors1 = median_cut(pixels[:median_idx], depth + 1, max_depth)
            colors2 = median_cut(pixels[median_idx:], depth + 1, max_depth)
            
            return colors1 + colors2
        
        colors_rgb = median_cut(pixels, max_depth=int(np.log2(num_colors)))
        
        colors_lab = []
        for rgb in colors_rgb[:num_colors]:
            lab = color.rgb2lab(rgb.reshape(1, 1, 3) / 255.0)[0, 0]
            colors_lab.append(lab)
        
        return colors_lab
    
    @staticmethod
    def octree_color_quantization(img_rgb: np.ndarray, num_colors: int = 8) -> List[np.ndarray]:
        """Octree color quantization - preserves color gradients."""
        from sklearn.preprocessing import KBinsDiscretizer
        
        pixels = img_rgb.reshape(-1, 3)
        
        if len(pixels) > 10000:
            indices = np.random.choice(len(pixels), 10000, replace=False)
            sample_pixels = pixels[indices]
        else:
            sample_pixels = pixels
        
        discretizer = KBinsDiscretizer(n_bins=num_colors, encode='ordinal', strategy='quantile')
        
        try:
            discretized = discretizer.fit_transform(sample_pixels)
            unique_colors = []
            
            for i in range(num_colors):
                mask = discretized[:, 0] == i
                if np.any(mask):
                    bin_pixels = sample_pixels[mask]
                    avg_color = np.mean(bin_pixels, axis=0)
                    unique_colors.append(avg_color)
            
            colors_lab = []
            for rgb in unique_colors[:num_colors]:
                lab = color.rgb2lab(rgb.reshape(1, 1, 3) / 255.0)[0, 0]
                colors_lab.append(lab)
            
            return colors_lab
        except:
            return ColorSeparationAlgorithms.color_quantization_median_cut(img_rgb, num_colors)
    
    @staticmethod
    def simulated_process_separation(img_rgb: np.ndarray) -> List[np.ndarray]:
        """
        Simulated process color separation - NOT CMYK!
        Fixed palette of 9-12 spot colors that simulate CMYK for dark/midtone garments.
        This is index separation with a carefully chosen palette.
        """
        # Standard simulated process palette (in Lab color space)
        # These spot colors blend optically to simulate full color on dark garments
        simulated_process_palette = [
            np.array([25, 0, 0]),      # Rich Black
            np.array([35, 50, -60]),   # Process Blue (cool)
            np.array([55, -35, -45]),  # Process Cyan
            np.array([70, -40, 70]),   # Process Green
            np.array([85, -10, 85]),   # Process Yellow
            np.array([65, 60, 50]),    # Process Orange
            np.array([50, 70, -5]),    # Process Magenta
            np.array([45, 65, 30]),    # Process Red
            np.array([60, 20, -30]),   # Process Purple/Violet
            np.array([75, -15, 25]),   # Light Yellow-Green
            np.array([40, 30, 40]),    # Warm Red
        ]
        
        return simulated_process_palette
    
    @staticmethod
    def gradient_aware_separation(img_rgb: np.ndarray, num_colors: int = 8) -> List[np.ndarray]:
        """Separation that preserves gradients using edge-aware filtering."""
        img_smoothed = cv2.bilateralFilter(img_rgb, 9, 75, 75)
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        
        kernel = np.ones((3, 3), np.uint8)
        gradient_mask = cv2.dilate(edges, kernel, iterations=1)
        
        gradient_regions = gradient_mask > 0
        flat_regions = ~gradient_regions
        
        colors_lab = []
        
        if np.any(flat_regions):
            flat_pixels = img_smoothed[flat_regions]
            if len(flat_pixels) > 100:
                flat_colors = ColorSeparationAlgorithms.color_quantization_median_cut(
                    img_smoothed, max(2, num_colors // 2)
                )
                colors_lab.extend(flat_colors)
        
        if np.any(gradient_regions) and len(colors_lab) < num_colors:
            from sklearn.cluster import MeanShift, estimate_bandwidth
            
            gradient_pixels = img_smoothed[gradient_regions]
            if len(gradient_pixels) > 100:
                if len(gradient_pixels) > 1000:
                    indices = np.random.choice(len(gradient_pixels), 1000, replace=False)
                    sample_pixels = gradient_pixels[indices]
                else:
                    sample_pixels = gradient_pixels
                
                bandwidth = estimate_bandwidth(sample_pixels, quantile=0.3)
                if bandwidth > 0:
                    ms = MeanShift(bandwidth=bandwidth, bin_seeding=True)
                    ms.fit(sample_pixels)
                    
                    for center in ms.cluster_centers_:
                        if len(colors_lab) >= num_colors:
                            break
                        lab = color.rgb2lab(center.reshape(1, 1, 3) / 255.0)[0, 0]
                        colors_lab.append(lab)
        
        if len(colors_lab) < num_colors:
            additional = ColorSeparationAlgorithms.color_quantization_median_cut(
                img_smoothed, num_colors - len(colors_lab)
            )
            colors_lab.extend(additional)
        
        unique_colors = []
        for color_lab in colors_lab:
            if not any(np.linalg.norm(color_lab - uc) < 20 for uc in unique_colors):
                unique_colors.append(color_lab)
        
        return unique_colors[:num_colors]

# ============ IMAGE PROCESSING UTILITIES ============

class ImageProcessor:
    """Image processing utilities for screen printing"""
    
    @staticmethod
    def base64_to_cv2(base64_string: str) -> np.ndarray:
        """Convert base64 to OpenCV image with alpha handling."""
        try:
            if "base64," in base64_string:
                base64_string = base64_string.split("base64,")[1]
            
            img_data = base64.b64decode(base64_string)
            pil_img = Image.open(io.BytesIO(img_data))
            
            if pil_img.mode == 'RGBA':
                background = Image.new('RGB', pil_img.size, (255, 255, 255))
                background.paste(pil_img, mask=pil_img.split()[3])
                pil_img = background
            elif pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            
            img_np = np.array(pil_img)
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            return img_bgr
        except Exception as e:
            raise ValueError(f"Image decode failed: {str(e)}")
    
    @staticmethod
    def cv2_to_base64(img: np.ndarray, format: str = 'png') -> str:
        """Convert OpenCV image to base64."""
        if len(img.shape) == 2:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        pil_img = Image.fromarray(img_rgb)
        buffer = io.BytesIO()
        
        if format == 'png':
            pil_img.save(buffer, format='PNG', optimize=True)
            mime_type = 'image/png'
        else:
            pil_img.save(buffer, format='JPEG', quality=95, optimize=True)
            mime_type = 'image/jpeg'
        
        return f"data:{mime_type};base64," + base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    @staticmethod
    def rgb_to_hex(rgb: np.ndarray) -> str:
        """Convert RGB array to hex string."""
        return f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}"
    
    @staticmethod
    def calculate_ink_spread(ink_type: InkType, fabric_type: FabricType) -> float:
        """Calculate ink spread factor for different ink/fabric combos."""
        spread_factors = {
            InkType.PLASTISOL: {
                FabricType.COTTON: 1.0,
                FabricType.POLYESTER: 0.8,
                FabricType.BLEND: 0.9,
                FabricType.DARK: 1.0,
                FabricType.LIGHT: 0.9
            },
            InkType.WATER_BASED: {
                FabricType.COTTON: 1.2,
                FabricType.POLYESTER: 0.7,
                FabricType.BLEND: 0.95,
                FabricType.DARK: 1.1,
                FabricType.LIGHT: 0.9
            },
            InkType.DISCHARGE: {
                FabricType.COTTON: 1.3,
                FabricType.POLYESTER: 0.6,
                FabricType.BLEND: 0.85,
                FabricType.DARK: 1.2,
                FabricType.LIGHT: 0.8
            }
        }
        
        return spread_factors.get(ink_type, {}).get(fabric_type, 1.0)
    
    @staticmethod
    def create_underbase_mask(img_rgb: np.ndarray, fabric_color: str = "#000000") -> np.ndarray:
        """Create optimized underbase mask."""
        lab = color.rgb2lab(img_rgb / 255.0)
        l_channel = (lab[:, :, 0] / 100 * 255).astype(np.uint8)
        
        underbase = cv2.adaptiveThreshold(
            l_channel, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        underbase = morphology.remove_small_objects(underbase.astype(bool), min_size=100)
        underbase = morphology.remove_small_holes(underbase, area_threshold=100)
        underbase = underbase.astype(np.uint8) * 255
        
        underbase = cv2.GaussianBlur(underbase, (3, 3), 0.5)
        
        return underbase
    
    @staticmethod
    def create_halftone_pattern(mask: np.ndarray, frequency: float = 45.0) -> np.ndarray:
        """Create halftone pattern for gradient printing."""
        h, w = mask.shape
        mask_norm = mask.astype(np.float32) / 255.0
        
        x = np.arange(w)
        y = np.arange(h)
        X, Y = np.meshgrid(x, y)
        
        Xr = X * 0.7071 - Y * 0.7071
        period = max(h, w) / frequency
        pattern = 0.5 + 0.5 * np.sin(2 * np.pi * Xr / period)
        
        halftone = np.where(mask_norm > pattern, 255, 0).astype(np.uint8)
        halftone = cv2.GaussianBlur(halftone, (3, 3), 0.5)
        
        return halftone
    
    @staticmethod
    def apply_choke_spread(mask: np.ndarray, amount: float) -> np.ndarray:
        """Apply choke (negative) or spread (positive) to mask."""
        kernel_size = int(abs(amount))
        if kernel_size == 0:
            return mask
        
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        
        if amount > 0:
            # Spread (dilate)
            return cv2.dilate(mask, kernel, iterations=1)
        else:
            # Choke (erode)
            return cv2.erode(mask, kernel, iterations=1)

# ============ SEPARATION ENGINE ============

class ProfessionalSeparationEngine:
    """Main separation engine using advanced algorithms"""
    
    def __init__(self):
        self.algorithms = ColorSeparationAlgorithms()
        self.processor = ImageProcessor()
        self.color_adjuster = ColorAdjustmentEngine()
        self.pantone_matcher = PantoneMatchingService()
    
    async def separate_image(self, request: ProcessRequest) -> SeparationResult:
        """Main separation function with all pro features."""
        try:
            # Decode image
            img_bgr = self.processor.base64_to_cv2(request.image_base64)
            
            # Resize for processing
            h, w = img_bgr.shape[:2]
            max_dim = 1200
            if h > max_dim or w > max_dim:
                scale = max_dim / max(h, w)
                new_size = (int(w * scale), int(h * scale))
                img_bgr = cv2.resize(img_bgr, new_size, interpolation=cv2.INTER_AREA)
            
            # Convert to RGB
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            
            # Apply color adjustments if provided
            if request.color_adjustment:
                img_rgb = self.color_adjuster.apply_all_adjustments(img_rgb, request.color_adjustment)
            
            # Calculate histogram for metadata
            histogram = self.color_adjuster.calculate_histogram(img_rgb)
            
            channels = []
            order_counter = 0
            
            # Add underbase if needed
            if request.use_underbase and request.fabric_color != "#FFFFFF":
                underbase_mask = self.processor.create_underbase_mask(img_rgb, request.fabric_color)
                
                spread_factor = self.processor.calculate_ink_spread(request.ink_type, request.fabric_type)
                if spread_factor > 1.0:
                    kernel_size = int(spread_factor)
                    kernel = np.ones((kernel_size, kernel_size), np.uint8)
                    underbase_mask = cv2.dilate(underbase_mask, kernel, iterations=1)
                
                # Apply choke/spread
                underbase_mask = self.processor.apply_choke_spread(underbase_mask, request.choke_spread)
                
                coverage = np.sum(underbase_mask > 10) / (underbase_mask.shape[0] * underbase_mask.shape[1]) * 100
                
                channels.append(ColorChannel(
                    name="Underbase White",
                    color="#FFFFFF",
                    type=ChannelType.UNDERBASE,
                    image=self.processor.cv2_to_base64(underbase_mask),
                    opacity=1.0,
                    blend_mode="normal",
                    order=order_counter,
                    printable=True,
                    ink_volume=1.0 if request.ink_type != InkType.DISCHARGE else 0.8,
                    coverage_percent=round(coverage, 2)
                ))
                order_counter += 1
            
            # Get dominant colors based on method or custom colors
            if request.custom_colors:
                # MANUAL COLOR SELECTION
                colors_lab = []
                for hex_color in request.custom_colors:
                    rgb = np.array([int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)])
                    lab = color.rgb2lab(rgb.reshape(1, 1, 3) / 255.0)[0, 0]
                    colors_lab.append(lab)
            else:
                # AUTOMATIC COLOR EXTRACTION
                if request.separation_method == SeparationMethod.WATERSHED:
                    colors_lab = self.algorithms.dominant_colors_watershed(img_rgb, request.max_colors)
                elif request.separation_method == SeparationMethod.MEDIAN_CUT:
                    colors_lab = self.algorithms.color_quantization_median_cut(img_rgb, request.max_colors)
                elif request.separation_method == SeparationMethod.OCTREE:
                    colors_lab = self.algorithms.octree_color_quantization(img_rgb, request.max_colors)
                elif request.separation_method == SeparationMethod.SIMULATED_PROCESS:
                    colors_lab = self.algorithms.simulated_process_separation(img_rgb)
                else:  # GRADIENT_AWARE (default)
                    colors_lab = self.algorithms.gradient_aware_separation(img_rgb, request.max_colors)
            
            # Match to Pantone if requested
            pantone_matches = []
            if request.match_pantone:
                pantone_matches = self.pantone_matcher.match_palette(colors_lab)
            
            # Create masks for each color
            for i, color_lab in enumerate(colors_lab):
                # Convert to RGB for display
                color_rgb = (color.lab2rgb(color_lab.reshape(1, 1, 3)) * 255).astype(np.uint8)[0, 0]
                
                # Create mask
                mask = self.create_color_mask(img_rgb, color_lab, request.softness)
                
                # Apply choke/spread
                mask = self.processor.apply_choke_spread(mask, request.choke_spread)
                
                # Apply minimum dot
                if request.min_dot > 0:
                    mask = np.where(mask < request.min_dot * 2.55, 0, mask).astype(np.uint8)
                
                # Calculate coverage
                coverage = np.sum(mask > 10) / (mask.shape[0] * mask.shape[1]) * 100
                
                # Apply minimum coverage threshold
                if coverage < request.min_ink_coverage * 100:
                    continue
                
                # Convert to hex
                color_hex = self.processor.rgb_to_hex(color_rgb)
                
                # Get Pantone match if available
                pantone_code = None
                if request.match_pantone and i < len(pantone_matches):
                    pantone_code = pantone_matches[i]['pantone']
                    color_hex = pantone_matches[i]['hex']  # Use Pantone hex instead
                
                # Apply halftone for gradient methods
                halftone_pattern = None
                if request.separation_method in [SeparationMethod.GRADIENT_AWARE, SeparationMethod.OCTREE]:
                    halftone = self.processor.create_halftone_pattern(mask, request.halftone_frequency)
                    halftone_pattern = self.processor.cv2_to_base64(halftone)
                
                # Determine channel type
                channel_type = ChannelType.GRADIENT if request.softness > 0.3 else ChannelType.SPOT_COLOR
                if request.separation_method == SeparationMethod.SIMULATED_PROCESS:
                    channel_type = ChannelType.PROCESS_COLOR
                
                channel_name = f"PMS {pantone_code}" if pantone_code else f"Color {i+1}"
                
                channels.append(ColorChannel(
                    name=channel_name,
                    color=color_hex,
                    pantone=pantone_code,
                    type=channel_type,
                    image=self.processor.cv2_to_base64(mask),
                    opacity=1.0,
                    blend_mode="normal",
                    order=order_counter,
                    printable=True,
                    ink_volume=1.0,
                    halftone_pattern=halftone_pattern,
                    coverage_percent=round(coverage, 2),
                    locked=False
                ))
                order_counter += 1
            
            # Create preview
            preview = self.create_preview_composite(img_rgb, channels, request.fabric_color)
            preview_base64 = self.processor.cv2_to_base64(preview)
            
            # Calculate results
            ink_estimate = self.calculate_ink_estimate(channels, img_rgb.shape[:2])
            quality_score = self.calculate_separation_quality(channels, img_rgb)
            recommendations = self.generate_recommendations(channels, request, ink_estimate, quality_score)
            
            # Extract palette
            palette = list(set([ch.color for ch in channels if ch.type not in [
                ChannelType.UNDERBASE, ChannelType.HIGHLIGHT_WHITE
            ]]))
            
            # Create metadata
            metadata = {
                "method": request.separation_method.value,
                "total_channels": len(channels),
                "color_channels": len([ch for ch in channels if ch.type in [
                    ChannelType.SPOT_COLOR, ChannelType.PROCESS_COLOR, 
                    ChannelType.GRADIENT, ChannelType.HALFTONE
                ]]),
                "white_channels": len([ch for ch in channels if ch.type in [
                    ChannelType.UNDERBASE, ChannelType.HIGHLIGHT_WHITE
                ]]),
                "image_dimensions": f"{h}x{w}",
                "ink_type": request.ink_type.value,
                "fabric_type": request.fabric_type.value,
                "choke_spread": request.choke_spread,
                "min_dot": request.min_dot,
                "pantone_matched": request.match_pantone,
                "timestamp": datetime.now().isoformat()
            }
            
            return SeparationResult(
                channels=channels,
                preview=preview_base64,
                metadata=metadata,
                palette=palette,
                pantone_matches=pantone_matches if request.match_pantone else None,
                ink_estimate=ink_estimate,
                separation_quality=quality_score,
                recommendations=recommendations,
                histogram=histogram
            )
            
        except Exception as e:
            raise Exception(f"Separation failed: {str(e)}")
    
    def create_color_mask(self, img_rgb: np.ndarray, target_lab: np.ndarray, 
                         softness: float = 0.5) -> np.ndarray:
        """Create color mask with smooth transitions."""
        img_lab = color.rgb2lab(img_rgb / 255.0)
        dist = np.sqrt(np.sum((img_lab - target_lab) ** 2, axis=2))
        
        max_dist = np.max(dist) if np.max(dist) > 0 else 1
        dist_norm = dist / max_dist
        
        if softness > 0.7:
            mask = 1 / (1 + np.exp(12 * (dist_norm - 0.4)))
        elif softness > 0.3:
            t = np.clip(1 - dist_norm, 0, 1)
            mask = t * t * (3 - 2 * t)
        else:
            mask = np.where(dist_norm < 0.5, 1, 0)
        
        mask = (mask * 255).astype(np.uint8)
        mask = cv2.bilateralFilter(mask, 9, 75, 75)
        
        return mask
    
    def create_preview_composite(self, img_rgb: np.ndarray, channels: List[ColorChannel], 
                                fabric_color: str = "#000000") -> np.ndarray:
        """Create preview composite image."""
        h, w = img_rgb.shape[:2]
        preview = np.ones((h, w, 3), dtype=np.float32)
        
        # Set fabric color
        hex_color = fabric_color.lstrip('#')
        fabric_r = int(hex_color[0:2], 16) / 255.0
        fabric_g = int(hex_color[2:4], 16) / 255.0
        fabric_b = int(hex_color[4:6], 16) / 255.0
        
        preview[:,:,0] = fabric_r
        preview[:,:,1] = fabric_g
        preview[:,:,2] = fabric_b
        
        sorted_channels = sorted(channels, key=lambda x: x.order)
        
        for channel in sorted_channels:
            if not channel.printable:
                continue
            
            mask_base64 = channel.image.split(",")[1]
            mask_data = base64.b64decode(mask_base64)
            mask_np = np.frombuffer(mask_data, np.uint8)
            mask = cv2.imdecode(mask_np, cv2.IMREAD_GRAYSCALE)
            
            if mask is None or mask.shape[:2] != (h, w):
                continue
            
            mask_norm = mask.astype(np.float32) / 255.0 * channel.opacity
            
            hex_color = channel.color.lstrip('#')
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            
            # Apply blend mode
            if channel.blend_mode == "multiply":
                preview[:,:,0] *= (1 - mask_norm + r * mask_norm)
                preview[:,:,1] *= (1 - mask_norm + g * mask_norm)
                preview[:,:,2] *= (1 - mask_norm + b * mask_norm)
            else:  # normal
                for c, color_val in enumerate([r, g, b]):
                    preview[:,:,c] = preview[:,:,c] * (1 - mask_norm) + color_val * mask_norm
        
        preview = np.clip(preview * 255, 0, 255).astype(np.uint8)
        return preview
    
    def calculate_ink_estimate(self, channels: List[ColorChannel], image_size: Tuple[int, int]) -> Dict[str, float]:
        """Calculate ink usage estimates."""
        h, w = image_size
        total_pixels = h * w
        
        estimates = {
            "total_coverage": 0.0,
            "white_ink_ml": 0.0,
            "colored_ink_ml": 0.0,
            "estimated_cost": 0.0
        }
        
        for channel in channels:
            if not channel.printable:
                continue
            
            coverage = channel.coverage_percent / 100
            ink_volume_ml = coverage * channel.ink_volume * 100
            
            if channel.type == ChannelType.UNDERBASE:
                estimates["white_ink_ml"] += ink_volume_ml
            elif channel.type == ChannelType.HIGHLIGHT_WHITE:
                estimates["white_ink_ml"] += ink_volume_ml * 0.5
            else:
                estimates["colored_ink_ml"] += ink_volume_ml
            
            estimates["total_coverage"] += coverage
        
        estimates["total_coverage"] = round(estimates["total_coverage"] * 100, 1)
        estimates["white_ink_ml"] = round(estimates["white_ink_ml"], 1)
        estimates["colored_ink_ml"] = round(estimates["colored_ink_ml"], 1)
        estimates["estimated_cost"] = round(
            estimates["white_ink_ml"] * 0.10 + estimates["colored_ink_ml"] * 0.15, 2
        )
        
        return estimates
    
    def calculate_separation_quality(self, channels: List[ColorChannel], original_img: np.ndarray) -> float:
        """Calculate separation quality score (0-100)."""
        if not channels:
            return 0.0
        
        quality_factors = []
        
        # Coverage factor
        total_coverage = sum(ch.coverage_percent for ch in channels if ch.printable and ch.type not in [ChannelType.UNDERBASE, ChannelType.HIGHLIGHT_WHITE])
        coverage_score = min(100, total_coverage)
        quality_factors.append(coverage_score * 0.4)
        
        # Channel count factor
        color_channels = [c for c in channels if c.type in [
            ChannelType.SPOT_COLOR, ChannelType.PROCESS_COLOR, 
            ChannelType.GRADIENT, ChannelType.HALFTONE
        ]]
        
        channel_score = max(0, 100 - abs(len(color_channels) - 6) * 10)
        quality_factors.append(channel_score * 0.3)
        
        # Ink efficiency factor
        estimates = self.calculate_ink_estimate(channels, original_img.shape[:2])
        efficiency_score = max(0, 100 - estimates["total_coverage"] * 0.5)
        quality_factors.append(efficiency_score * 0.3)
        
        return round(sum(quality_factors), 1)
    
    def generate_recommendations(self, channels: List[ColorChannel], request: ProcessRequest,
                                ink_estimate: Dict[str, float], quality_score: float) -> List[str]:
        """Generate professional recommendations."""
        recommendations = []
        
        color_channels = [c for c in channels if c.type in [
            ChannelType.SPOT_COLOR, ChannelType.PROCESS_COLOR, 
            ChannelType.GRADIENT, ChannelType.HALFTONE
        ]]
        
        if len(color_channels) > 8:
            recommendations.append(f"Consider reducing colors to 6-8 for better printability (currently {len(color_channels)})")
        elif len(color_channels) < 4:
            recommendations.append(f"Consider increasing colors for better detail (currently {len(color_channels)})")
        
        if ink_estimate["total_coverage"] > 250:
            recommendations.append("High ink coverage may cause stiff prints. Consider reducing colors or using discharge ink.")
        elif ink_estimate["total_coverage"] < 100:
            recommendations.append("Low ink coverage - good for soft-hand prints")
        
        if request.separation_method == SeparationMethod.SIMULATED_PROCESS:
            recommendations.append("Simulated process uses fixed spot colors - ideal for full-color images on dark garments")
        elif request.separation_method == SeparationMethod.GRADIENT_AWARE:
            recommendations.append("Gradient-aware separation is optimal for designs with smooth transitions")
        
        if quality_score < 70:
            recommendations.append(f"Quality score is low ({quality_score}/100). Try adjusting softness or color count.")
        elif quality_score > 90:
            recommendations.append(f"Excellent separation quality ({quality_score}/100)")
        
        if request.match_pantone:
            recommendations.append("Colors matched to Pantone library for accurate ink specification")
        
        if request.choke_spread != 0:
            recommendations.append(f"Trapping applied: {abs(request.choke_spread)}pt {'spread' if request.choke_spread > 0 else 'choke'}")
        
        return recommendations[:7]

# ============ FASTAPI APP ============

app = FastAPI(
    title="Professional Screen Print Separation API - Pro Edition",
    description="Advanced color separation with adjustment tools and Pantone matching",
    version="3.0"
)

engine = ProfessionalSeparationEngine()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ ENDPOINTS ============

@app.get("/")
async def root():
    return {
        "name": "Professional Screen Print Separation - Pro Edition",
        "version": "3.0",
        "features": [
            "Color adjustment tools (curves, levels, HSL, color balance)",
            "Pantone color matching",
            "Manual color selection",
            "Simulated process separation (9-12 spot colors for dark garments)",
            "Choke/spread trapping",
            "Minimum dot control",
            "Histogram analysis"
        ],
        "algorithms": [
            "gradient_aware - Best for gradients and smooth transitions",
            "median_cut - Preserves color relationships",
            "watershed - Natural color boundaries",
            "simulated_process - Fixed spot color palette for dark garments",
            "octree - Gradient-preserving quantization"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "engine": "ProfessionalSeparationEngine",
        "pantone_loaded": len(engine.pantone_matcher.pantones) > 0
    }

@app.post("/process", response_model=SeparationResult)
async def process_image(request: ProcessRequest):
    """Main separation endpoint with all pro features."""
    try:
        result = await engine.separate_image(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/adjust-colors")
async def adjust_colors(
    image_base64: str = Body(...),
    adjustments: ColorAdjustment = Body(...)
):
    """Apply color adjustments to image and return adjusted image with histogram."""
    try:
        img_bgr = engine.processor.base64_to_cv2(image_base64)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        
        adjusted_rgb = engine.color_adjuster.apply_all_adjustments(img_rgb, adjustments)
        histogram = engine.color_adjuster.calculate_histogram(adjusted_rgb)
        
        adjusted_base64 = engine.processor.cv2_to_base64(cv2.cvtColor(adjusted_rgb, cv2.COLOR_RGB2BGR))
        
        return {
            "adjusted_image": adjusted_base64,
            "histogram": histogram
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/match-pantone")
async def match_pantone(
    colors_hex: List[str] = Body(...)
):
    """Match hex colors to Pantone library."""
    try:
        colors_lab = []
        for hex_color in colors_hex:
            rgb = np.array([int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)])
            lab = color.rgb2lab(rgb.reshape(1, 1, 3) / 255.0)[0, 0]
            colors_lab.append(lab)
        
        matches = engine.pantone_matcher.match_palette(colors_lab)
        
        return {
            "matches": matches,
            "count": len(matches)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_image(image_base64: str = Body(...)):
    """Analyze image and suggest best separation method."""
    try:
        img_bgr = engine.processor.base64_to_cv2(image_base64)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (img_rgb.shape[0] * img_rgb.shape[1])
        unique_colors = len(np.unique(img_rgb.reshape(-1, 3), axis=0))
        
        # Calculate histogram
        histogram = engine.color_adjuster.calculate_histogram(img_rgb)
        
        if edge_density > 0.3:
            suggested_method = SeparationMethod.GRADIENT_AWARE
        elif unique_colors > 100:
            suggested_method = SeparationMethod.SIMULATED_PROCESS
        else:
            suggested_method = SeparationMethod.MEDIAN_CUT
        
        if unique_colors > 500:
            suggested_colors = 8
        elif unique_colors > 100:
            suggested_colors = 6
        else:
            suggested_colors = 4
        
        return {
            "edge_density": round(edge_density * 100, 1),
            "unique_colors": unique_colors,
            "suggested_method": suggested_method.value,
            "suggested_colors": suggested_colors,
            "image_size": f"{img_rgb.shape[1]}x{img_rgb.shape[0]}",
            "histogram": histogram
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/compare")
async def compare_methods(
    image_base64: str = Body(...),
    methods: List[str] = Body(["gradient_aware", "median_cut", "simulated_process"])
):
    """Compare different separation methods."""
    try:
        results = []
        
        for method_name in methods:
            try:
                method = SeparationMethod(method_name)
                request = ProcessRequest(
                    image_base64=image_base64,
                    separation_method=method,
                    max_colors=6,
                    use_underbase=True,
                    fabric_color="#000000"
                )
                
                result = await engine.separate_image(request)
                
                results.append({
                    "method": method.value,
                    "channel_count": len(result.channels),
                    "quality_score": result.separation_quality,
                    "ink_estimate": result.ink_estimate,
                    "recommendations": result.recommendations[:2]
                })
            except:
                continue
        
        results.sort(key=lambda x: x["quality_score"], reverse=True)
        
        return {
            "comparison": results,
            "best_method": results[0]["method"] if results else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
