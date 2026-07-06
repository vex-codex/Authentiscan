from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from database import Base

# ---------------- USER TABLE ----------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

# ---------------- PREDICTION TABLE ----------------
class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)

    product_name = Column(String)
    review = Column(String)

    review_prediction = Column(String)
    image_prediction = Column(String)

    confidence = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())