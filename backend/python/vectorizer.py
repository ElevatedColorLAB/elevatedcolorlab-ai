# vectorizer.py
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
import io
import base64
import numpy as np
import cv2

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class VectorizeRequest(BaseModel):
    image_b64: str
    max_colors: int = 6
    generate_underbase: bool = True

def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])

@app.post("/vectorize")
async def vectorize_image(request: VectorizeRequest):
    try:
        if "base64," in request.image_b64:
            img_str = request.image_b64.split("base64,")[1]
        else:
            img_str = request.image_b64
            
        image_data = base64.b64decode(img_str)
        original_img = Image.open(io.BytesIO(image_data)).convert("RGBA")
        
        # --- FIX: Convert to RGB for Quantization to avoid Octree Error ---
        rgb_img = original_img.convert("RGB")
        
        # Quantize to reduce colors to solid blocks
        quantized = rgb_img.quantize(colors=request.max_colors, method=Image.Quantize.MAXCOVERAGE).convert("RGB")
        
        # Re-apply alpha channel from original if needed, or treat white as transparent
        # For vectorization, we usually trace shapes.
        
        width, height = quantized.size
        svg_groups = []
        
        # Get colors
        colors = quantized.getcolors(width * height)
        if not colors:
            # Fallback if getcolors returns None (too many colors)
            quantized = quantized.quantize(colors=request.max_colors)
            colors = quantized.getcolors(width * height)

        img_array = np.array(quantized)

        for count, color_tuple in colors:
            # color_tuple is (R, G, B)
            # Ignore pure white if it's the background
            if color_tuple == (255, 255, 255): 
                continue
                
            hex_color = rgb_to_hex(color_tuple)
            
            # Create mask for this specific color
            # Use OpenCV for contour tracing (much faster than Shapely)
            lower = np.array(color_tuple, dtype="uint8")
            upper = np.array(color_tuple, dtype="uint8")
            
            # Convert PIL RGB to OpenCV BGR
            opencv_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            mask = cv2.inRange(opencv_img, lower[::-1], upper[::-1]) # BGR check
            
            # Smooth mask slightly to reduce noise
            kernel = np.ones((3,3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            path_d = []
            for cnt in contours:
                if cv2.contourArea(cnt) < 20: continue # Skip noise
                
                # Build SVG Path String
                start_point = cnt[0][0]
                path_segment = f"M {start_point[0]},{start_point[1]} "
                
                for point in cnt[1:]:
                    p = point[0]
                    path_segment += f"L {p[0]},{p[1]} "
                
                path_segment += "Z"
                path_d.append(path_segment)
            
            if path_d:
                full_path = " ".join(path_d)
                svg_groups.append(f'<path fill="{hex_color}" d="{full_path}" />')

        svg_content = f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">{ "".join(svg_groups) }</svg>'
        
        return Response(content=svg_content, media_type="image/svg+xml")

    except Exception as e:
        print(f"Vector Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
