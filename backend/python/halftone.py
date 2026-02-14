# halftone.py
# This is a placeholder service for port 8006.
# It will be expanded later to create halftone films.

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "Halftone Service"}

@app.post("/generate-halftones")
async def generate_halftones(data: dict = Body(...)):
    """
    Placeholder endpoint for generating halftone PDFs.
    """
    # In the future, this will do real processing.
    # For now, it just returns a success message.
    print("Halftone generation request received.")
    
    # Simulating a successful response
    return {
        "message": "Halftone service is running, but PDF generation is not yet implemented.",
        "received_max_colors": data.get("max_colors"),
        "design_name": data.get("design_name")
    }

if __name__ == "__main__":
    print("--- Starting Halftone Service on port 8006 ---")
    uvicorn.run(app, host="0.0.0.0", port=8006)
