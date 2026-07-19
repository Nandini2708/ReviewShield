from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict

Base = declarative_base()

# ============ SQLAlchemy Models ============

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # AI Analysis
    spam_score = Column(Float, default=0)
    is_spam = Column(Boolean, default=False)
    authenticity_score = Column(Integer, default=0)
    sentiment = Column(String(20), default="neutral")
    spam_reasons = Column(Text, default="[]")
    
    # Status
    status = Column(String(20), default="pending")  # pending, approved, rejected


class Business(Base):
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(200), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# change above

class ReviewRequest(Base):
    __tablename__ = "review_requests"

    id = Column(Integer, primary_key=True, index=True)

    customer_name = Column(String(100), nullable=False)

    customer_email = Column(String(100), nullable=False)

    order_id = Column(String(100), nullable=False)

    product_name = Column(String(100), nullable=True)

    request_token = Column(String(255), unique=True, nullable=False)

    status = Column(String(30), default="Pending")

    review_submitted = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============ Pydantic Models (API) ============

class ReviewCreate(BaseModel):
    customer_name: str
    email: EmailStr
    rating: int
    review_text: str
    token: str | None = None

class ReviewResponse(BaseModel):
    id: int
    customer_name: str
    rating: int
    review_text: str
    created_at: datetime
    is_spam: bool
    authenticity_score: int
    sentiment: str
    status: str
    
    class Config:
        from_attributes = True


class SpamAnalysisResponse(BaseModel):
    is_spam: bool
    spam_score: int
    confidence: int
    reasons: list
    sentiment: str
    recommendation: str


class ReviewStats(BaseModel):
    total_reviews: int
    verified_reviews: int
    spam_reviews: int
    pending_reviews: int
    average_rating: float
    sentiment_breakdown: dict



#change below
class UserRegister(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ReviewRequestCreate(BaseModel):

    customer_name: str

    customer_email: EmailStr

    order_id: str

    product_name: str


class ReviewRequestResponse(BaseModel):

    id: int

    customer_name: str

    customer_email: EmailStr

    order_id: str

    product_name: str

    status: str
    review_link: str

    # review_submitted: bool

    created_at: datetime

    class Config:
        from_attributes = True