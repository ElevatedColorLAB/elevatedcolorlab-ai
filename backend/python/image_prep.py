# image_prep.py
# Production‑grade image microservice for ElevatedColorLAB
# Port: 8008

import os
import io
import base64
import logging
from typing import Tuple

from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import numpy as np

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SERVICE_NAME = "Image Prep Service"
SERVICE_VERSION = "2.0.0"

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(SERVICE_NAME)

# -----------------------------------------------------------------------------
# App Setup
# -----------------------------------------------------------------------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}})

# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------
def fail(message: str, status: int = 400):
    return jsonify({"error": message}), status


def decode_base64_image(data: str) -> Image.Image:
    if not isinstance(data, str) or not data.strip():
        raise ValueError("Image data must be a non‑empty base64 string")

    if "base64," in data:
        data = data.split("base64,", 1)[1]

    try:
        raw = base64.b64decode(data)
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        return img
    except Exception as e:
        raise ValueError(f"Invalid base64 image: {e}")


def encode_base64_image(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def get_json():
    if not request.is_json:
        raise ValueError("Request must be JSON")
    data = request.get_json(silent=True)
    if data is None:
        raise ValueError("Invalid JSON payload")
    return data

# -----------------------------------------------------------------------------
# Image Operations
# -----------------------------------------------------------------------------
def knockout_black_pixels(img: Image.Image, tolerance: int) -> Image.Image:
    arr = np.array(img)
    rgb = arr[:, :, :3]
    brightness = np.max(rgb, axis=2)

    mask = brightness < tolerance
    arr[:, :, 3][mask] = 0

    return Image.fromarray(arr)


def dither_alpha(img: Image.Image) -> Image.Image:
    arr = np.array(img).astype(float)
    h, w, _ = arr.shape
    alpha = arr[:, :, 3]

    for y in range(h):
        for x in range(w):
            old = alpha[y, x]
            new = 255 if old > 127 else 0
            alpha[y, x] = new
            err = old - new

            if x + 1 < w:
                alpha[y, x + 1] += err * 7 / 16
            if x - 1 >= 0 and y + 1 < h:
                alpha[y + 1, x - 1] += err * 3 / 16
            if y + 1 < h:
                alpha[y + 1, x] += err * 5 / 16
            if x + 1 < w and y + 1 < h:
                alpha[y + 1, x + 1] += err * 1 / 16

    alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    arr[:, :, 3] = alpha

    return Image.fromarray(arr.astype(np.uint8))

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/knockout_black", methods=["POST"])
def route_knockout_black():
    try:
        data = get_json()
        img = decode_base64_image(data.get("image"))
        tolerance = int(data.get("options", {}).get("tolerance", 30))
        tolerance = max(0, min(255, tolerance))

        result = knockout_black_pixels(img, tolerance)
        return jsonify({"image": encode_base64_image(result)})

    except Exception as e:
        log.exception("knockout_black failed")
        return fail(str(e), 500)


@app.route("/fix_transparency", methods=["POST"])
def route_fix_transparency():
    try:
        data = get_json()
        img = decode_base64_image(data.get("image"))

        result = dither_alpha(img)
        return jsonify({"image": encode_base64_image(result)})

    except Exception as e:
        log.exception("fix_transparency failed")
        return fail(str(e), 500)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "online", "service": SERVICE_NAME})


@app.route("/version", methods=["GET"])
def version():
    return jsonify({
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "allowed_origins": ALLOWED_ORIGINS
    })


# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8008"))
    log.info(f"Starting {SERVICE_NAME} v{SERVICE_VERSION} on port {port}")
    app.run(host="0.0.0.0", port=port)