from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import json
import uuid



from database import engine, get_db, init_db
from models import ( Review, ReviewCreate, ReviewResponse, SpamAnalysisResponse, ReviewStats, User, UserRegister, UserLogin, ReviewRequest, ReviewRequestCreate, ReviewRequestResponse )
from spam_detector import spam_detector
from auth import (
    get_password_hash,
    verify_password,
    create_access_token
)

from email_service import send_review_email
from review_link import generate_review_link
#change above


# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(title="ReviewShield API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ API Endpoints ============

@app.get("/")
def root():
    return {
        "message": "ReviewShield API is running!",
        "status": "active",
        "version": "1.0.0"
    }

@app.post("/api/submit-review", response_model=ReviewResponse)
def submit_review(review: ReviewCreate, db: Session = Depends(get_db)):

 request = None
 if review.token:

    request = db.query(ReviewRequest).filter(
        ReviewRequest.request_token == review.token
    ).first()

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Invalid review link"
        )

    if request.review_submitted:
        raise HTTPException(
            status_code=400,
            detail="Review already submitted"
        )
    
    
    # Run AI spam detection
    spam_result = spam_detector.detect(review.review_text, review.email)
    


    
    # Save to database
    db_review = Review(
        customer_name=review.customer_name,
        email=review.email,
        rating=review.rating,
        review_text=review.review_text,
        spam_score=spam_result['spam_score'],
        is_spam=spam_result['is_spam'],
        authenticity_score=spam_result['confidence'],
        sentiment=spam_result['sentiment'],
        spam_reasons=json.dumps(spam_result['reasons']),
        status="approved" if not spam_result['is_spam'] else "pending"
    )
    
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
 if request:

    request.review_submitted = True

    request.status = "Completed"

    db.commit()
    
 return ReviewResponse(
        id=db_review.id,
        customer_name=db_review.customer_name,
        rating=db_review.rating,
        review_text=db_review.review_text,
        created_at=db_review.created_at or datetime.utcnow(),
        is_spam=db_review.is_spam,
        authenticity_score=db_review.authenticity_score,
        sentiment=db_review.sentiment,
        status=db_review.status
    )

@app.post("/api/analyze-spam", response_model=SpamAnalysisResponse)
def analyze_spam(review: ReviewCreate):
    """Test AI spam detection without saving to database"""
    result = spam_detector.detect(review.review_text, review.email)
    return SpamAnalysisResponse(**result)

@app.get("/api/reviews", response_model=List[ReviewResponse])
def get_reviews(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all reviews"""
    reviews = db.query(Review).order_by(Review.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        ReviewResponse(
            id=r.id,
            customer_name=r.customer_name,
            rating=r.rating,
            review_text=r.review_text,
            created_at=r.created_at or datetime.utcnow(),
            is_spam=r.is_spam,
            authenticity_score=r.authenticity_score,
            sentiment=r.sentiment,
            status=r.status
        ) for r in reviews
    ]

@app.get("/api/stats", response_model=ReviewStats)
def get_stats(db: Session = Depends(get_db)):
    """Get review statistics"""
    all_reviews = db.query(Review).all()
    
    total = len(all_reviews)
    verified = len([r for r in all_reviews if not r.is_spam and r.status == "approved"])
    spam = len([r for r in all_reviews if r.is_spam])
    pending = len([r for r in all_reviews if r.status == "pending"])
    
    # Average rating (only verified reviews)
    ratings = [r.rating for r in all_reviews if not r.is_spam]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Sentiment breakdown
    sentiment_breakdown = {
        "positive": len([r for r in all_reviews if r.sentiment == "positive"]),
        "negative": len([r for r in all_reviews if r.sentiment == "negative"]),
        "neutral": len([r for r in all_reviews if r.sentiment == "neutral"])
    }
    
    return ReviewStats(
        total_reviews=total,
        verified_reviews=verified,
        spam_reviews=spam,
        pending_reviews=pending,
        average_rating=round(avg_rating, 1),
        sentiment_breakdown=sentiment_breakdown
    )

@app.delete("/api/reviews/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    """Delete a review"""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    db.delete(review)
    db.commit()
    
    return {"message": "Review deleted successfully"}
  

#change below


@app.post("/api/review-requests/create", response_model=ReviewRequestResponse)
def create_review_request(
    request: ReviewRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):

    token = str(uuid.uuid4())
   

    # review_link = f"http://localhost:5500/index.html?token={token}"

    review_link = generate_review_link(token)

    db_request = ReviewRequest(
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        order_id=request.order_id,
        product_name=request.product_name,
        request_token=token,
        status="pending"
       
        # email_sent=True
    )

    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    background_tasks.add_task(
        send_review_email,
        request.customer_name,
        request.customer_email,
        review_link
    )

    db_request.status = "sent"
    db.commit()

    # return db_request
    return ReviewRequestResponse(
    id=db_request.id,
    customer_name=db_request.customer_name,
    customer_email=db_request.customer_email,
    order_id=db_request.order_id,
    product_name=db_request.product_name,
    status=db_request.status,
    created_at=db_request.created_at,
    review_link=review_link
)


@app.get("/api/review-request-stats")
def review_request_stats(db: Session = Depends(get_db)):

    total = db.query(ReviewRequest).count()

    pending = db.query(ReviewRequest).filter(
        ReviewRequest.status == "pending"
    ).count()

    sent = db.query(ReviewRequest).filter(
        ReviewRequest.status == "sent"
    ).count()

    completed = db.query(ReviewRequest).filter(
        ReviewRequest.status == "Completed"
    ).count()

    return {
        "total": total,
        "pending": pending,
        "sent": sent,
        "completed": completed
    }

@app.post("/api/auth/register")
def register(user: UserRegister, db: Session = Depends(get_db)):

    existing = db.query(User).filter(User.email == user.email).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = User(
        full_name=user.full_name,
        username=user.username,
        email=user.email,
        password_hash=get_password_hash(user.password)
    )

    db.add(new_user)
    db.commit()

    return {
        "success": True,
        "message": "Registration Successful"
    }
###


@app.post("/api/auth/login")
def login(user: UserLogin, db: Session = Depends(get_db)):

    db_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid Email"
        )

    if not verify_password(
        user.password,
        db_user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Wrong Password"
        )

    token = create_access_token(
        {"sub": db_user.email}
    )

    return {
        "success": True,
        "token": token,
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email
        }
    }

  
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/db-check")
def db_check(db: Session = Depends(get_db)):
    """Check if database is working"""
    count = db.query(Review).count()
    return {"database": "connected", "review_count": count}

# @app.post("/api/send-review-request")
# def send_review_request(
#     customer_name: str,
#     customer_email: str,
#     background_tasks: BackgroundTasks
# ):
#     """
#     Send review request email
#     """

#     review_link = f"http://localhost:5500/index.html?email={customer_email}"

#     background_tasks.add_task(
#         send_review_email,
#         customer_name,
#         customer_email,
#         review_link
#     )

    # return {
    #     "success": True,
    #     "message": "Review request email is being sent.",
    #     "review_link": review_link
    # }


# ============ Run Server ============
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🚀 ReviewShield Backend Starting...")
    print("=" * 50)
    print("📡 API URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🩺 Health Check: http://localhost:8000/api/health")
    print("=" * 50)
    print("💡 Press CTRL+C to stop")
    print("=" * 50)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)