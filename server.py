from __future__ import annotations

import io
import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker
from jose import jwt
from passlib.context import CryptContext
from fastapi.staticfiles import StaticFiles


ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models"
PRODUCT_MODEL_PATH = Path(os.environ.get("PRODUCT_MODEL_PATH", MODEL_DIR / "fake_product_detector.keras"))
REVIEW_MODEL_PATH = Path(os.environ.get("REVIEW_MODEL_PATH", MODEL_DIR / "review_model.pkl"))
REVIEW_VECTOR_PATH = Path(os.environ.get("REVIEW_VECTOR_PATH", MODEL_DIR / "vectorizer.pkl"))
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:PostgreSQL2026@localhost:5432/fake_review_db",
)

PRODUCT_CLASSES = [
    "adidas_fake",
    "adidas_genuine",
    "gucci_fake",
    "gucci_genuine",
    "lv_fake",
    "lv_genuine",
    "nike_fake",
    "nike_genuine",
    "puma_fake",
    "puma_genuine",
]

Base = declarative_base()


class ScanRecord(Base):
    __tablename__ = "scan_records"

    id = Column(Integer, primary_key=True, index=True)
    scan_type = Column(String(24), nullable=False, index=True)
    verdict = Column(String(32), nullable=False)
    brand = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=True)
    input_summary = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(100), unique=True, nullable=False)

    password = Column(String(255), nullable=False)

class ReviewRequest(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=160)
    review_text: str = Field(..., min_length=5, max_length=5000)
    rating: float | None = Field(default=None, ge=1, le=5)

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    username: str
    password: str


class ModelBundle:
    def __init__(self) -> None:
        self._product_model: Any | None = None
        self._review_model: Any | None = None
        self._review_vectorizer: Any | None = None
        self._lock = threading.Lock()
        self.product_error: str | None = None
        self.review_error: str | None = None

    def product_model(self) -> Any:
        if self._product_model is not None:
            return self._product_model
        if not PRODUCT_MODEL_PATH.exists():
            raise FileNotFoundError(f"Product model missing at {PRODUCT_MODEL_PATH}")
        with self._lock:
            if self._product_model is None:
                try:
                    import tensorflow as tf

                    try:
                        self._product_model = tf.keras.models.load_model(PRODUCT_MODEL_PATH, compile=False)
                    except Exception:
                        self._product_model = build_product_architecture(tf)
                        self._product_model(np.zeros((1, 224, 224, 3), dtype=np.float32))
                        self._product_model.load_weights(PRODUCT_MODEL_PATH)
                    self.product_error = None
                except Exception as exc:  # pragma: no cover - depends on local TF install
                    self.product_error = f"{type(exc).__name__}: {exc}"
                    raise
        return self._product_model

    def review_assets(self) -> tuple[Any, Any]:
        if self._review_model is not None and self._review_vectorizer is not None:
            return self._review_model, self._review_vectorizer
        missing = [str(path.name) for path in (REVIEW_MODEL_PATH, REVIEW_VECTOR_PATH) if not path.exists()]
        if missing:
            raise FileNotFoundError("Missing review artifact(s): " + ", ".join(missing))
        with self._lock:
            if self._review_model is None or self._review_vectorizer is None:
                try:
                    import joblib

                    self._review_model = joblib.load(REVIEW_MODEL_PATH)
                    self._review_vectorizer = joblib.load(REVIEW_VECTOR_PATH)
                    self.review_error = None
                except Exception as exc:  # pragma: no cover - depends on local model files
                    self.review_error = f"{type(exc).__name__}: {exc}"
                    raise
        return self._review_model, self._review_vectorizer


bundle = ModelBundle()
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

SECRET_KEY = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET_KEY"

ALGORITHM = "HS256"
app = FastAPI(title="AuthentiScan API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app = FastAPI(title="AuthentiScan API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# FIXED FRONTEND PATH (ONLY THIS)
FRONTEND_DIR = ROOT.parent / "frontend"

print("Frontend folder:", FRONTEND_DIR)
print("Login exists:", (FRONTEND_DIR / "login.html").exists())

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

engine = None

engine = None
SessionLocal = None
database_error: str | None = "Database check pending"


def init_database() -> None:
    global engine, SessionLocal, database_error
    try:
        connect_args = {"connect_timeout": 2} if DATABASE_URL.startswith("postgresql") else {}
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(bind=engine)
        database_error = None
    except Exception as exc:
        engine = None
        SessionLocal = None
        database_error = f"{type(exc).__name__}: {exc}"


def build_product_architecture(tf: Any) -> Any:
    base_model = tf.keras.applications.MobileNetV2(
        weights=None,
        include_top=False,
        input_shape=(224, 224, 3),
    )
    base_model.trainable = False
    return tf.keras.Sequential(
        [
            tf.keras.layers.Rescaling(1.0 / 255),
            base_model,
            tf.keras.layers.GlobalAveragePooling2D(),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dense(10, activation="softmax"),
        ]
    )


@app.on_event("startup")
def startup() -> None:
    threading.Thread(target=init_database, daemon=True).start()
    if PRODUCT_MODEL_PATH.exists():
        threading.Thread(target=warm_product_model, daemon=True).start()


def warm_product_model() -> None:
    try:
        bundle.product_model()
    except Exception:
        pass


def clean_review(text: str) -> str:
    text = str(text).lower()
    return re.sub(r"[^a-zA-Z ]", "", text)


def label_to_payload(label: str, confidence: float) -> dict[str, Any]:
    brand, authenticity = label.rsplit("_", 1)
    verdict = "Original" if authenticity == "genuine" else "Fake"
    return {
        "label": label,
        "brand": brand.upper() if brand == "lv" else brand.title(),
        "authenticity": authenticity,
        "verdict": verdict,
        "confidence": round(confidence * 100, 2),
    }


def normalize_brand_name(brand: str | None) -> str | None:
    if not brand:
        return None
    value = brand.strip().lower()
    aliases = {"louis vuitton": "lv", "lv": "lv"}
    return aliases.get(value, value)


def save_scan(scan_type: str, verdict: str, brand: str | None, confidence: float | None, input_summary: str, details: dict[str, Any]) -> None:
    if SessionLocal is None:
        return
    session = SessionLocal()
    try:
        session.add(
            ScanRecord(
                scan_type=scan_type,
                verdict=verdict,
                brand=brand,
                confidence=confidence,
                input_summary=input_summary[:500],
                details=details,
            )
        )
        session.commit()
    except SQLAlchemyError:
        session.rollback()
    finally:
        session.close()


@app.get("/")
def login_page():
    return FileResponse(FRONTEND_DIR / "login.html")

@app.get("/dashboard")
def dashboard() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/api/status")
def status() -> dict[str, Any]:
    return {
        "ok": True,
        "database": {
            "connected": database_error is None,
            "url": re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", DATABASE_URL),
            "error": database_error,
        },
        "models": {
            "product": {
                "available": PRODUCT_MODEL_PATH.exists(),
                "path": str(PRODUCT_MODEL_PATH),
                "classes": PRODUCT_CLASSES,
                "error": bundle.product_error,
            },
            "review": {
                "available": REVIEW_MODEL_PATH.exists() and REVIEW_VECTOR_PATH.exists(),
                "model_path": str(REVIEW_MODEL_PATH),
                "vectorizer_path": str(REVIEW_VECTOR_PATH),
                "error": bundle.review_error,
            },
        },
    }


@app.post("/api/detect/product")
async def detect_product(image: UploadFile = File(...), expected_brand: str | None = Form(default=None)) -> dict[str, Any]:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Upload a product image file.")
    try:
        from PIL import Image

        model = bundle.product_model()
        raw = await image.read()
        img = Image.open(io.BytesIO(raw)).convert("RGB").resize((224, 224))
        array = np.expand_dims(np.asarray(img, dtype=np.float32), axis=0)
        prediction = model.predict(array, verbose=0)[0]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Product model failed: {exc}") from exc

    ordered = np.argsort(prediction)[::-1]
    expected_key = normalize_brand_name(expected_brand)
    if expected_key:
        brand_indexes = [
            index
            for index, label in enumerate(PRODUCT_CLASSES)
            if label.startswith(f"{expected_key}_")
        ]
        if not brand_indexes:
            raise HTTPException(status_code=400, detail=f"Unsupported brand: {expected_brand}")
        brand_total = float(sum(prediction[index] for index in brand_indexes)) or 1.0
        top_index = max(brand_indexes, key=lambda index: prediction[index])
        top_label = PRODUCT_CLASSES[int(top_index)]
        top = label_to_payload(top_label, float(prediction[int(top_index)] / brand_total))
        top["raw_model_score"] = round(float(prediction[int(top_index)]) * 100, 2)
        authenticity_scores = {
            PRODUCT_CLASSES[index].rsplit("_", 1)[1]: round(float(prediction[index] / brand_total) * 100, 2)
            for index in brand_indexes
        }
        decision_mode = "expected_brand"
    else:
        top_label = PRODUCT_CLASSES[int(ordered[0])]
        top = label_to_payload(top_label, float(prediction[int(ordered[0])]))
        top["raw_model_score"] = top["confidence"]
        authenticity_scores = None
        decision_mode = "auto_brand"
    alternatives = [
        label_to_payload(PRODUCT_CLASSES[int(index)], float(prediction[int(index)]))
        for index in ordered[:5]
    ]
    brand_match = None
    if expected_brand:
        brand_match = top["brand"].lower() == expected_brand.strip().lower()

    response = {
        **top,
        "expected_brand": expected_brand,
        "brand_match": brand_match,
        "decision_mode": decision_mode,
        "authenticity_scores": authenticity_scores,
        "top_predictions": alternatives,
        "filename": image.filename,
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
    }
    save_scan("product", top["verdict"], top["brand"], top["confidence"], image.filename or "product image", response)
    return response


@app.post("/api/detect/review")
def detect_review(payload: ReviewRequest) -> dict[str, Any]:
    try:
        model, vectorizer = bundle.review_assets()
        from scipy.sparse import hstack
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Review model failed: {exc}") from exc

    review_clean = clean_review(payload.review_text)
    length = len(review_clean.split())
    exclamation = payload.review_text.count("!")
    caps = sum(1 for word in payload.review_text.split() if word.isupper())
    product_score = float(payload.rating or 3)
    text_vector = vectorizer.transform([review_clean])
    extra = np.array([[length, exclamation, caps, product_score]])
    final_vector = hstack([text_vector, extra])
    fake_probability = float(model.predict_proba(final_vector)[0][1])

    if fake_probability > 0.70:
        verdict = "Fake"
        tone = "danger"
    elif fake_probability > 0.40:
        verdict = "Suspicious"
        tone = "warning"
    else:
        verdict = "Original"
        tone = "safe"

    response = {
        "verdict": verdict,
        "tone": tone,
        "confidence": round(max(fake_probability, 1 - fake_probability) * 100, 2),
        "fake_probability": round(fake_probability * 100, 2),
        "signals": {
            "word_count": length,
            "exclamation_count": exclamation,
            "uppercase_words": caps,
            "rating_used": product_score,
        },
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
    }
    save_scan("review", verdict, None, response["confidence"], payload.review_text, response)
    return response


@app.get("/api/history")
def history(limit: int = 20) -> dict[str, Any]:
    if SessionLocal is None:
        return {"items": [], "database_connected": False, "error": database_error}
    session = SessionLocal()
    try:
        rows = session.query(ScanRecord).order_by(ScanRecord.created_at.desc()).limit(min(limit, 100)).all()
        return {
            "database_connected": True,
            "items": [
                {
                    "id": row.id,
                    "type": row.scan_type,
                    "verdict": row.verdict,
                    "brand": row.brand,
                    "confidence": row.confidence,
                    "input_summary": row.input_summary,
                    "created_at": row.created_at.isoformat() + "Z",
                    "details": row.details,
                }
                for row in rows
            ],
        }
    finally:
        session.close()


@app.get("/api/export/schema")
def export_schema() -> dict[str, Any]:
    return {
        "postgres_table": "scan_records",
        "columns": {
            "id": "integer primary key",
            "scan_type": "product | review",
            "verdict": "Original | Fake | Suspicious",
            "brand": "predicted brand for products",
            "confidence": "percentage score",
            "input_summary": "filename or review excerpt",
            "details": "full JSON prediction payload",
            "created_at": "UTC timestamp",
        },
    }

@app.post("/register")
def register(user: RegisterRequest):

    if SessionLocal is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    db = SessionLocal()

    try:
        existing = db.query(User).filter(
            User.username == user.username
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Username already exists"
            )

        hashed_password = pwd_context.hash(user.password)

        new_user = User(
            username=user.username,
            password=hashed_password
        )

        db.add(new_user)
        db.commit()

        return {
            "message": "Registration successful"
        }

    finally:
        db.close()

@app.post("/login")
def login(user: LoginRequest):

    if SessionLocal is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    db = SessionLocal()

    try:
        account = db.query(User).filter(
            User.username == user.username
        ).first()

        if account is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )

        if not pwd_context.verify(user.password, account.password):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )

        token = jwt.encode(
            {"sub": account.username},
            SECRET_KEY,
            algorithm=ALGORITHM
        )

        return {
            "access_token": token,
            "token_type": "bearer"
        }

    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="127.0.0.1", port=int(os.environ.get("PORT", "4174")), reload=False)
