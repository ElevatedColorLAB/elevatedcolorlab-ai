# upscale.py
import base64
import io
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Request(BaseModel):
    image_b64: str
    target_width: int = 0
    target_height: int = 0
    dpi: int = 300

@app.post("/upscale")
async def upscale(req: Request):
    try:
        # Robust Base64 Decoding
        b64 = req.image_b64
        if "base64," in b64: b64 = b64.split("base64,")[1]
        
        img = Image.open(io.BytesIO(base64.b64decode(b64)))
        
        # Default to 2x if no target sent
        w = req.target_width if req.target_width > 0 else img.width * 2
        h = req.target_height if req.target_height > 0 else img.height * 2

        img = img.resize((w, h), Image.Resampling.LANCZOS)
        
        buf = io.BytesIO()
        img.save(buf, format="PNG", dpi=(req.dpi, req.dpi))
        return {"image_b64": base64.b64encode(buf.getvalue()).decode("utf-8")}
    except Exception as e:
        print(f"Upscale Error: {e}")
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
