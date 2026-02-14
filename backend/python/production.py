# production.py - Halftone and Production Form Service
# To run: uvicorn production:app --host 0.0.0.0 --port 8004
import base64
import io
from typing import List, Dict
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class HalftoneRequest(BaseModel):
    image_b64: str
    lpi: float
    angle: float
    dot_shape: str
    channel_name: str
    mesh_count: int
    print_order: int

class ProductionFormRequest(BaseModel):
    job_name: str
    image_b64: str
    channels: List[Dict]

# --- Core Logic ---
def create_halftone_bitmap(gray_image: Image.Image, lpi: float, angle: float, shape: str) -> Image.Image:
    """
    Simulates the creation of a 1-bit halftone bitmap from a grayscale image.
    This provides a visual representation for demonstration purposes. A real-world
    implementation would use complex digital screening algorithms (RIP software).
    """
    width, height = gray_image.size
    bitmap = Image.new("1", (width, height), color=1) # White canvas (1-bit)
    draw = ImageDraw.Draw(bitmap)
    pixels = gray_image.load()
    
    # Calculate cell size based on Lines Per Inch (LPI)
    cell_size = int(width / lpi)
    if cell_size < 2: cell_size = 2 # Prevent zero or one pixel cells

    # Iterate over the image in halftone cells
    for x in range(0, width, cell_size):
        for y in range(0, height, cell_size):
            # Calculate the average intensity of the pixels in the cell
            intensity_sum = 0
            num_pixels = 0
            for i in range(cell_size):
                for j in range(cell_size):
                    if x + i < width and y + j < height:
                        intensity_sum += pixels[x + i, y + j]
                        num_pixels += 1
            
            if num_pixels == 0: continue
            
            # Normalize intensity (0.0 = black, 1.0 = white)
            intensity = (intensity_sum / num_pixels) / 255.0
            # Dot size is inversely proportional to intensity
            dot_size_factor = (1.0 - intensity)
            
            cx, cy = x + cell_size / 2, y + cell_size / 2
            
            # Draw the dot if it has a size
            if dot_size_factor > 0.1:
                if shape == 'ellipse':
                    rx = dot_size_factor * (cell_size / 1.8)
                    ry = dot_size_factor * (cell_size / 2.2)
                    draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=0)
                elif shape == 'round':
                    radius = dot_size_factor * (cell_size / 2.0)
                    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=0)
                elif shape == 'line':
                    thickness = int(dot_size_factor * (cell_size / 2.0))
                    if thickness > 0:
                        draw.line((x, cy, x + cell_size, cy), fill=0, width=thickness)

    # TODO: Implement rotation based on the 'angle' parameter
    return bitmap

@app.post("/generate-film")
async def generate_film(request: HalftoneRequest):
    """
    Generates a single production-ready film positive as a PNG image,
    complete with registration marks and information text.
    """
    try:
        image_data = base64.b64decode(request.image_b64.split(',')[1])
        channel_img = Image.open(io.BytesIO(image_data)).convert('L')
        
        halftone_bitmap = create_halftone_bitmap(channel_img, request.lpi, request.angle, request.dot_shape)
        
        # Create a larger canvas for the film, adding margins
        margin = int(1 * 72) # 1 inch in pixels (assuming 72 DPI for this context)
        new_width = channel_img.width + 2 * margin
        new_height = channel_img.height + 2 * margin
        film_output = Image.new("1", (new_width, new_height), 1) # White background
        
        # Paste the halftone art in the center
        film_output.paste(halftone_bitmap, (margin, margin))
        
        draw = ImageDraw.Draw(film_output)
        try:
            # Use a common system font; provide a fallback
            font = ImageFont.truetype("arial.ttf", 24)
        except IOError:
            font = ImageFont.load_default()

        # Function to draw a standard registration mark
        def draw_reg_mark(x, y, radius=10, crosshair_len=20):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=0, width=1)
            draw.line((x - crosshair_len, y, x + crosshair_len, y), fill=0, width=1)
            draw.line((x, y - crosshair_len, x, y + crosshair_len), fill=0, width=1)

        # Draw registration marks at the center of each edge
        draw_reg_mark(new_width // 2, margin // 2)
        draw_reg_mark(new_width // 2, new_height - margin // 2)
        draw_reg_mark(margin // 2, new_height // 2)
        draw_reg_mark(new_width - margin // 2, new_height // 2)
        
        # Add production info text at the bottom
        info_text = f"Print Order: {request.print_order} | Channel: {request.channel_name} | {request.lpi} LPI @ {request.angle} deg | Mesh: {request.mesh_count}"
        draw.text((margin, new_height - margin / 2), info_text, font=font, fill=0, anchor="lm")

        # Encode the final film to base64
        buffered = io.BytesIO()
        film_output.save(buffered, format="PNG")
        film_b64 = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return {"film_b64": film_b64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-form", response_class=Response)
async def generate_production_form(request: ProductionFormRequest):
    """
    Generates a PDF production form with job details, a preview image,
    and a list of color channels and their settings.
    """
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # --- PDF Header ---
        p.setFont("Helvetica-Bold", 16)
        p.drawString(inch, height - inch, f"Production Form: {request.job_name}")
        
        # --- Preview Image ---
        p.setFont("Helvetica", 12)
        img_data = base64.b64decode(request.image_b64.split(',')[1])
        img_reader = ImageReader(io.BytesIO(img_data))
        p.drawImage(img_reader, inch, height - 4*inch, width=2.5*inch, preserveAspectRatio=True, mask='auto')

        # --- Ink Details Section ---
        y_pos = height - 1.5*inch
        p.setFont("Helvetica-Bold", 12)
        p.drawString(inch * 4, y_pos, "Print Order & Ink Details:")
        y_pos -= 25
        
        p.setFont("Helvetica", 10)
        # Sort channels by print order before listing them
        sorted_channels = sorted(request.channels, key=lambda c: c.get('print_order', 99))
        for i, channel in enumerate(sorted_channels):
            order = channel.get('print_order', i + 1)
            text = f"{order}. {channel.get('name', 'N/A')} ({channel.get('color', 'N/A')}) - Mesh: {channel.get('mesh', 'N/A')}"
            p.drawString(inch * 4.2, y_pos, text)
            y_pos -= 20

        p.showPage()
        p.save()
        buffer.seek(0)
        
        # Return the PDF as a file attachment
        return Response(
            content=buffer.getvalue(), 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"attachment; filename={request.job_name.replace(' ', '_')}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    """Root endpoint to check service status."""
    return {"message": "Production Service is running."}
