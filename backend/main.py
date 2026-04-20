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
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

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

DATABASE_URL    = "sqlite:///./xray_app.db"
UPLOAD_DIR      = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_CONTENT_TYPES  = {"image/jpeg", "image/jpg", "image/png"}
ALLOWED_EXTENSIONS     = {".jpg", ".jpeg", ".png"}
SIMULATED_DELAY_SECS   = 1.5

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

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_path  = Column(String, nullable=False)
    disease     = Column(String, nullable=False)
    confidence  = Column(Float, nullable=False)
    report_text = Column(Text, nullable=True)   # full radiology report text (TEXT for large content)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user        = relationship("UserModel", back_populates="reports")


# Create all tables on startup
Base.metadata.create_all(bind=engine)

# ── Auto-migrate: add report_text column if it doesn't exist (SQLite) ──
with engine.connect() as _conn:
    from sqlalchemy import text as _sql
    cols = [row[1] for row in _conn.execute(_sql("PRAGMA table_info(reports)")).fetchall()]
    if "report_text" not in cols:
        _conn.execute(_sql("ALTER TABLE reports ADD COLUMN report_text TEXT"))
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
    disease:    str
    confidence: float
    report:     str


class ReportOut(BaseModel):
    id:          int
    image_path:  str
    disease:     str
    confidence:  float
    report_text: str | None = None
    created_at:  datetime

    # Computed field — full URL the frontend can use directly in <img src=...>
    image_url: str = ""

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_url(cls, obj: "ReportModel", base_url: str) -> "ReportOut":
        # from_attributes=True is required in Pydantic v2 when validating
        # SQLAlchemy ORM objects — without it, lazy-loaded fields return None.
        inst = cls.model_validate(obj, from_attributes=True)
        inst.image_url = f"{base_url}{obj.image_path}"
        return inst



class HealthResponse(BaseModel):
    status: str


# ─────────────────────────────────────────────────────────────────
# Dummy ML prediction catalogue
# ─────────────────────────────────────────────────────────────────

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


def run_prediction(image: Image.Image) -> tuple[str, float, str]:
    """
    Placeholder ML inference. Replace with real model in production.

    Args:
        image: PIL Image object (already validated and opened).

    Returns:
        Tuple of (disease_name, confidence_score, report_text)
    """
    random.seed(image.size[0] * image.size[1])
    result = random.choice(DISEASE_CATALOGUE)
    return result["disease"], result["confidence"], result["report"]


# ─────────────────────────────────────────────────────────────────
# App initialisation
# ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI X-ray Diagnosis API (v2)",
    description="Backend for the AI-powered chest X-ray classifier with JWT auth and report storage.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
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
    (e.g. created before the column existed) and fill them with the
    matching text from DISEASE_CATALOGUE. Falls back to a generic template.
    """
    catalogue_map = {item["disease"]: item["report"] for item in DISEASE_CATALOGUE}
    db = SessionLocal()
    try:
        null_rows = db.query(ReportModel).filter(ReportModel.report_text == None).all()
        if null_rows:
            for row in null_rows:
                row.report_text = catalogue_map.get(
                    row.disease,
                    (
                        "PRELIMINARY RADIOLOGY REPORT\n"
                        "─────────────────────────────\n"
                        f"Findings: X-ray analysis indicates findings consistent with {row.disease}.\n\n"
                        "Impression: Clinical correlation and specialist review recommended.\n\n"
                        "⚠ This is an AI-generated draft. A licensed radiologist must\n"
                        "  review and sign off before any clinical decision is made."
                    ),
                )
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

    # ── 7. Simulate processing delay (remove in production) ────
    await asyncio.sleep(SIMULATED_DELAY_SECS)

    # ── 8. Run prediction ──────────────────────────────────────
    try:
        disease, confidence, report = run_prediction(image)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model inference failed: {exc}",
        )

    # ── 9. Persist report to database ─────────────────────────
    db_report = ReportModel(
        user_id     = current_user.id,
        image_path  = f"/uploads/{unique_filename}",
        disease     = disease,
        confidence  = round(confidence, 4),
        report_text = report,   # save full radiology text for modal display
    )
    db.add(db_report)
    db.commit()

    # ── 10. Return response ────────────────────────────────────
    return PredictionResponse(
        disease    = disease,
        confidence = round(confidence, 4),
        report     = report,
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
