from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from datetime import datetime
import mysql.connector
import uuid
import os

app = FastAPI(title="ReviewShield API with MySQL", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ MySQL CONNECTION ============
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admins',  # Apna password daalo
    'database': 'reviewshield'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# ============ SPAM DETECTOR ============
import re
from textblob import TextBlob

class SpamDetector:
    def __init__(self):
        self.temp_domains = {
            'tempmail.com', '10minutemail.com', 'mailinator.com', 
            'guerrillamail.com', 'yopmail.com', 'throwaway.com'
        }
        self.spam_patterns = [
            (r'buy\s+now', 20), (r'click\s+here', 25), (r'free\s+shipping', 15),
            (r'limited\s+time', 20), (r'www\.', 30), (r'https?://', 35),
            (r'lottery', 40), (r'prize', 35), (r'bitcoin', 35), (r'crypto', 30)
        ]
        self.spam_keywords = ['free', 'money', 'win', 'prize', 'lottery', 'bitcoin', 
                              'crypto', 'investment', 'click', 'subscribe', 'bonus', 'cash']
    
    def detect(self, text, email):
        score = 100
        reasons = []
        
        try:
            domain = email.split('@')[1].lower()
            if domain in self.temp_domains:
                score -= 40
                reasons.append("Temporary email domain")
        except:
            pass
        
        for pattern, weight in self.spam_patterns:
            if re.search(pattern, text.lower()):
                score -= weight
                reasons.append("Spam pattern detected")
                break
        
        found = [kw for kw in self.spam_keywords if kw in text.lower()]
        if len(found) >= 2:
            score -= 20
            reasons.append(f"Spam keywords: {', '.join(found[:3])}")
        
        if len(text.strip()) < 15:
            score -= 35
            reasons.append("Review too short")
        
        try:
            blob = TextBlob(text)
            sentiment = "positive" if blob.sentiment.polarity > 0.1 else "negative" if blob.sentiment.polarity < -0.1 else "neutral"
        except:
            sentiment = "neutral"
        
        is_spam = score < 50
        return {
            'is_spam': is_spam,
            'spam_score': 100 - score,
            'authenticity': score,
            'sentiment': sentiment,
            'reasons': reasons
        }

spam_detector = SpamDetector()

# ============ PYDANTIC MODELS ============
class ReviewSubmit(BaseModel):
    customer_name: str
    email: EmailStr
    rating: int
    review_text: str

# ============ REVIEW SUBMISSION ============
@app.post("/api/submit-review")
async def submit_review(request: Request):
    try:
        data = await request.json()
        print(f"📝 New review from: {data.get('customer_name')}")
        
        result = spam_detector.detect(data['review_text'], data['email'])
        print(f"🤖 Spam result: {result}")
        
        # ============ MYSQL SAVE ============
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reviews (customer_name, email, rating, review_text, is_spam, authenticity_score, sentiment, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data['customer_name'], 
            data['email'], 
            data['rating'], 
            data['review_text'],
            1 if result['is_spam'] else 0, 
            result['authenticity'], 
            result['sentiment'],
            'approved' if not result['is_spam'] else 'pending'
        ))
        conn.commit()
        review_id = cursor.lastrowid
        conn.close()
        
        print(f"✅ Review saved to MySQL with ID: {review_id}")
        
        return {
            "success": True, 
            "id": review_id, 
            "is_spam": result['is_spam'], 
            "authenticity_score": result['authenticity']
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/reviews")
def get_reviews():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reviews ORDER BY id DESC")
    reviews = cursor.fetchall()
    conn.close()
    return reviews

@app.get("/api/stats")
def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reviews")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reviews WHERE is_spam = 0")
    verified = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(rating) FROM reviews WHERE is_spam = 0")
    avg = cursor.fetchone()[0] or 0
    conn.close()
    return {"total_reviews": total, "verified_reviews": verified, "average_rating": round(avg, 1)}

@app.get("/api/health")
def health():
    return {"status": "healthy"}

# ============ REVIEW REQUESTS (ADD THIS) ============

@app.post("/api/review-requests/create")
async def create_review_request(request: Request):
    try:
        data = await request.json()
        token = str(uuid.uuid4())[:8]
        review_link = f"http://localhost:8001/review/{token}"
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO review_requests (customer_name, customer_email, order_id, product_name, request_token, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
        ''', (data['customer_name'], data['customer_email'], data.get('order_id', ''), data.get('product_name', ''), token))
        conn.commit()
        conn.close()
        
        return {"success": True, "token": token, "review_link": review_link}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/review-requests/pending")
def get_pending_requests():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM review_requests WHERE status = 'pending' ORDER BY created_at DESC")
    requests = cursor.fetchall()
    conn.close()
    return requests

@app.post("/api/review-requests/send/{token}")
def send_request(token: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_email FROM review_requests WHERE request_token = %s", (token,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "Not found"}
    cursor.execute('UPDATE review_requests SET status = "sent", sent_at = NOW() WHERE request_token = %s', (token,))
    conn.commit()
    conn.close()
    return {"success": True, "to_email": row[0], "review_link": f"http://localhost:8001/review/{token}"}

@app.get("/review/{token}")
def review_page(token: str):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM review_requests WHERE request_token = %s", (token,))
    req = cursor.fetchone()
    conn.close()
    
    if not req:
        return HTMLResponse("<h2>❌ Invalid or expired link</h2>")
    
    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html>
    <head><title>Share Your Experience</title>
    <style>
        body {{ font-family: Arial; background: linear-gradient(135deg, #667eea, #764ba2); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }}
        .card {{ background: white; max-width: 550px; width: 100%; padding: 40px; border-radius: 24px; }}
        input, textarea {{ width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; }}
        .stars {{ display: flex; gap: 5px; margin: 15px 0; }}
        .star {{ font-size: 40px; cursor: pointer; color: #cbd5e1; }}
        .star.selected {{ color: #f59e0b; }}
        button {{ background: #2563eb; color: white; padding: 14px; border: none; border-radius: 50px; cursor: pointer; width: 100%; }}
    </style>
    </head>
    <body>
        <div class="card">
            <h2>📝 Share Your Experience</h2>
            <p>Dear <strong>{req['customer_name']}</strong>,</p>
            <form id="reviewForm">
                <input type="hidden" id="token" value="{token}">
                <input type="hidden" id="customerEmail" value="{req['customer_email']}">
                <input type="hidden" id="customerName" value="{req['customer_name']}">
                <label>Your Name</label>
                <input type="text" id="name" value="{req['customer_name']}" readonly>
                <label>Rating</label>
                <div class="stars" id="stars">
                    <span class="star" data-rating="1">★</span>
                    <span class="star" data-rating="2">★</span>
                    <span class="star" data-rating="3">★</span>
                    <span class="star" data-rating="4">★</span>
                    <span class="star" data-rating="5">★</span>
                </div>
                <input type="hidden" id="rating" value="0">
                <label>Your Review</label>
                <textarea id="review" rows="5" placeholder="Tell us about your experience..."></textarea>
                <button type="submit">Submit Review</button>
            </form>
        </div>
        <script>
            let currentRating = 0;
            document.querySelectorAll('.star').forEach(star => {{
                star.addEventListener('click', () => {{
                    currentRating = parseInt(star.dataset.rating);
                    document.getElementById('rating').value = currentRating;
                    document.querySelectorAll('.star').forEach((s, i) => {{
                        if (i < currentRating) s.classList.add('selected');
                        else s.classList.remove('selected');
                    }});
                }});
            }});
            document.getElementById('reviewForm').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const rating = document.getElementById('rating').value;
                const review = document.getElementById('review').value;
                if (rating == 0) {{ alert('Select rating'); return; }}
                if (!review.trim()) {{ alert('Write review'); return; }}
                const response = await fetch('/api/submit-request-review', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        token: document.getElementById('token').value,
                        customer_name: document.getElementById('customerName').value,
                        email: document.getElementById('customerEmail').value,
                        rating: parseInt(rating),
                        review_text: review
                    }})
                }});
                const result = await response.json();
                if (result.success) alert('✅ Thank you!');
                else alert('Error: ' + result.error);
            }});
        </script>
    </body>
    </html>
    ''')

@app.post("/api/submit-request-review")
async def submit_request_review(request: Request):
    try:
        data = await request.json()
        result = spam_detector.detect(data['review_text'], data['email'])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reviews (customer_name, email, rating, review_text, is_spam, authenticity_score, sentiment, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (data['customer_name'], data['email'], data['rating'], data['review_text'],
              1 if result['is_spam'] else 0, result['authenticity'], result['sentiment'],
              'approved' if not result['is_spam'] else 'pending'))
        conn.commit()
        cursor.execute('UPDATE review_requests SET status = "completed", completed_at = NOW() WHERE request_token = %s', (data['token'],))
        conn.commit()
        conn.close()
        return {"success": True, "is_spam": result['is_spam']}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/admin/dashboard")
def admin_dashboard():
    return HTMLResponse('''
    <!DOCTYPE html>
    <html>
    <head><title>Admin Dashboard</title>
    <style>
        body { font-family: Arial; background: #f1f5f9; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; border-radius: 16px; padding: 24px; margin-bottom: 20px; }
        input { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 8px; width: calc(25% - 12px); }
        button { background: #2563eb; color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
    </style>
    </head>
    <body>
        <div class="container">
            <h1>📧 Review Requests Admin</h1>
            <div class="card">
                <h3>➕ Create Review Request</h3>
                <input type="text" id="custName" placeholder="Customer Name">
                <input type="email" id="custEmail" placeholder="Customer Email">
                <input type="text" id="product" placeholder="Product Name">
                <button onclick="createRequest()">Create Request</button>
            </div>
            <div class="card">
                <h3>📋 Pending Requests</h3>
                <div id="requestsList">Loading...</div>
            </div>
        </div>
        <script>
            const API = "http://localhost:8001";
            async function createRequest() {
                const data = {
                    customer_name: document.getElementById('custName').value,
                    customer_email: document.getElementById('custEmail').value,
                    product_name: document.getElementById('product').value
                };
                const res = await fetch(`${API}/api/review-requests/create`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (result.success) {
                    await navigator.clipboard.writeText(result.review_link);
                    alert(`✅ Created! Link copied: ${result.review_link}`);
                    location.reload();
                }
            }
            async function loadRequests() {
                const res = await fetch(`${API}/api/review-requests/pending`);
                const requests = await res.json();
                if (requests.length === 0) {
                    document.getElementById('requestsList').innerHTML = '<p>No pending requests</p>';
                    return;
                }
                let html = `<table><th>Customer</th><th>Email</th><th>Product</th><th>Action</th></tr>`;
                requests.forEach(r => {
                    html += `<tr><td>${r.customer_name}</td><td>${r.customer_email}</td><td>${r.product_name || '-'}</td><td><button onclick="sendRequest('${r.request_token}')">Send</button></td></tr>`;
                });
                html += `</div>`;
                document.getElementById('requestsList').innerHTML = html;
            }
            async function sendRequest(token) {
                const res = await fetch(`${API}/api/review-requests/send/${token}`, { method: 'POST' });
                const result = await res.json();
                alert(`✅ Sent to ${result.to_email}`);
                loadRequests();
            }
            loadRequests();
            setInterval(loadRequests, 5000);
        </script>
    </body>
    </html>
    ''')

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🚀 ReviewShield with MySQL Starting...")
    print("📡 API: http://localhost:8001")
    print("👑 Admin: http://localhost:8001/admin/dashboard")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8001)