"""
AI X-ray Diagnosis System — FastAPI Backend
============================================
Connects with the React + Tailwind frontend at http://localhost:5173.

Run with:
    uvicorn main:app --reload

Endpoints:
    GET  /health   → Health check
    POST /predict  → X-ray image classifier
"""

import asyncio
import io
import random
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────────
# App initialisation
# ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI X-ray Diagnosis API",
    description="Backend for the AI-powered chest X-ray classifier.",
    version="1.0.0",
)

# ─────────────────────────────────────────────────────────────────
# CORS — allow the React dev server (Vite on 5173, CRA on 3000)
# ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite (React + Tailwind frontend)
        "http://localhost:3000",  # Create React App fallback
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────

# Accepted image MIME types — must match frontend validation
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}
ALLOWED_EXTENSIONS    = {".jpg", ".jpeg", ".png"}

# Simulated processing delay (seconds) — remove in production
SIMULATED_DELAY_SECS  = 1.5

# ─────────────────────────────────────────────────────────────────
# Pydantic response model — must match frontend expectations exactly
# ─────────────────────────────────────────────────────────────────

class PredictionResponse(BaseModel):
    disease:    str
    confidence: float
    report:     str


class HealthResponse(BaseModel):
    status: str

# ─────────────────────────────────────────────────────────────────
# Dummy ML prediction function
# Replace this with your real model inference logic.
# ─────────────────────────────────────────────────────────────────

# Sample diseases the dummy model can "predict"
DISEASE_CATALOGUE = [
    {
        "disease":    "Pneumonia",
        "confidence": 0.92,
        "report": (
            "PRELIMINARY RADIOLOGY REPORT\n"
            "─────────────────────────────\n"
            "Findings: The X-ray demonstrates increased opacity in the lower\n"
            "right lobe consistent with consolidation. Air bronchograms are\n"
            "visible, suggesting alveolar filling.\n\n"
            "Impression: Findings are highly suggestive of right lower lobe\n"
            "pneumonia. Recommend clinical correlation and antibiotic therapy\n"
            "as clinically indicated. Follow-up imaging in 4–6 weeks.\n\n"
            "⚠ This is an AI-generated draft. A licensed radiologist must\n"
            "  review and sign off before any clinical decision is made."
        ),
    },
    {
        "disease":    "Cardiomegaly",
        "confidence": 0.87,
        "report": (
            "PRELIMINARY RADIOLOGY REPORT\n"
            "─────────────────────────────\n"
            "Findings: The cardiothoracic ratio appears elevated (> 0.5),\n"
            "indicating cardiac enlargement. The pulmonary vasculature shows\n"
            "mild prominence. No pleural effusion detected.\n\n"
            "Impression: Findings consistent with cardiomegaly. Recommend\n"
            "echocardiogram and cardiology referral for further evaluation.\n\n"
            "⚠ This is an AI-generated draft. A licensed radiologist must\n"
            "  review and sign off before any clinical decision is made."
        ),
    },
    {
        "disease":    "Pleural Effusion",
        "confidence": 0.78,
        "report": (
            "PRELIMINARY RADIOLOGY REPORT\n"
            "─────────────────────────────\n"
            "Findings: Blunting of the right costophrenic angle is noted,\n"
            "with homogeneous opacity tracking along the lateral chest wall.\n"
            "This is consistent with a moderate right-sided pleural effusion.\n\n"
            "Impression: Right pleural effusion present. Thoracentesis may\n"
            "be considered for diagnostic and/or therapeutic purposes.\n\n"
            "⚠ This is an AI-generated draft. A licensed radiologist must\n"
            "  review and sign off before any clinical decision is made."
        ),
    },
    {
        "disease":    "Atelectasis",
        "confidence": 0.81,
        "report": (
            "PRELIMINARY RADIOLOGY REPORT\n"
            "─────────────────────────────\n"
            "Findings: Linear band-like opacities are observed at the left\n"
            "lung base, consistent with subsegmental atelectasis. Volume\n"
            "loss is noted in the left lower lobe.\n\n"
            "Impression: Left lower lobe atelectasis. Incentive spirometry\n"
            "and deep breathing exercises recommended. Monitor for secondary\n"
            "infection.\n\n"
            "⚠ This is an AI-generated draft. A licensed radiologist must\n"
            "  review and sign off before any clinical decision is made."
        ),
    },
    {
        "disease":    "No Finding",
        "confidence": 0.96,
        "report": (
            "PRELIMINARY RADIOLOGY REPORT\n"
            "─────────────────────────────\n"
            "Findings: Lung fields appear clear and well-aerated bilaterally.\n"
            "No focal consolidation, pleural effusion, or pneumothorax is\n"
            "identified. Cardiac silhouette is within normal limits.\n"
            "Bony thorax intact.\n\n"
            "Impression: No acute cardiopulmonary findings detected.\n"
            "Routine follow-up as clinically indicated.\n\n"
            "⚠ This is an AI-generated draft. A licensed radiologist must\n"
            "  review and sign off before any clinical decision is made."
        ),
    },
]


def predict(image: Image.Image) -> tuple[str, float, str]:
    """
    Placeholder ML inference function.

    In production, replace this with your actual model:
        model = load_model("weights/resnet50_chest.pth")
        tensor = preprocess(image)
        logits = model(tensor)
        label, conf = postprocess(logits)

    Args:
        image: A PIL Image object (already validated and opened).

    Returns:
        Tuple of (disease_name, confidence_score, report_text)
    """
    # ── Dummy logic: randomly pick from catalogue ──────────────
    # Seeding on image size gives deterministic results per image.
    random.seed(image.size[0] * image.size[1])
    result = random.choice(DISEASE_CATALOGUE)

    return result["disease"], result["confidence"], result["report"]

# ─────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    """Returns 200 OK when the service is running."""
    return HealthResponse(status="ok")


@app.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Predict disease from X-ray image",
    tags=["Prediction"],
    status_code=status.HTTP_200_OK,
)
async def predict_xray(
    file: UploadFile = File(..., description="Chest X-ray image (JPEG or PNG)"),
) -> PredictionResponse:
    """
    Accepts a chest X-ray image upload and returns an AI-generated
    disease prediction, confidence score, and radiology report.

    - **file**: multipart/form-data image — key must be `file`
    - **Returns**: disease, confidence (0–1), and a text report
    """

    # ── 1. Validate file was actually provided ─────────────────
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided. Please upload a chest X-ray image.",
        )

    # ── 2. Validate file extension ─────────────────────────────
    filename  = file.filename or ""
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid file type '{extension}'. "
                f"Accepted formats: {', '.join(ALLOWED_EXTENSIONS)}."
            ),
        )

    # ── 3. Validate MIME / content type ───────────────────────
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid content type '{content_type}'. "
                f"Accepted types: {', '.join(ALLOWED_CONTENT_TYPES)}."
            ),
        )

    # ── 4. Read file bytes into memory ─────────────────────────
    try:
        raw_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read uploaded file: {exc}",
        )

    # ── 5. Open and validate as a real image via Pillow ────────
    try:
        image = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File could not be decoded as a valid image. Please upload an undamaged JPEG or PNG.",
        )

    # ── 6. Simulate processing delay (remove in production) ────
    await asyncio.sleep(SIMULATED_DELAY_SECS)

    # ── 7. Run prediction ──────────────────────────────────────
    try:
        disease, confidence, report = predict(image)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model inference failed: {exc}",
        )

    # ── 8. Return response matching frontend contract ──────────
    return PredictionResponse(
        disease=disease,
        confidence=round(confidence, 4),
        report=report,
    )

# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
