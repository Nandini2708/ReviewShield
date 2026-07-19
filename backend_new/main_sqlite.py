from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from datetime import datetime
import sqlite3
import os
import uuid
import re
import hashlib
import secrets
from textblob import TextBlob

# ============ CREATE APP ============
app = FastAPI(title="ReviewShield API", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ DATABASE SETUP ============
os.makedirs("data", exist_ok=True)
DB_PATH = 'data/reviewshield.db'

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Reviews table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            rating INTEGER NOT NULL,
            review_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_spam INTEGER DEFAULT 0,
            authenticity_score INTEGER DEFAULT 0,
            sentiment TEXT DEFAULT 'neutral',
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    # Review requests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS review_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            order_id TEXT,
            product_name TEXT,
            request_token TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending',
            sent_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_database()

# ============ ROOT ENDPOINT ============
@app.get("/")
def root():
    return {"message": "ReviewShield API Running", "status": "active"}

# ============ HEALTH CHECK ENDPOINT ============
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "SQLite",
        "version": "2.0.0"
    }

# ============ AUTHENTICATION FUNCTIONS ============
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest() + ":" + salt

def verify_password(password: str, hashed: str) -> bool:
    try:
        hash_val, salt = hashed.split(":")
        return hash_val == hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    except:
        return False

def generate_token(username: str, user_id: int, role: str) -> str:
    token_data = f"{username}:{user_id}:{role}:{datetime.now().isoformat()}"
    return hashlib.sha256(token_data.encode()).hexdigest() + ":" + str(user_id)

def verify_token(token: str) -> dict:
    try:
        token_hash, user_id = token.split(":")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return {"valid": True, "user_id": user[0], "username": user[1], "role": user[2]}
        return {"valid": False}
    except:
        return {"valid": False}

def create_admin_user():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE role = 'admin'")
    if not cursor.fetchone():
        admin_password = hash_password("admin123")
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, 'admin')
        ''', ("admin", "admin@reviewshield.com", admin_password, "Administrator"))
        conn.commit()
        print("✅ Default admin user created: admin@reviewshield.com / admin123")
    conn.close()

create_admin_user()

# ============ AUTHENTICATION MODELS ============
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# ============ AUTHENTICATION API ENDPOINTS ============

@app.post("/api/auth/register")
async def register_user(user: UserRegister):
    print(f"📝 Registering user: {user.username}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
    if cursor.fetchone():
        conn.close()
        return {"success": False, "message": "Email already registered"}
    
    cursor.execute("SELECT id FROM users WHERE username = ?", (user.username,))
    if cursor.fetchone():
        conn.close()
        return {"success": False, "message": "Username already taken"}
    
    password_hash = hash_password(user.password)
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, full_name, role)
        VALUES (?, ?, ?, ?, 'user')
    ''', (user.username, user.email, password_hash, user.full_name))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    print(f"✅ User registered: {user.username} (ID: {user_id})")
    return {"success": True, "message": "User registered successfully", "user_id": user_id}

@app.post("/api/auth/login")
async def login_user(user: UserLogin):
    print(f"🔐 Login attempt: {user.email}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password_hash, full_name, role FROM users WHERE email = ?", (user.email,))
    db_user = cursor.fetchone()
    
    if not db_user:
        conn.close()
        return {"success": False, "message": "Invalid email or password"}
    
    if not verify_password(user.password, db_user[3]):
        conn.close()
        return {"success": False, "message": "Invalid email or password"}
    
    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (db_user[0],))
    conn.commit()
    conn.close()
    
    token = generate_token(db_user[1], db_user[0], db_user[5])
    
    print(f"✅ User logged in: {db_user[1]}")
    
    return {
        "success": True,
        "token": token,
        "user": {
            "id": db_user[0],
            "username": db_user[1],
            "email": db_user[2],
            "full_name": db_user[4],
            "role": db_user[5]
        },
        "message": "Login successful"
    }

@app.get("/api/auth/me")
async def get_current_user(token: str):
    user_data = verify_token(token)
    if not user_data["valid"]:
        return {"success": False, "message": "Invalid token"}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, created_at FROM users WHERE id = ?", (user_data["user_id"],))
    user = cursor.fetchone()
    conn.close()
    
    return {
        "success": True,
        "user": {
            "id": user[0],
            "username": user[1],
            "email": user[2],
            "full_name": user[3],
            "role": user[4],
            "created_at": user[5]
        }
    }

@app.post("/api/auth/logout")
async def logout_user():
    return {"success": True, "message": "Logged out successfully"}

@app.get("/api/admin/users")
async def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, is_active, created_at, last_login FROM users ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    users = []
    for row in rows:
        users.append({
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "full_name": row[3],
            "role": row[4],
            "is_active": bool(row[5]),
            "created_at": row[6],
            "last_login": row[7]
        })
    
    return {"success": True, "users": users}

@app.get("/api/admin/users/count")
async def get_users_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    admin_count = cursor.fetchone()[0]
    conn.close()
    return {"total_users": total, "admin_count": admin_count}

# ============ ADVANCED SPAM DETECTOR ============
class SpamDetector:
    def __init__(self):
        self.temp_domains = {
            'tempmail.com', '10minutemail.com', 'mailinator.com', 
            'guerrillamail.com', 'yopmail.com', 'throwaway.com',
            'temp-mail.org', 'fakeinbox.com', 'dispostable.com'
        }
        self.spam_patterns = [
            (r'buy\s+now', 20), (r'click\s+here', 25), (r'free\s+shipping', 15),
            (r'limited\s+time', 20), (r'www\.', 30), (r'https?://', 35),
            (r'lottery', 40), (r'prize', 35), (r'bitcoin', 35), (r'crypto', 30),
            (r'make\s+money', 35), (r'earn\s+cash', 30), (r'get\s+rich', 40),
            (r'urgent', 30), (r'act\s+now', 25), (r'don[\'\"]?t\s+miss', 20),
            (r'best\s+ever', 15), (r'worst\s+ever', 15), (r'amazing.*product', 10)
        ]
        self.spam_keywords = ['free', 'money', 'win', 'prize', 'lottery', 'bitcoin', 
                              'crypto', 'investment', 'click', 'subscribe', 'bonus', 'cash',
                              'profit', 'income', 'discount', 'offer', 'promo', 'cheap',
                              'deal', 'sale', 'limited', 'urgent', 'claim', 'opportunity']
        self.fake_review_patterns = [
            (r'best\s+product\s+ever', 15),
            (r'worst\s+product\s+ever', 15),
            (r'amazing.*product', 10),
            (r'terrible.*service', 10),
            (r'5\s+stars\s+all\s+the\s+way', 15),
            (r'highly\s+recommend\s+to\s+everyone', 10)
        ]
    
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
        
        for pattern, weight in self.fake_review_patterns:
            if re.search(pattern, text.lower()):
                score -= weight
                reasons.append("Suspicious review pattern")
                break
        
        found = [kw for kw in self.spam_keywords if kw in text.lower()]
        if len(found) >= 2:
            score -= 20
            reasons.append(f"Spam keywords: {', '.join(found[:3])}")
        elif len(found) == 1:
            score -= 10
            reasons.append(f"Suspicious keyword: {found[0]}")
        
        if len(text.strip()) < 15:
            score -= 35
            reasons.append("Review too short")
        
        if len(text) > 20:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.6:
                score -= 20
                reasons.append("Excessive capitalization")
        
        exc_count = text.count('!')
        if exc_count > 3:
            score -= min(exc_count * 3, 15)
            reasons.append(f"Too many exclamation marks ({exc_count})")
        
        try:
            blob = TextBlob(text)
            sentiment = "positive" if blob.sentiment.polarity > 0.1 else "negative" if blob.sentiment.polarity < -0.1 else "neutral"
            if abs(blob.sentiment.polarity) > 0.8:
                score -= 15
                reasons.append("Extreme sentiment detected")
        except:
            sentiment = "neutral"
        
        score = max(0, min(score, 100))
        is_spam = score < 45
        
        return {
            'is_spam': is_spam,
            'spam_score': 100 - score,
            'authenticity': score,
            'sentiment': sentiment,
            'reasons': reasons[:5],
            'recommendation': 'Manual review needed' if is_spam else 'Auto-approve'
        }

spam_detector = SpamDetector()

# ============ REVIEW SUBMISSION ============

@app.post("/api/submit-review")
async def submit_review(request: Request):
    try:
        data = await request.json()
        print(f"📝 New review from: {data.get('customer_name')}")
        
        result = spam_detector.detect(data['review_text'], data['email'])
        print(f"🤖 Spam result: {result}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reviews (customer_name, email, rating, review_text, is_spam, authenticity_score, sentiment, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['customer_name'], data['email'], data['rating'], data['review_text'],
              1 if result['is_spam'] else 0, result['authenticity'], result['sentiment'],
              'approved' if not result['is_spam'] else 'pending'))
        conn.commit()
        review_id = cursor.lastrowid
        conn.close()
        
        print(f"✅ Review saved to SQLite with ID: {review_id}")
        
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    reviews = []
    for row in rows:
        reviews.append({
            "id": row[0], "customer_name": row[1], "email": row[2],
            "rating": row[3], "review_text": row[4], "created_at": row[5],
            "is_spam": bool(row[6]), "authenticity_score": row[7],
            "sentiment": row[8], "status": row[9]
        })
    return reviews

@app.get("/api/stats")
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reviews")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reviews WHERE is_spam = 0")
    verified = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reviews WHERE is_spam = 1")
    spam = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(rating) FROM reviews WHERE is_spam = 0")
    avg = cursor.fetchone()[0] or 0
    conn.close()
    return {"total_reviews": total, "verified_reviews": verified, "spam_reviews": spam, "average_rating": round(avg, 1)}

# ============ REVIEW REQUESTS ============

@app.post("/api/review-requests/create")
async def create_review_request(request: Request):
    try:
        data = await request.json()
        token = str(uuid.uuid4())[:8]
        review_link = f"http://localhost:8001/review/{token}"
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO review_requests (customer_name, customer_email, order_id, product_name, request_token, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (data['customer_name'], data['customer_email'], data.get('order_id', ''), data.get('product_name', ''), token))
        conn.commit()
        conn.close()
        
        return {"success": True, "token": token, "review_link": review_link}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/review-requests/pending")
def get_pending_requests():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM review_requests WHERE status = 'pending' ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    requests = []
    for row in rows:
        requests.append({
            "id": row[0], "customer_name": row[1], "customer_email": row[2],
            "order_id": row[3], "product_name": row[4], "request_token": row[5],
            "token": row[5], "status": row[6], "created_at": row[9]
        })
    return requests

@app.post("/api/review-requests/send/{token}")
def send_review_request(token: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT customer_email FROM review_requests WHERE request_token = ?", (token,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return {"success": False, "error": "Request not found"}
    
    cursor.execute('UPDATE review_requests SET status = "sent", sent_at = CURRENT_TIMESTAMP WHERE request_token = ?', (token,))
    conn.commit()
    conn.close()
    
    return {"success": True, "to_email": row[0], "review_link": f"http://localhost:8001/review/{token}"}

@app.get("/review/{token}")
def public_review_page(token: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM review_requests WHERE request_token = ?", (token,))
    req = cursor.fetchone()
    conn.close()
    
    if not req:
        return HTMLResponse("<h2>❌ Invalid or expired review link</h2>")
    
    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html>
    <head><title>Share Your Experience</title>
    <style>
        body {{ font-family: Arial; background: linear-gradient(135deg, #667eea, #764ba2); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }}
        .card {{ background: white; max-width: 550px; width: 100%; padding: 40px; border-radius: 24px; }}
        input, textarea {{ width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #e2e8f0; border-radius: 12px; }}
        .stars {{ display: flex; gap: 8px; margin: 15px 0; }}
        .star {{ font-size: 45px; cursor: pointer; color: #cbd5e1; }}
        .star.selected {{ color: #f59e0b; }}
        button {{ background: #2563eb; color: white; padding: 14px; border: none; border-radius: 50px; cursor: pointer; width: 100%; }}
    </style>
    </head>
    <body>
        <div class="card">
            <h2>📝 Share Your Experience</h2>
            <p>Dear <strong>{req[1]}</strong>,</p>
            <form id="reviewForm">
                <input type="hidden" id="token" value="{token}">
                <input type="hidden" id="customerEmail" value="{req[2]}">
                <input type="hidden" id="customerName" value="{req[1]}">
                <label>Your Name</label>
                <input type="text" id="name" value="{req[1]}" readonly>
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
                if (rating == 0) {{ alert('Please select a rating'); return; }}
                if (!review.trim()) {{ alert('Please write your review'); return; }}
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
                if (result.success) {{
                    alert('✅ Thank you for your review!');
                    window.location.href = '/thank-you';
                }} else {{
                    alert('Error: ' + result.error);
                }}
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
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reviews (customer_name, email, rating, review_text, is_spam, authenticity_score, sentiment, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['customer_name'], data['email'], data['rating'], data['review_text'],
              1 if result['is_spam'] else 0, result['authenticity'], result['sentiment'],
              'approved' if not result['is_spam'] else 'pending'))
        conn.commit()
        review_id = cursor.lastrowid
        
        cursor.execute('UPDATE review_requests SET status = "completed", completed_at = CURRENT_TIMESTAMP WHERE request_token = ?', (data['token'],))
        conn.commit()
        conn.close()
        
        return {"success": True, "review_id": review_id}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/thank-you")
def thank_you():
    return HTMLResponse('''
    <!DOCTYPE html>
    <html>
    <head><title>Thank You</title>
    <style>
        body { font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; background: linear-gradient(135deg, #667eea, #764ba2); }
        .card { background: white; padding: 50px; border-radius: 24px; text-align: center; }
        button { background: #2563eb; color: white; padding: 12px 24px; border: none; border-radius: 50px; cursor: pointer; margin: 5px; }
    </style>
    </head>
    <body>
        <div class="card">
            <h1>🎉 Thank You!</h1>
            <p>Your review has been submitted successfully.</p>
            <button onclick="window.location.href='http://localhost:8001/admin/dashboard'">Go to Dashboard</button>
        </div>
    </body>
    </html>
    ''')

# ============ ADMIN DASHBOARD ============

@app.get("/admin/dashboard")
def admin_dashboard():
    return HTMLResponse('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard</title>
        <style>
            body { font-family: Arial; background: #f1f5f9; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: white; border-radius: 16px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
            h1 { color: #1e293b; }
            h3 { color: #2563eb; margin-top: 0; }
            input { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 8px; width: calc(25% - 12px); }
            button { background: #2563eb; color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; margin: 5px; }
            .btn-copy { background: #10b981; }
            .btn-send { background: #f59e0b; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
            th { background: #f8fafc; }
            .link-cell { word-break: break-all; font-size: 12px; max-width: 300px; }
            .status-pending { background: #f59e0b; color: white; padding: 4px 8px; border-radius: 20px; font-size: 12px; display: inline-block; }
            .toast { position: fixed; bottom: 20px; right: 20px; background: #10b981; color: white; padding: 12px 24px; border-radius: 8px; z-index: 1000; animation: fadeIn 0.3s; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
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
            
            function showToast(msg, isError = false) {
                const toast = document.createElement('div');
                toast.className = 'toast';
                toast.style.backgroundColor = isError ? '#ef4444' : '#10b981';
                toast.textContent = msg;
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 3000);
            }
            
            async function copyToClipboard(text) {
                try {
                    await navigator.clipboard.writeText(text);
                    showToast('✅ Link copied!');
                } catch(err) {
                    const textarea = document.createElement('textarea');
                    textarea.value = text;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    showToast('✅ Link copied!');
                }
            }
            
            async function createRequest() {
                const data = {
                    customer_name: document.getElementById('custName').value,
                    customer_email: document.getElementById('custEmail').value,
                    product_name: document.getElementById('product').value
                };
                
                if (!data.customer_name || !data.customer_email) {
                    showToast('Please fill name and email', true);
                    return;
                }
                
                try {
                    const res = await fetch(`${API}/api/review-requests/create`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    const result = await res.json();
                    
                    if (result.success) {
                        showToast('✅ Request created!');
                        await copyToClipboard(result.review_link);
                        setTimeout(() => location.reload(), 1500);
                    } else {
                        showToast('Error: ' + result.error, true);
                    }
                } catch (error) {
                    showToast('Error creating request', true);
                }
            }
            
            async function sendRequest(token) {
                if (!token || token === 'undefined' || token === 'null') {
                    showToast('❌ Invalid token! Please refresh the page.', true);
                    return;
                }
                
                try {
                    const res = await fetch(`${API}/api/review-requests/send/${token}`, { method: 'POST' });
                    const result = await res.json();
                    
                    if (result.success) {
                        showToast(`✅ Sent to ${result.to_email}`);
                        loadRequests();
                    } else {
                        showToast('Error: ' + (result.error || 'Failed to send'), true);
                    }
                } catch (error) {
                    showToast('Error sending request', true);
                }
            }
            
            async function loadRequests() {
                try {
                    const res = await fetch(`${API}/api/review-requests/pending`);
                    const requests = await res.json();
                    
                    if (!requests || requests.length === 0) {
                        document.getElementById('requestsList').innerHTML = '<p>✨ No pending requests. Create one above!</p>';
                        return;
                    }
                    
                    let html = `<table>
                        <thead>
                            <tr>
                                <th>Customer</th>
                                <th>Email</th>
                                <th>Product</th>
                                <th>Review Link</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                    `;
                    
                    requests.forEach(r => {
                        const token = r.request_token || r.token;
                        const link = `${API}/review/${token}`;
                        
                        html += `
                            <tr>
                                <td><strong>${r.customer_name}</strong></td>
                                <td>${r.customer_email}</td>
                                <td>${r.product_name || '-'}</td>
                                <td class="link-cell">
                                    <small>${link}</small>
                                    <button class="btn-copy" onclick="copyToClipboard('${link}')">📋 Copy</button>
                                </td>
                                <td><span class="status-pending">${r.status}</span></td>
                                <td>
                                    <button class="btn-send" onclick="sendRequest('${token}')">📧 Send Request</button>
                                </td>
                            </tr>
                        `;
                    });
                    
                    html += `</tbody></div>`;
                    document.getElementById('requestsList').innerHTML = html;
                } catch (error) {
                    console.error('Error loading requests:', error);
                    document.getElementById('requestsList').innerHTML = '<p>❌ Error loading requests. Make sure backend is running.</p>';
                }
            }
            
            loadRequests();
            setInterval(loadRequests, 5000);
        </script>
    </body>
    </html>
    ''')

# ============ RUN SERVER ============
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🚀 ReviewShield Backend Starting...")
    print("=" * 50)
    print("📡 API: http://localhost:8001")
    print("👑 Admin: http://localhost:8001/admin/dashboard")
    print("🔐 Login: http://localhost:8001/login.html")
    print("📚 Docs: http://localhost:8001/docs")
    print("🩺 Health: http://localhost:8001/api/health")
    print("🗄️  Database: SQLite only")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8001)