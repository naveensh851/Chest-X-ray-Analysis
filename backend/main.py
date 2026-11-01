"""
AI X-ray Diagnosis System — FastAPI Backend (v2 with Auth + Reports)
=====================================================================
Connects with the React + Tailwind frontend at http://localhost:5173.

Run with:
    uvicorn main:app --reload

Endpoints:
    GET  /health       → Health check (public)
    POST /auth/register → Register new user (public)
    POST /auth/login   → Login, returns JWT token (public)
    POST /predict      → X-ray image classifier (🔒 JWT required)
    GET  /reports      → List user's saved reports (🔒 JWT required)
    GET  /uploads/{filename} → Serve uploaded images
"""

import asyncio
import io
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import numpy as np

# ── TensorFlow / Keras (imported lazily so startup errors are visible) ──
try:
    import tensorflow as tf
    from tensorflow.keras.applications import EfficientNetB0
    from tensorflow.keras.applications.efficientnet import preprocess_input
    from tensorflow.keras.layers import (
        BatchNormalization, Dense, Dropout, GlobalAveragePooling2D,
    )
    from tensorflow.keras.models import Model
    _TF_AVAILABLE = True
except ImportError:
    _TF_AVAILABLE = False
    logging.warning("TensorFlow not installed — model inference will be unavailable.")

import uvicorn
from fastapi import (
    Depends, FastAPI, File, HTTPException, Request, UploadFile, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from PIL import Image
from pydantic import BaseModel, EmailStr
from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, event,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

# ─────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────

# IMPORTANT: Change SECRET_KEY in production (use secrets.token_hex(32))
SECRET_KEY      = "xray-super-secret-key-change-in-production-2024"
ALGORITHM       = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

BASE_DIR        = Path(__file__).resolve().parent
DATABASE_URL    = f"sqlite:///{BASE_DIR / 'xray_app.db'}"
UPLOAD_DIR      = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
HEATMAP_DIR     = UPLOAD_DIR / "heatmaps"
HEATMAP_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_CONTENT_TYPES  = {"image/jpeg", "image/jpg", "image/png"}
ALLOWED_EXTENSIONS     = {".jpg", ".jpeg", ".png"}

# ── EfficientNetB0 — 5-class chest X-ray classifier (balanced) ───────────
CLASS_LABELS   = ["Infiltration", "Effusion", "Atelectasis", "Nodule", "Mass"]
_candidate_weights = [
    BASE_DIR / "model" / "model_5class_balanced_weights.h5",
    Path("model") / "model_5class_balanced_weights.h5",
    BASE_DIR.parent / "frontend and model" / "model" / "model_5class_balanced_weights.h5",
]
MODEL_WEIGHTS  = next((p for p in _candidate_weights if p.exists()), _candidate_weights[0])
MODEL_INPUT_SHAPE = (224, 224, 3)

# ─────────────────────────────────────────────────────────────────
# Database — SQLAlchemy
# ─────────────────────────────────────────────────────────────────

engine         = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal   = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    """Users table."""
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, index=True)
    email    = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)             # bcrypt hash

    reports  = relationship("ReportModel", back_populates="user", cascade="all, delete-orphan")


class ReportModel(Base):
    """Reports table — one row per prediction."""
    __tablename__ = "reports"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_path   = Column(String, nullable=False)
    disease      = Column(String, nullable=False)
    confidence   = Column(Float, nullable=False)
    report_text  = Column(Text, nullable=True)   # full radiology report text (TEXT for large content)
    heatmap_path = Column(String, nullable=True)  # relative path to generated heatmap PNG
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user         = relationship("UserModel", back_populates="reports")


# Create all tables on startup
Base.metadata.create_all(bind=engine)

# ── Auto-migrate: add report_text and heatmap_path columns if they don't exist ──
with engine.connect() as _conn:
    from sqlalchemy import text as _sql
    cols = [row[1] for row in _conn.execute(_sql("PRAGMA table_info(reports)")).fetchall()]
    if "report_text" not in cols:
        _conn.execute(_sql("ALTER TABLE reports ADD COLUMN report_text TEXT"))
        _conn.commit()
    if "heatmap_path" not in cols:
        _conn.execute(_sql("ALTER TABLE reports ADD COLUMN heatmap_path TEXT"))
        _conn.commit()

# ── Backfill: ensure existing reports have report_text ──
with SessionLocal() as db:
    reports = db.query(ReportModel).filter(ReportModel.report_text == None).all()
    for r in reports:
        r.report_text = "Legacy report: No text available."
    db.commit()


def get_db():
    """Dependency: yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# Security helpers
# ─────────────────────────────────────────────────────────────────

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(plain: str) -> str:
    # bcrypt silently truncates or raises at 72 bytes — we enforce the limit.
    plain = plain.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    # Mirror the same truncation so login always matches the stored hash.
    plain = plain.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserModel:
    """Validate JWT and return the corresponding UserModel or raise 401."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = db.query(UserModel).filter(UserModel.email == email).first()
    if user is None:
        raise credentials_exc
    return user


# ─────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email:    EmailStr
    password: str


class UserLoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


class PredictionResponse(BaseModel):
    disease:     str
    confidence:  float
    report:      str
    heatmap_url: str = ""   # absolute URL to the demo heatmap PNG


class ReportOut(BaseModel):
    id:           int
    image_path:   str
    disease:      str
    confidence:   float
    report_text:  str | None = None
    heatmap_path: str | None = None
    created_at:   datetime

    # Computed fields — full URLs the frontend can use directly in <img src=...>
    image_url:   str = ""
    heatmap_url: str = ""

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_url(cls, obj: "ReportModel", base_url: str) -> "ReportOut":
        # from_attributes=True is required in Pydantic v2 when validating
        # SQLAlchemy ORM objects — without it, lazy-loaded fields return None.
        inst = cls.model_validate(obj, from_attributes=True)
        inst.image_url   = f"{base_url}{obj.image_path}"
        inst.heatmap_url = f"{base_url}{obj.heatmap_path}" if obj.heatmap_path else ""
        return inst



class HealthResponse(BaseModel):
    status: str


# ─────────────────────────────────────────────────────────────────
# Model loading — EfficientNetB0 (built once at import time)
# ─────────────────────────────────────────────────────────────────

def _build_efficientnet_model() -> "Model | None":
    """
    Rebuild the EfficientNetB0 architecture, load pre-trained weights,
    and return the compiled Keras model.  Returns None when TF is not
    installed or the weights file is missing.
    """
    if not _TF_AVAILABLE:
        logging.error("TensorFlow unavailable — model will not be loaded.")
        return None

    if not MODEL_WEIGHTS.exists():
        logging.error(
            "Weights file not found at '%s'. "
            "Place model_5class_balanced_weights.h5 inside backend/model/.",
            MODEL_WEIGHTS,
        )
        return None

    try:
        logging.info("Building EfficientNetB0 architecture (balanced) …")
        base_model = EfficientNetB0(
            weights=None,
            include_top=False,
            input_shape=MODEL_INPUT_SHAPE,
        )

        x = base_model.output
        x = GlobalAveragePooling2D()(x)
        x = BatchNormalization()(x)
        x = Dense(256, activation="relu")(x)
        x = Dropout(0.5)(x)          # balanced model uses 0.5
        output = Dense(5, activation="sigmoid")(x)

        model = Model(inputs=base_model.input, outputs=output)
        logging.info("Loading weights from '%s' …", MODEL_WEIGHTS)
        model.load_weights(str(MODEL_WEIGHTS))
        logging.info("EfficientNetB0 model loaded successfully (%d params).",
                     model.count_params())
        return model
    except Exception as exc:  # noqa: BLE001
        logging.exception("Failed to build/load model: %s", exc)
        return None


# Module-level singleton — loaded once, reused across all requests
_ML_MODEL: "Model | None" = _build_efficientnet_model()


# ─────────────────────────────────────────────────────────────────
# Preprocessing & prediction helpers
# ─────────────────────────────────────────────────────────────────

def _preprocess_image(image: Image.Image) -> "np.ndarray":
    """
    Convert a PIL image to the exact input tensor expected by the model.

    Pipeline:
        1. Grayscale  → remove colour information (X-rays are monochrome)
        2. Resize     → 224×224
        3. To array   → shape (224, 224)
        4. Stack ×3   → shape (224, 224, 3)  (model expects 3 channels)
        5. preprocess_input → EfficientNet-specific normalisation
        6. Expand dims → shape (1, 224, 224, 3)  (batch dimension)
    """
    gray   = image.convert("L")                      # 1. grayscale
    resized = gray.resize((224, 224))                # 2. resize
    arr     = np.array(resized, dtype=np.float32)    # 3. to array (H, W)
    rgb     = np.stack([arr, arr, arr], axis=-1)     # 4. repeat → (H, W, 3)
    normed  = preprocess_input(rgb)                  # 5. EfficientNet norm
    batched = np.expand_dims(normed, axis=0)         # 6. add batch dim
    return batched


def _generate_report(disease: str, confidence: float) -> str:
    """Build a simple dynamic radiology report string."""
    return (
        "PRELIMINARY RADIOLOGY REPORT\n"
        "─────────────────────────────\n"
        f"Findings: The X-ray suggests signs of {disease} "
        f"with a model confidence of {confidence:.2f}.\n\n"
        "Impression: Clinical correlation and review by a licensed radiologist\n"
        "is strongly recommended before any clinical decision is made.\n\n"
        "⚠ This is an AI-generated draft. A licensed radiologist must\n"
        "  review and sign off before any clinical decision is made."
    )


# Grad-CAM target layer in EfficientNetB0
GRADCAM_LAYER = "top_conv"


def run_prediction(image: Image.Image) -> tuple[str, float, str, "np.ndarray"]:
    """
    Run EfficientNetB0 inference on a chest X-ray PIL image.

    Args:
        image: PIL Image object (already validated and opened).

    Returns:
        Tuple of (disease_name, confidence_score, report_text, input_tensor)
        The input_tensor is returned so the caller can pass it directly to
        Grad-CAM without re-running the expensive preprocessing step.

    Raises:
        RuntimeError: When the model is not loaded (TF missing / weights absent).
    """
    if _ML_MODEL is None:
        raise RuntimeError(
            "ML model is not available. "
            "Ensure TensorFlow is installed and the weights file exists at "
            f"'{MODEL_WEIGHTS}'."
        )

    # Preprocess → predict
    input_tensor = _preprocess_image(image)           # shape (1, 224, 224, 3)
    preds        = _ML_MODEL.predict(input_tensor, verbose=0)[0]  # shape (5,)

    best_idx    = int(np.argmax(preds))
    confidence  = float(preds[best_idx])
    disease     = CLASS_LABELS[best_idx]
    report_text = _generate_report(disease, confidence)

    return disease, confidence, report_text, input_tensor


# ─────────────────────────────────────────────────────────────────
# Real Grad-CAM heatmap
# ─────────────────────────────────────────────────────────────────

def _apply_jet_colormap(gray: np.ndarray) -> np.ndarray:
    """
    Apply a JET-like colormap to a 2-D float array [0,1].
    Uses OpenCV when available; falls back to a pure-NumPy approximation.

    Returns an (H, W, 3) uint8 RGB array.
    """
    try:
        import cv2  # noqa: PLC0415
        gray_uint8 = np.uint8(255 * gray)
        colored    = cv2.applyColorMap(gray_uint8, cv2.COLORMAP_JET)
        # cv2 returns BGR — convert to RGB
        return colored[:, :, ::-1]
    except ImportError:
        # NumPy fallback: blue→cyan→green→yellow→red JET approximation
        r = np.clip(1.5 - np.abs(4 * gray - 3), 0, 1)
        g = np.clip(1.5 - np.abs(4 * gray - 2), 0, 1)
        b = np.clip(1.5 - np.abs(4 * gray - 1), 0, 1)
        rgb = np.stack([r, g, b], axis=-1)
        return np.uint8(rgb * 255)


def get_gradcam(
    model: "Model",
    input_tensor: np.ndarray,
    class_idx: int,
    layer_name: str = GRADCAM_LAYER,
) -> np.ndarray:
    """
    Compute the Grad-CAM activation map for a given class index.

    Args:
        model:        The loaded Keras model.
        input_tensor: Preprocessed batch tensor, shape (1, 224, 224, 3).
        class_idx:    Index of the predicted class (used to select gradient).
        layer_name:   Name of the last convolutional layer to hook.

    Returns:
        2-D NumPy float32 array normalised to [0, 1], shape (H_feat, W_feat).
        Returns a zero array on any error.
    """
    try:
        # Build a sub-model: input → [conv-layer output, final predictions]
        grad_model = Model(
            inputs  = model.inputs,
            outputs = [model.get_layer(layer_name).output, model.output],
        )

        inp = tf.cast(input_tensor, tf.float32)
        with tf.GradientTape() as tape:
            tape.watch(inp)
            conv_outputs, predictions = grad_model(inp, training=False)
            # Score for the predicted class
            class_score = predictions[:, class_idx]

        # Gradient of the class score w.r.t. conv feature maps
        grads = tape.gradient(class_score, conv_outputs)   # (1, H, W, C)

        # Global-average-pool the gradients over spatial dims → (C,)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

        # Weight each feature map channel by its importance
        conv_out = conv_outputs[0]                         # (H, W, C)
        heatmap  = conv_out @ pooled_grads[..., tf.newaxis]  # (H, W, 1)
        heatmap  = tf.squeeze(heatmap)                     # (H, W)

        # ReLU + normalise to [0, 1]
        heatmap = tf.nn.relu(heatmap).numpy()
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()
        return heatmap.astype(np.float32)

    except Exception as exc:  # noqa: BLE001
        logging.warning("Grad-CAM computation failed: %s", exc)
        return np.zeros((7, 7), dtype=np.float32)


def overlay_heatmap(
    original_image: Image.Image,
    heatmap: np.ndarray,
    alpha: float = 0.45,
) -> bytes:
    """
    Resize the Grad-CAM heatmap to match the original image, colourise it
    with a JET colormap, and alpha-blend it over the original.

    Args:
        original_image: PIL Image (original X-ray, any size).
        heatmap:        2-D float array [0, 1] from get_gradcam().
        alpha:          Blend weight for the colorised heatmap (0=invisible, 1=opaque).

    Returns:
        PNG-encoded bytes of the blended image.
    """
    orig_w, orig_h = original_image.size

    # 1. Resize heatmap to original image dimensions using Pillow
    heatmap_img   = Image.fromarray(np.uint8(heatmap * 255), mode="L")
    heatmap_resized = heatmap_img.resize((orig_w, orig_h), Image.BILINEAR)
    heatmap_arr   = np.array(heatmap_resized, dtype=np.float32) / 255.0

    # 2. Colourise with JET
    colored = _apply_jet_colormap(heatmap_arr)          # (H, W, 3) uint8 RGB
    colored_img = Image.fromarray(colored, mode="RGB")

    # 3. Alpha-blend: result = (1-alpha)*original + alpha*heatmap
    base        = original_image.convert("RGB")
    blended_arr = (
        (1.0 - alpha) * np.array(base, dtype=np.float32)
        + alpha       * np.array(colored_img, dtype=np.float32)
    )
    blended = Image.fromarray(np.uint8(np.clip(blended_arr, 0, 255)), mode="RGB")

    # 4. Encode as PNG bytes
    out_io = io.BytesIO()
    blended.save(out_io, format="PNG", optimize=True)
    return out_io.getvalue()


# ─────────────────────────────────────────────────────────────────
# App initialisation
# ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI X-ray Diagnosis API (v2)",
    description="Backend for the AI-powered chest X-ray classifier with JWT auth and report storage.",
    version="2.0.0",
)

# ── CORS Middleware ──────────────────────────────────────────────
_env_origins = os.getenv("ALLOWED_ORIGINS", "")
_cors_origins = [o.strip() for o in _env_origins.split(",") if o.strip()]
_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
ALL_ALLOWED_ORIGINS = list(set(_cors_origins + _default_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALL_ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────
# Startup event — backfill any NULL report_text rows
# ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def backfill_report_text() -> None:
    """
    On every server start, find any reports rows where report_text is NULL
    (e.g. created before the column existed) and fill them using
    _generate_report() with a default confidence of 0.0.
    """
    db = SessionLocal()
    try:
        null_rows = db.query(ReportModel).filter(ReportModel.report_text == None).all()
        if null_rows:
            for row in null_rows:
                row.report_text = _generate_report(row.disease, row.confidence or 0.0)
            db.commit()
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# Routes — Public
# ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Returns 200 OK when the service is running."""
    return HealthResponse(status="ok")


@app.get("/uploads/{filename}", tags=["Files"])
async def serve_upload(filename: str):
    """Serve a previously uploaded X-ray image."""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path)


@app.get("/uploads/heatmaps/{filename}", tags=["Files"])
async def serve_heatmap(filename: str):
    """Serve a generated heatmap image."""
    file_path = HEATMAP_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Heatmap not found.")
    return FileResponse(file_path, media_type="image/png")


# ─────────────────────────────────────────────────────────────────
# Routes — Authentication
# ─────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=TokenResponse, tags=["Auth"], status_code=201)
async def register(body: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and return a JWT token."""
    existing = db.query(UserModel).filter(UserModel.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with that email already exists.",
        )

    # Wrap hashing so a bcrypt/passlib library issue surfaces as a clean 500
    # rather than an unhandled crash that kills the request.
    try:
        hashed_pw = hash_password(body.password)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password hashing failed: {exc}",
        )

    user = UserModel(email=body.email, password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(access_token=token)


@app.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
async def login(body: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return a JWT token."""
    user = db.query(UserModel).filter(UserModel.email == body.email).first()
    if not user or not verify_password(body.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(access_token=token)


# ─────────────────────────────────────────────────────────────────
# Routes — Protected (JWT required)
# ─────────────────────────────────────────────────────────────────

@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["Prediction"],
    status_code=status.HTTP_200_OK,
)
async def predict_xray(
    file: UploadFile = File(..., description="Chest X-ray image (JPEG or PNG)"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PredictionResponse:
    """
    Accepts a chest X-ray image upload, runs AI prediction,
    saves the image and a report row, and returns the prediction.

    Requires: Authorization: Bearer <token>
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

    # ── 6. Save image to /uploads with a unique filename ───────
    unique_filename = f"{uuid.uuid4().hex}{extension}"
    save_path       = UPLOAD_DIR / unique_filename
    try:
        with open(save_path, "wb") as f_out:
            f_out.write(raw_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded image: {exc}",
        )

    # ── 7. (Processing delay removed — real inference runs synchronously) ──

    # ── 8. Run prediction ──────────────────────────────────────
    try:
        disease, confidence, report, input_tensor = run_prediction(image)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model inference failed: {exc}",
        )

    # ── 9. Generate real Grad-CAM heatmap ─────────────────────
    heatmap_path = ""
    heatmap_url  = ""
    try:
        best_idx         = CLASS_LABELS.index(disease)
        cam              = get_gradcam(_ML_MODEL, input_tensor, best_idx)
        heatmap_bytes    = overlay_heatmap(image, cam)
        heatmap_filename = f"{uuid.uuid4().hex}.png"
        heatmap_save     = HEATMAP_DIR / heatmap_filename
        heatmap_save.write_bytes(heatmap_bytes)
        heatmap_path = f"/uploads/heatmaps/{heatmap_filename}"
        heatmap_url  = f"http://localhost:8000{heatmap_path}"
    except Exception as exc:
        # Grad-CAM is non-critical; log and continue without it
        logging.warning("Grad-CAM heatmap generation failed: %s", exc)

    # ── 10. Persist report to database ────────────────────────
    db_report = ReportModel(
        user_id      = current_user.id,
        image_path   = f"/uploads/{unique_filename}",
        disease      = disease,
        confidence   = round(confidence, 4),
        report_text  = report,
        heatmap_path = heatmap_path or None,
    )
    db.add(db_report)
    db.commit()

    # ── 11. Return response ───────────────────────────────────
    return PredictionResponse(
        disease     = disease,
        confidence  = round(confidence, 4),
        report      = report,
        heatmap_url = heatmap_url,
    )


@app.get(
    "/reports",
    response_model=List[ReportOut],
    tags=["Reports"],
)
async def get_reports(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all saved reports for the currently authenticated user,
    newest first. Each row includes `image_url` (absolute) and
    `report_text` (full radiology text) for modal display.

    Requires: Authorization: Bearer <token>
    """
    base_url = str(request.base_url).rstrip("/")
    rows = (
        db.query(ReportModel)
        .filter(ReportModel.user_id == current_user.id)
        .order_by(ReportModel.created_at.desc())
        .all()
    )
    return [ReportOut.from_orm_with_url(r, base_url) for r in rows]


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
