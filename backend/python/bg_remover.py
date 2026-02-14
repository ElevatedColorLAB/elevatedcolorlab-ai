# bg_remover.py
import base64
import io
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
from transformers import AutoModelForImageSegmentation
from torchvision import transforms

# --- Model Initialization ---
MODEL = None
MODEL_STATUS = "Not Loaded"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    global MODEL, MODEL_STATUS
    print(f"BG Remover: Loading on {DEVICE}...")
    try:
        # Safely try to set precision (only works on newer PyTorch)
        if hasattr(torch, "set_float32_matmul_precision"):
            torch.set_float32_matmul_precision("high")
        
        MODEL = AutoModelForImageSegmentation.from_pretrained("ZhengPeng7/BiRefNet", trust_remote_code=True)
        MODEL.to(DEVICE)
        MODEL.eval()
        MODEL_STATUS = "Ready"
    except Exception as e:
        MODEL_STATUS = f"Error: {e}"
        print(MODEL_STATUS)

transform_image = transforms.Compose([
    transforms.Resize((1024, 1024)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

class Request(BaseModel):
    image_b64: str
    threshold: float = 0.5

@app.post("/remove-background")
async def remove_background(req: Request):
    if not MODEL: raise HTTPException(503, f"Model not ready: {MODEL_STATUS}")
    try:
        # Robust Base64 Decoding
        b64 = req.image_b64
        if "base64," in b64: b64 = b64.split("base64,")[1]
        
        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        orig_size = img.size
        
        input_tensor = transform_image(img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            preds = MODEL(input_tensor)[-1].sigmoid().cpu()
        
        mask = transforms.ToPILImage()(preds[0].squeeze()).resize(orig_size, Image.Resampling.LANCZOS)
        mask = mask.point(lambda p: 255 if p > int(255 * req.threshold) else 0)
        
        img_rgba = img.convert("RGBA")
        img_rgba.putalpha(mask)
        
        buf = io.BytesIO()
        img_rgba.save(buf, format="PNG")
        return {"image_b64": base64.b64encode(buf.getvalue()).decode("utf-8")}
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
