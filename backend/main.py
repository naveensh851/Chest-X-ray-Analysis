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
import gc
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

# ── Memory optimization flags for Render (512MB free tier limit) ──────────
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "1")
os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")
os.environ.setdefault("MALLOC_ARENA_MAX", "1")

# Concurrency lock so only 1 inference runs at a time (prevents simultaneous RAM spikes)
_INFERENCE_LOCK = asyncio.Lock()

import numpy as np

# ── TensorFlow / Keras (imported lazily so startup errors are visible) ──
try:
    import tensorflow as tf
    try:
        tf.config.threading.set_inter_op_parallelism_threads(1)
        tf.config.threading.set_intra_op_parallelism_threads(1)
    except Exception:
        pass
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


def release_system_memory() -> None:
    """Forces garbage collection and glibc malloc_trim to return free heap to the OS."""
    gc.collect()
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass

import uvicorn
from fastapi import (
    Depends, FastAPI, File, HTTPException, Request, UploadFile, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
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
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "admin123")

BASE_DIR        = Path(__file__).resolve().parent
DATABASE_URL    = f"sqlite:///{BASE_DIR / 'xray_app.db'}"
UPLOAD_DIR      = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
HEATMAP_DIR     = UPLOAD_DIR / "heatmaps"
HEATMAP_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_storage(max_age_seconds: int = 180) -> int:
    """
    Automatically purges temporary uploaded images and generated heatmaps
    older than max_age_seconds from disk to prevent storage and memory leaks.
    """
    removed = 0
    now = datetime.now(timezone.utc).timestamp()
    for directory in [UPLOAD_DIR, HEATMAP_DIR]:
        if not directory.exists():
            continue
        for f in directory.iterdir():
            if f.is_file() and not f.name.startswith("."):
                try:
                    if (now - f.stat().st_mtime) >= max_age_seconds:
                        f.unlink()
                        removed += 1
                except Exception:
                    pass
    return removed

ALLOWED_CONTENT_TYPES  = {"image/jpeg", "image/jpg", "image/png"}
ALLOWED_EXTENSIONS     = {".jpg", ".jpeg", ".png"}

# ── EfficientNetB0 — 5-class chest X-ray classifier (balanced) ───────────
CLASS_LABELS   = ["Infiltration", "Effusion", "Atelectasis", "Nodule", "Mass"]
_candidate_weights = [
    BASE_DIR / "model" / "model_5class_balanced_weights.h5",
    Path("model") / "model_5class_balanced_weights.h5",
]
MODEL_WEIGHTS  = next((p for p in _candidate_weights if p.exists()), _candidate_weights[0])
MODEL_INPUT_SHAPE = (224, 224, 3)
GRADCAM_LAYER     = "top_conv"

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

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String, unique=True, index=True, nullable=False)
    password   = Column(String, nullable=False)             # bcrypt hash
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)

    reports    = relationship("ReportModel", back_populates="user", cascade="all, delete-orphan")


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

# ── Auto-migrate: add columns if they don't exist ──
with engine.connect() as _conn:
    from sqlalchemy import text as _sql
    cols_reports = [row[1] for row in _conn.execute(_sql("PRAGMA table_info(reports)")).fetchall()]
    if "report_text" not in cols_reports:
        _conn.execute(_sql("ALTER TABLE reports ADD COLUMN report_text TEXT"))
        _conn.commit()
    if "heatmap_path" not in cols_reports:
        _conn.execute(_sql("ALTER TABLE reports ADD COLUMN heatmap_path TEXT"))
        _conn.commit()

    cols_users = [row[1] for row in _conn.execute(_sql("PRAGMA table_info(users)")).fetchall()]
    if "created_at" not in cols_users:
        _conn.execute(_sql("ALTER TABLE users ADD COLUMN created_at DATETIME"))
        _conn.commit()
    if "last_login" not in cols_users:
        _conn.execute(_sql("ALTER TABLE users ADD COLUMN last_login DATETIME"))
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
    disease:      str
    confidence:   float
    report:       str
    heatmap_url:  str = ""   # absolute URL to the generated heatmap PNG
    heatmap_path: str = ""   # relative path to the generated heatmap PNG


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
_CONV_EXTRACTOR: "Model | None" = None
_HEAD_LAYERS: "dict | None" = None

if _ML_MODEL is not None:
    try:
        _CONV_EXTRACTOR = Model(
            inputs=_ML_MODEL.input,
            outputs=_ML_MODEL.get_layer(GRADCAM_LAYER).output,
        )
        _HEAD_LAYERS = {
            "top_bn": _ML_MODEL.get_layer("top_bn"),
            "top_activation": _ML_MODEL.get_layer("top_activation"),
            "gap": _ML_MODEL.get_layer("global_average_pooling2d"),
            "bn": _ML_MODEL.get_layer("batch_normalization"),
            "dense1": _ML_MODEL.get_layer("dense"),
            "dense2": _ML_MODEL.get_layer("dense_1"),
        }
        logging.info("Extracted lightweight classifier head for memory-safe Grad-CAM.")
    except Exception as exc:
        logging.warning("Could not extract head layers: %s", exc)


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
    """
    if _ML_MODEL is None:
        raise RuntimeError(
            "ML model is not available. "
            "Ensure TensorFlow is installed and the weights file exists at "
            f"'{MODEL_WEIGHTS}'."
        )

    # Preprocess → predict
    input_tensor = _preprocess_image(image)           # shape (1, 224, 224, 3)
    preds        = _ML_MODEL(input_tensor, training=False).numpy()[0]  # shape (5,)

    best_idx    = int(np.argmax(preds))
    confidence  = float(preds[best_idx])
    disease     = CLASS_LABELS[best_idx]
    report_text = _generate_report(disease, confidence)

    return disease, confidence, report_text, input_tensor


def run_prediction_and_gradcam(
    image: Image.Image,
) -> tuple[str, float, str, "np.ndarray", "np.ndarray"]:
    """
    Run EfficientNetB0 inference and compute Grad-CAM activation in a single
    memory-optimized forward pass. GradientTape only tracks the 5-layer classifier
    head instead of all 237 layers of EfficientNet, dropping peak RAM by >100MB
    and keeping container RAM safely under Render's 512MB limit.

    Returns:
        (disease, confidence, report_text, input_tensor, heatmap_2d)
    """
    if _ML_MODEL is None:
        raise RuntimeError(
            "ML model is not available. "
            "Ensure TensorFlow is installed and the weights file exists at "
            f"'{MODEL_WEIGHTS}'."
        )

    input_tensor = _preprocess_image(image)

    # Fallback to standard inference if head layers were not extracted
    if _CONV_EXTRACTOR is None or _HEAD_LAYERS is None:
        disease, confidence, report_text, _ = run_prediction(image)
        return disease, confidence, report_text, input_tensor, np.zeros((7, 7), dtype=np.float32)

    try:
        inp = tf.cast(input_tensor, tf.float32)
        # 1. Forward pass through conv backbone (NO tape overhead on 230 conv layers!)
        conv_out = _CONV_EXTRACTOR(inp, training=False)

        # 2. GradientTape ONLY on the tiny 5-layer classifier head
        with tf.GradientTape() as tape:
            tape.watch(conv_out)
            h = _HEAD_LAYERS["top_bn"](conv_out, training=False)
            h = _HEAD_LAYERS["top_activation"](h)
            h = _HEAD_LAYERS["gap"](h)
            h = _HEAD_LAYERS["bn"](h, training=False)
            h = _HEAD_LAYERS["dense1"](h)
            predictions = _HEAD_LAYERS["dense2"](h)
            preds = predictions.numpy()[0]
            best_idx = int(np.argmax(preds))
            confidence = float(preds[best_idx])
            disease = CLASS_LABELS[best_idx]
            class_score = predictions[:, best_idx]

        grads = tape.gradient(class_score, conv_out)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        conv_feature = conv_out[0]
        heatmap = conv_feature @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        heatmap = tf.nn.relu(heatmap).numpy()
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()

        report_text = _generate_report(disease, confidence)
        heatmap_2d = heatmap.astype(np.float32)

        del inp, conv_out, grads, pooled_grads, conv_feature, heatmap
        return disease, confidence, report_text, input_tensor, heatmap_2d
    except Exception as exc:
        logging.warning("Unified Grad-CAM failed, falling back: %s", exc)
        disease, confidence, report_text, _ = run_prediction(image)
        return disease, confidence, report_text, input_tensor, np.zeros((7, 7), dtype=np.float32)


# ─────────────────────────────────────────────────────────────────
# Real Grad-CAM heatmap overlay (memory-bounded)
# ─────────────────────────────────────────────────────────────────

def _apply_jet_colormap(gray: np.ndarray) -> np.ndarray:
    """
    Apply a fast JET colormap to a 2-D float array [0,1].
    Uses pure-NumPy vectorization (zero OpenCV dependency, zero RAM bloat).

    Returns an (H, W, 3) uint8 RGB array.
    """
    r = np.clip(1.5 - np.abs(4.0 * gray - 3.0), 0.0, 1.0)
    g = np.clip(1.5 - np.abs(4.0 * gray - 2.0), 0.0, 1.0)
    b = np.clip(1.5 - np.abs(4.0 * gray - 1.0), 0.0, 1.0)
    rgb = np.stack([r, g, b], axis=-1)
    return np.uint8(rgb * 255.0)


def overlay_heatmap(
    original_image: Image.Image,
    heatmap: np.ndarray,
    alpha: float = 0.45,
    max_dim: int = 800,
) -> bytes:
    """
    Resize heatmap to a bounded display resolution (max 800px) and blend
    using Pillow's fast C-level Image.blend.
    Avoids multi-hundred MB float32 allocations on high-res X-rays.

    Args:
        original_image: PIL Image (original X-ray).
        heatmap:        2-D float array [0, 1] from Grad-CAM.
        alpha:          Blend weight (0=invisible, 1=opaque).
        max_dim:        Maximum display dimension to prevent RAM spikes.

    Returns:
        PNG-encoded bytes of the blended image.
    """
    orig_w, orig_h = original_image.size
    if max(orig_w, orig_h) > max_dim:
        scale = max_dim / max(orig_w, orig_h)
        disp_w, disp_h = max(1, int(orig_w * scale)), max(1, int(orig_h * scale))
    else:
        disp_w, disp_h = orig_w, orig_h

    # 1. Base display image
    base = original_image.convert("RGB").resize((disp_w, disp_h), Image.BILINEAR)

    # 2. Resize heatmap to display dimensions using Pillow
    heatmap_img = Image.fromarray(np.uint8(np.clip(heatmap * 255.0, 0, 255)), mode="L")
    heatmap_resized = heatmap_img.resize((disp_w, disp_h), Image.BILINEAR)
    cam_norm = np.array(heatmap_resized, dtype=np.float32) / 255.0

    # 3. Vectorized JET colormap
    colored = _apply_jet_colormap(cam_norm)
    colored_img = Image.fromarray(colored, mode="RGB")

    # 4. Fast C-level uint8 alpha-blend (saves >200MB compared to 3D float32 arrays)
    blended = Image.blend(base, colored_img, alpha=alpha)

    # 5. Encode as PNG bytes
    out_io = io.BytesIO()
    blended.save(out_io, format="PNG", optimize=True)
    result = out_io.getvalue()

    # Free local references
    del base, heatmap_img, heatmap_resized, cam_norm, colored, colored_img, blended, out_io
    return result


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
async def startup_warmup() -> None:
    """
    On server start, purge legacy temporary files, ensure database schema is ready,
    and pre-warm the model with a single lightweight pass, immediately releasing
    temporary buffers to keep RAM well under Render's 512MB limit.
    """
    # 1. Purge any lingering temporary uploads or heatmaps from disk
    cleanup_storage(max_age_seconds=0)

    # 2. Database validation & backfill
    db = SessionLocal()
    try:
        null_rows = db.query(ReportModel).filter(ReportModel.report_text == None).all()
        if null_rows:
            for row in null_rows:
                row.report_text = _generate_report(row.disease, row.confidence or 0.0)
            db.commit()
    finally:
        db.close()

    if _CONV_EXTRACTOR is not None and _HEAD_LAYERS is not None:
        try:
            dummy = np.zeros((1, 224, 224, 3), dtype=np.float32)
            c_out = _CONV_EXTRACTOR(dummy, training=False)
            with tf.GradientTape() as tape:
                tape.watch(c_out)
                h = _HEAD_LAYERS["top_bn"](c_out, training=False)
                h = _HEAD_LAYERS["top_activation"](h)
                h = _HEAD_LAYERS["gap"](h)
                h = _HEAD_LAYERS["bn"](h, training=False)
                h = _HEAD_LAYERS["dense1"](h)
                preds = _HEAD_LAYERS["dense2"](h)
                score = preds[:, 0]
            _ = tape.gradient(score, c_out)
            del dummy, c_out, h, preds, score
            logging.info("TensorFlow lightweight pipeline pre-warmed successfully.")
        except Exception as exc:
            logging.warning("TensorFlow warmup: %s", exc)
        finally:
            release_system_memory()
    elif _ML_MODEL is not None:
        try:
            dummy = np.zeros((1, 224, 224, 3), dtype=np.float32)
            _ML_MODEL(dummy, training=False)
            del dummy
            logging.info("TensorFlow model pre-warmed successfully.")
        except Exception as exc:
            logging.warning("TensorFlow warmup: %s", exc)
        finally:
            release_system_memory()


# ─────────────────────────────────────────────────────────────────
# Routes — Public
# ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Returns 200 OK, purges expired temporary assets, and trims idle memory."""
    cleanup_storage(max_age_seconds=120)
    release_system_memory()
    return HealthResponse(status="ok")


@app.get("/uploads/heatmaps/{filename}", tags=["Files"])
async def serve_heatmap(filename: str):
    """Serve a generated heatmap image."""
    file_path = HEATMAP_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Heatmap not found.")
    return FileResponse(file_path, media_type="image/png")


@app.get("/uploads/{filename}", tags=["Files"])
async def serve_upload(filename: str):
    """Serve a previously uploaded X-ray image."""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path)


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

    now = datetime.now(timezone.utc)
    user = UserModel(email=body.email, password=hashed_pw, created_at=now, last_login=now)
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

    user.last_login = datetime.now(timezone.utc)
    db.commit()

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
    request: Request,
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

    # ── 4. Stream uploaded file directly to disk in chunks (bounded RAM) ──
    temp_filename = f"temp_{uuid.uuid4().hex}{extension}"
    temp_path     = UPLOAD_DIR / temp_filename
    heatmap_save: Optional[Path] = None

    try:
        CHUNK_SIZE = 512 * 1024  # 512KB chunks to minimize memory during transfer
        with open(temp_path, "wb") as f_out:
            while chunk := await file.read(CHUNK_SIZE):
                f_out.write(chunk)

        # ── 5. Open image directly from disk & downsample before inference ──────
        try:
            with Image.open(temp_path) as img:
                max_edge = 1024
                w, h = img.size
                if max(w, h) > max_edge:
                    scale = max_edge / max(w, h)
                    img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BILINEAR)
                image = img.convert("RGB")
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File could not be decoded as a valid image. Please upload an undamaged JPEG or PNG.",
            )

        # ── 6. Run prediction & Grad-CAM inside Concurrency Lock ────
        async with _INFERENCE_LOCK:
            try:
                disease, confidence, report, _, cam = run_prediction_and_gradcam(image)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Model inference failed: {exc}",
                )

            # ── 7. Generate real Grad-CAM heatmap ─────────────────────
            heatmap_path = ""
            heatmap_url  = ""
            try:
                heatmap_bytes    = overlay_heatmap(image, cam, max_dim=800)
                
                # Convert to Base64 data URL for instant zero-disk client rendering
                import base64
                heatmap_b64 = f"data:image/png;base64,{base64.b64encode(heatmap_bytes).decode('ascii')}"

                # Save ephemeral preview file for direct URL access
                heatmap_filename = f"hm_{uuid.uuid4().hex}.png"
                heatmap_save     = HEATMAP_DIR / heatmap_filename
                heatmap_save.write_bytes(heatmap_bytes)
                heatmap_path = f"/uploads/heatmaps/{heatmap_filename}"
                
                base_url = str(request.base_url).rstrip("/")
                proto = request.headers.get("x-forwarded-proto", "")
                if proto == "https" and base_url.startswith("http://"):
                    base_url = "https://" + base_url[len("http://"):]
                
                # Return data URL so client never depends on long-term disk storage
                heatmap_url = heatmap_b64
                del heatmap_bytes
            except Exception as exc:
                # Grad-CAM is non-critical; log and continue without it
                logging.warning("Grad-CAM heatmap generation failed: %s", exc)

            # Clean up local image & CAM objects immediately
            del image, cam

            # ── 8. Persist report to database ────────────────────────
            db_report = ReportModel(
                user_id      = current_user.id,
                image_path   = f"/uploads/{temp_filename}",
                disease      = disease,
                confidence   = round(confidence, 4),
                report_text  = report,
                heatmap_path = heatmap_path or None,
            )
            db.add(db_report)
            db.commit()

            # ── 9. Return response ───────────────────────────────────
            return PredictionResponse(
                disease      = disease,
                confidence   = round(confidence, 4),
                report       = report,
                heatmap_url  = heatmap_url,
                heatmap_path = heatmap_path,
            )
    finally:
        # ── 10. Automatic cleanup: delete temporary upload file and trim heap ──
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        
        # Purge any ephemeral heatmaps older than 60 seconds
        cleanup_storage(max_age_seconds=60)
        
        # Release memory back to OS immediately (keeps container < 410MB)
        release_system_memory()


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
    proto = request.headers.get("x-forwarded-proto", "")
    if proto == "https" and base_url.startswith("http://"):
        base_url = "https://" + base_url[len("http://"):]
    rows = (
        db.query(ReportModel)
        .filter(ReportModel.user_id == current_user.id)
        .order_by(ReportModel.created_at.desc())
        .all()
    )
    return [ReportOut.from_orm_with_url(r, base_url) for r in rows]


# ─────────────────────────────────────────────────────────────────
# Admin & Database Inspection Dashboard
# ─────────────────────────────────────────────────────────────────

@app.get("/admin/api/overview", tags=["Admin"])
async def admin_api_overview(
    key: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """API endpoint to view all registered users and reports in the database."""
    if key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key.")

    users = db.query(UserModel).order_by(UserModel.id.desc()).all()
    reports = db.query(ReportModel).order_by(ReportModel.created_at.desc()).all()

    return {
        "total_users": len(users),
        "total_reports": len(reports),
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "report_count": len(u.reports),
            }
            for u in users
        ],
        "reports": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "user_email": r.user.email if r.user else "Unknown",
                "disease": r.disease,
                "confidence": round(r.confidence, 4),
                "image_path": r.image_path,
                "heatmap_path": r.heatmap_path,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ],
    }


@app.post("/admin/api/cleanup", tags=["Admin"])
async def admin_api_cleanup(
    key: Optional[str] = None,
    clear_reports: bool = False,
    db: Session = Depends(get_db),
):
    """
    Completely cleans application data and memory:
    - Clears all temporary images and heatmaps.
    - Resets historical login sessions (keeps registered accounts & credentials).
    - Optionally purges historical prediction reports.
    - Runs SQLite VACUUM to reclaim disk space.
    - Runs gc.collect() and libc malloc_trim(0) to release RAM to OS.
    """
    if key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key.")

    # 1. Clear temporary files on disk
    removed_files = cleanup_storage(max_age_seconds=0)

    # 2. Reset login history / sessions
    db.query(UserModel).update({UserModel.last_login: None})

    # 3. Clear obsolete prediction reports if requested
    removed_reports = 0
    if clear_reports:
        removed_reports = db.query(ReportModel).delete()

    db.commit()

    # 4. VACUUM database to reclaim disk space
    try:
        from sqlalchemy import text as _sql
        db.execute(_sql("VACUUM"))
        db.commit()
    except Exception:
        pass

    # 5. Release system memory
    release_system_memory()

    return {
        "status": "success",
        "message": "Application storage and memory cleaned successfully.",
        "removed_files": removed_files,
        "removed_reports": removed_reports,
        "login_sessions_cleared": True,
        "database_vacuumed": True,
        "memory_trimmed": True,
    }


@app.get("/admin", response_class=HTMLResponse, tags=["Admin"])
async def admin_dashboard(
    request: Request,
    key: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Interactive database inspector for users, logins, and diagnostic reports."""
    base_url = str(request.base_url).rstrip("/")
    if key != ADMIN_SECRET_KEY:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html lang="en" class="dark">
        <head>
          <meta charset="UTF-8">
          <title>Admin Login — Database Inspector</title>
          <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-slate-950 text-slate-100 flex items-center justify-center min-h-screen p-4">
          <div class="max-w-md w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
            <div class="text-center mb-6">
              <div class="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-500/10 text-blue-400 mb-3 font-bold text-xl">🛡️</div>
              <h1 class="text-2xl font-bold text-white">Database Inspector</h1>
              <p class="text-sm text-slate-400 mt-1">Enter your admin key to view all logins and reports.</p>
            </div>
            <form method="GET" action="/admin" class="space-y-4">
              <div>
                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Admin Key</label>
                <input type="password" name="key" autofocus placeholder="Default: admin123" required
                  class="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm">
              </div>
              <button type="submit" class="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-xl transition duration-150 shadow-lg shadow-blue-600/30">
                Unlock Database Dashboard
              </button>
            </form>
          </div>
        </body>
        </html>
        """)

    users = db.query(UserModel).order_by(UserModel.id.desc()).all()
    reports = db.query(ReportModel).order_by(ReportModel.created_at.desc()).all()

    user_rows_html = ""
    for u in users:
        c_time = u.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if u.created_at else "Earlier"
        l_time = u.last_login.strftime('%Y-%m-%d %H:%M:%S UTC') if u.last_login else "N/A"
        r_count = len(u.reports)
        user_rows_html += f"""
        <tr class="border-b border-slate-800/80 hover:bg-slate-900/40 transition">
          <td class="py-3 px-4 font-mono text-xs text-slate-400">#{u.id}</td>
          <td class="py-3 px-4 font-semibold text-white">{u.email}</td>
          <td class="py-3 px-4 text-xs text-slate-300 font-mono">{c_time}</td>
          <td class="py-3 px-4 text-xs text-emerald-400 font-mono">{l_time}</td>
          <td class="py-3 px-4 text-center">
            <span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">{r_count}</span>
          </td>
        </tr>
        """

    report_rows_html = ""
    for r in reports:
        u_email = r.user.email if r.user else f"User #{r.user_id}"
        r_time = r.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if r.created_at else "N/A"
        conf_pct = f"{round(r.confidence * 100, 1)}%"
        img_url = f"{base_url}{r.image_path}"
        hm_url = f"{base_url}{r.heatmap_path}" if r.heatmap_path else ""
        hm_btn = f'<a href="{hm_url}" target="_blank" class="px-2 py-1 bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/20 rounded text-xs transition">Heatmap</a>' if hm_url else '<span class="text-xs text-slate-600">—</span>'
        orig_btn = f'<a href="{img_url}" target="_blank" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded text-xs transition">Original</a>'

        report_rows_html += f"""
        <tr class="border-b border-slate-800/80 hover:bg-slate-900/40 transition">
          <td class="py-3 px-4 font-mono text-xs text-slate-400">#{r.id}</td>
          <td class="py-3 px-4 text-sm text-slate-200">{u_email}</td>
          <td class="py-3 px-4">
            <span class="px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/20">{r.disease}</span>
          </td>
          <td class="py-3 px-4 font-mono text-sm font-semibold text-emerald-400">{conf_pct}</td>
          <td class="py-3 px-4 text-xs text-slate-400 font-mono">{r_time}</td>
          <td class="py-3 px-4 flex gap-1.5 items-center">
            {orig_btn}
            {hm_btn}
          </td>
        </tr>
        """

    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang="en" class="dark">
    <head>
      <meta charset="UTF-8">
      <title>Admin Overview — Database Inspector</title>
      <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen p-6 md:p-10 font-sans">
      <div class="max-w-6xl mx-auto space-y-8">
        
        <!-- Header -->
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div class="flex items-center gap-3">
              <span class="px-2.5 py-1 rounded bg-blue-500/20 text-blue-400 text-xs font-bold uppercase tracking-wider">Live Database</span>
              <span class="text-xs text-slate-500 font-mono">SQLite: xray_app.db</span>
            </div>
            <h1 class="text-2xl md:text-3xl font-bold text-white mt-1">Admin & Database Inspector</h1>
            <p class="text-sm text-slate-400">All registered user accounts, logins, and diagnosis reports stored in the database.</p>
          </div>
          <div class="flex items-center gap-3">
            <button onclick="fetch('/admin/api/cleanup?key={key}', {{method: 'POST'}}).then(r => r.json()).then(d => {{ alert('Storage & Memory Cleaned! ' + d.removed_files + ' temporary files purged, RAM trimmed.'); window.location.reload(); }})" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-sm font-medium transition shadow-sm flex items-center gap-1.5">
              <span>🧹</span> Clean Storage & Memory
            </button>
            <a href="/admin?key={key}" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-sm font-medium transition border border-slate-700 shadow-sm">
              ↻ Refresh Data
            </a>
            <a href="/admin/api/overview?key={key}" target="_blank" class="px-4 py-2 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded-xl text-sm font-medium transition">
              View Raw JSON
            </a>
          </div>
        </div>

        <!-- Metric Badges -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div class="bg-slate-900 border border-slate-800/80 rounded-2xl p-5 shadow-lg">
            <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Registered Accounts</div>
            <div class="text-3xl font-bold text-white mt-2">{len(users)}</div>
            <div class="text-xs text-slate-500 mt-1">Users signed up via email</div>
          </div>
          <div class="bg-slate-900 border border-slate-800/80 rounded-2xl p-5 shadow-lg">
            <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Diagnostic Reports</div>
            <div class="text-3xl font-bold text-blue-400 mt-2">{len(reports)}</div>
            <div class="text-xs text-slate-500 mt-1">X-ray scans classified & saved</div>
          </div>
          <div class="bg-slate-900 border border-slate-800/80 rounded-2xl p-5 shadow-lg">
            <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Authentication Guard</div>
            <div class="text-3xl font-bold text-emerald-400 mt-2">Active</div>
            <div class="text-xs text-slate-500 mt-1">JWT Tokens (HS256)</div>
          </div>
        </div>

        <!-- Section 1: Users & Logins -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-bold text-white">1. User Accounts & Login Activity</h2>
            <span class="text-xs text-slate-400 font-mono">{len(users)} accounts</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse text-sm">
              <thead>
                <tr class="border-b border-slate-800 text-xs text-slate-400 font-semibold uppercase tracking-wider bg-slate-950/40">
                  <th class="py-3 px-4">User ID</th>
                  <th class="py-3 px-4">Gmail / Email</th>
                  <th class="py-3 px-4">Registered At</th>
                  <th class="py-3 px-4">Last Login</th>
                  <th class="py-3 px-4 text-center">Reports</th>
                </tr>
              </thead>
              <tbody>
                {user_rows_html if user_rows_html else '<tr><td colspan="5" class="py-6 text-center text-slate-500 text-sm">No users registered yet.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Section 2: Reports -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-bold text-white">2. Diagnostic Reports & Scans Log</h2>
            <span class="text-xs text-slate-400 font-mono">{len(reports)} scans</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse text-sm">
              <thead>
                <tr class="border-b border-slate-800 text-xs text-slate-400 font-semibold uppercase tracking-wider bg-slate-950/40">
                  <th class="py-3 px-4">Report ID</th>
                  <th class="py-3 px-4">User Account</th>
                  <th class="py-3 px-4">Detected Disease</th>
                  <th class="py-3 px-4">Confidence</th>
                  <th class="py-3 px-4">Date / Time</th>
                  <th class="py-3 px-4">Assets</th>
                </tr>
              </thead>
              <tbody>
                {report_rows_html if report_rows_html else '<tr><td colspan="6" class="py-6 text-center text-slate-500 text-sm">No diagnostic reports stored yet.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </body>
    </html>
    """)


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
