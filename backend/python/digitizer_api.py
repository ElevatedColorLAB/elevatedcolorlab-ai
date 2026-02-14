# digitizer_api.py
# RUN ON VPS: python digitizer_api.py
# IP: 74.208.133.116 | Port: 8007

import os
import numpy as np
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image
import cv2
from sklearn.cluster import MiniBatchKMeans
import pyembroidery
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin for your HTML frontend

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def quantize_image(image_path, n_colors=8):
    """Reduces image to n_colors using K-Means clustering."""
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    (h, w) = img.shape[:2]
    
    # Reshape for K-Means
    img_reshaped = img.reshape((img.shape[0] * img.shape[1], 3))
    
    # Cluster
    clt = MiniBatchKMeans(n_clusters=n_colors)
    labels = clt.fit_predict(img_reshaped)
    quant = clt.cluster_centers_.astype("uint8")[labels]
    
    # Reshape back
    quant = quant.reshape((h, w, 3))
    
    # Convert back to BGR for OpenCV processing later
    return cv2.cvtColor(quant, cv2.COLOR_RGB2BGR), clt.cluster_centers_

def generate_stitches(quantized_img, centers, pull_comp=0.2, underlay_type='Center Run', density=0.4):
    """Generates embroidery pattern from quantized image with Pro features."""
    pattern = pyembroidery.EmbPattern()
    
    # Convert density (mm) to stitch points (0.1mm units)
    # Standard density is ~4-5 points. Lower density value = closer stitches.
    # 0.4mm = 4 points
    stitch_spacing = int(density * 10) 

    # For each color center, create a mask and find contours
    for center in centers:
        # Create mask for this color
        # Note: center is in RGB, image is in BGR (OpenCV standard)
        color_bgr = center[::-1].astype("uint8")
        
        # Find pixels matching this color
        mask = cv2.inRange(quantized_img, color_bgr, color_bgr)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Add Color Change to Pattern
        pattern.add_thread(pyembroidery.EmbThread(int(center[0]), int(center[1]), int(center[2])))
        
        for contour in contours:
            # Skip small noise
            if cv2.contourArea(contour) < 50:
                continue
                
            # Simplify contour
            epsilon = 0.01 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Convert to Shapely Polygon
            points = approx.reshape(-1, 2)
            if len(points) < 3: continue
            
            poly = Polygon(points)
            
            # --- PRO FEATURE: PULL COMPENSATION ---
            # Expand shape slightly to account for thread tension pulling fabric in
            # pull_comp is in mm, convert to units (1mm = 10 units)
            buffered_poly = poly.buffer(pull_comp * 10, join_style=2) # 2 = Miter join
            
            # --- PRO FEATURE: UNDERLAY ---
            if underlay_type != 'None':
                # Underlay is usually smaller than the main shape
                underlay_poly = poly.buffer(-5) # Shrink by 0.5mm
                
                if not underlay_poly.is_empty:
                    if underlay_type == 'Center Run':
                        # Simple running stitch along the center/skeleton (simplified here as boundary)
                        # Ideally would use medial axis transform, but boundary walk is a basic underlay
                        u_points = list(underlay_poly.exterior.coords)
                        pattern.add_stitch_absolute(pyembroidery.JUMP, u_points[0][0] * 2, u_points[0][1] * 2)
                        for pt in u_points:
                            pattern.add_stitch_absolute(pyembroidery.STITCH, pt[0] * 2, pt[1] * 2)
                            
                    elif underlay_type == 'Tatami (Full)':
                         # Generate a sparse fill for underlay
                         # (Simplified: just another outline for this demo, full tatami logic is complex)
                         u_points = list(underlay_poly.exterior.coords)
                         pattern.add_stitch_absolute(pyembroidery.JUMP, u_points[0][0] * 2, u_points[0][1] * 2)
                         for pt in u_points:
                            pattern.add_stitch_absolute(pyembroidery.STITCH, pt[0] * 2, pt[1] * 2)

            # --- MAIN FILL (TATAMI / SATIN SIMULATION) ---
            # For this engine, we will use a scan-line fill approach for Tatami
            
            # Get bounding box
            minx, miny, maxx, maxy = buffered_poly.bounds
            
            # Generate scan lines
            y = miny
            while y < maxy:
                # Create a horizontal line across the shape
                line_string = [(minx, y), (maxx, y)]
                # In a real implementation, we intersect this line with the polygon
                # to find entry/exit points for stitches.
                # Due to complexity of full Tatami math in a single file, we will stick to 
                # a high-quality Outline/Satin simulation for the main visual.
                
                # Fallback to Outline (Satin-like) for robust demo
                final_points = list(buffered_poly.exterior.coords)
                
                # Move to start
                pattern.add_stitch_absolute(pyembroidery.JUMP, final_points[0][0] * 2, final_points[0][1] * 2)
                
                # Stitch the path
                for pt in final_points:
                     # Scale up (pixels -> 0.1mm units). Factor 2 is arbitrary for visibility scaling.
                    pattern.add_stitch_absolute(pyembroidery.STITCH, pt[0] * 2, pt[1] * 2)
                
                # Close loop
                pattern.add_stitch_absolute(pyembroidery.STITCH, final_points[0][0] * 2, final_points[0][1] * 2)
                
                # Break loop as we are doing outline mode for stability
                break 
            
    pattern.end()
    return pattern

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "online", "service": "Digitizer Pro"})

@app.route('/digitize', methods=['POST'])
def digitize():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    colors = int(request.form.get('colors', 8))
    pull_comp = float(request.form.get('pull_comp', 0.2))
    density = float(request.form.get('density', 0.4))
    underlay = request.form.get('underlay', 'Center Run')
    
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    
    try:
        # 1. Process Image
        quantized, centers = quantize_image(filepath, n_colors=colors)
        
        # 2. Generate Pattern with Pro Settings
        pattern = generate_stitches(quantized, centers, pull_comp, underlay, density)
        
        # 3. Save DST
        output_filename = os.path.splitext(file.filename)[0] + ".dst"
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)
        pyembroidery.write_dst(pattern, output_path)
        
        return send_file(output_path, as_attachment=True)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Best Digitizer Backend on Port 8007...")
    # Host 0.0.0.0 allows external connections
    app.run(host='0.0.0.0', port=8007)
