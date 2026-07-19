from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Create data directory
os.makedirs("data", exist_ok=True)

# Database URL
DATABASE_URL = "sqlite:///./data/reviewshield.db"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database - import here to avoid circular imports"""
    from models import Base
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")