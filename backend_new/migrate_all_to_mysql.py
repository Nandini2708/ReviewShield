import sqlite3
import mysql.connector
import hashlib
import secrets

print("=" * 50)
print("🔄 Migrating ALL Data from SQLite to MySQL")
print("=" * 50)

# ============ SQLite Connection ============
sqlite_conn = sqlite3.connect('data/reviewshield.db')
sqlite_cursor = sqlite_conn.cursor()

# ============ MySQL Connection ============
# APNI MYSQL DETAILS DALO
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admins',  # Apna MySQL password daalo
    'database': 'reviewshield'
}

try:
    mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
    mysql_cursor = mysql_conn.cursor()
    print("✅ MySQL Connected Successfully!")
except Exception as e:
    print(f"❌ MySQL Connection Failed: {e}")
    print("\n💡 Check:")
    print("   1. MySQL server running hai? (services.msc → MySQL80)")
    print("   2. Password sahi hai?")
    exit()

# ============ CREATE USERS TABLE IN MYSQL ============
print("\n📝 Creating Users Table in MySQL...")
mysql_cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(100) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name VARCHAR(200),
        role VARCHAR(50) DEFAULT 'user',
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP NULL
    )
''')
mysql_conn.commit()
print("✅ Users table created/verified")

# ============ MIGRATE USERS ============
print("\n📝 Migrating Users...")

# Check if users table exists in SQLite
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
if sqlite_cursor.fetchone():
    sqlite_cursor.execute("SELECT * FROM users")
    users = sqlite_cursor.fetchall()
    print(f"   Found {len(users)} users in SQLite")
    
    for user in users:
        try:
            mysql_cursor.execute('''
                INSERT INTO users (id, username, email, password_hash, full_name, role, is_active, created_at, last_login)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', user)
        except Exception as e:
            print(f"   ⚠️ Skipping user {user[1]}: {e}")
    
    mysql_conn.commit()
    print(f"   ✅ {len(users)} users migrated")
else:
    print("   ⚠️ No users table in SQLite, adding default admin")
    
    # Hash password
    salt = secrets.token_hex(16)
    admin_password = hashlib.sha256(f"admin123{salt}".encode()).hexdigest() + ":" + salt
    
    mysql_cursor.execute('''
        INSERT INTO users (username, email, password_hash, full_name, role)
        VALUES (%s, %s, %s, %s, 'admin')
    ''', ("admin", "admin@reviewshield.com", admin_password, "Administrator"))
    mysql_conn.commit()
    print("   ✅ Default admin created")

# ============ MIGRATE REVIEWS ============
print("\n📝 Migrating Reviews...")

# Check if reviews table exists in SQLite
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'")
if sqlite_cursor.fetchone():
    sqlite_cursor.execute("SELECT * FROM reviews")
    reviews = sqlite_cursor.fetchall()
    print(f"   Found {len(reviews)} reviews in SQLite")
    
    # Create reviews table if not exists
    mysql_cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INT PRIMARY KEY AUTO_INCREMENT,
            customer_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL,
            rating INT NOT NULL,
            review_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_spam BOOLEAN DEFAULT FALSE,
            authenticity_score INT DEFAULT 0,
            sentiment VARCHAR(20) DEFAULT 'neutral',
            status VARCHAR(20) DEFAULT 'pending'
        )
    ''')
    
    for review in reviews:
        try:
            mysql_cursor.execute('''
                INSERT INTO reviews (id, customer_name, email, rating, review_text, created_at, is_spam, authenticity_score, sentiment, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', review)
        except Exception as e:
            print(f"   ⚠️ Skipping review: {e}")
    
    mysql_conn.commit()
    print(f"   ✅ {len(reviews)} reviews migrated")
else:
    print("   ⚠️ No reviews table in SQLite")

# ============ MIGRATE REVIEW REQUESTS ============
print("\n📝 Migrating Review Requests...")

sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='review_requests'")
if sqlite_cursor.fetchone():
    sqlite_cursor.execute("SELECT * FROM review_requests")
    requests = sqlite_cursor.fetchall()
    print(f"   Found {len(requests)} review requests in SQLite")
    
    mysql_cursor.execute('''
        CREATE TABLE IF NOT EXISTS review_requests (
            id INT PRIMARY KEY AUTO_INCREMENT,
            customer_name VARCHAR(100) NOT NULL,
            customer_email VARCHAR(100) NOT NULL,
            order_id VARCHAR(50),
            product_name VARCHAR(200),
            request_token VARCHAR(100) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            sent_at TIMESTAMP NULL,
            completed_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    for req in requests:
        try:
            mysql_cursor.execute('''
                INSERT INTO review_requests (id, customer_name, customer_email, order_id, product_name, request_token, status, sent_at, completed_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', req)
        except Exception as e:
            print(f"   ⚠️ Skipping request: {e}")
    
    mysql_conn.commit()
    print(f"   ✅ {len(requests)} review requests migrated")
else:
    print("   ⚠️ No review_requests table in SQLite")

# ============ VERIFY ============
print("\n" + "=" * 50)
print("📊 MIGRATION COMPLETE!")
print("=" * 50)

mysql_cursor.execute("SELECT COUNT(*) FROM users")
user_count = mysql_cursor.fetchone()[0]
print(f"📝 Users in MySQL: {user_count}")

mysql_cursor.execute("SELECT COUNT(*) FROM reviews")
review_count = mysql_cursor.fetchone()[0]
print(f"📝 Reviews in MySQL: {review_count}")

mysql_cursor.execute("SELECT COUNT(*) FROM review_requests")
request_count = mysql_cursor.fetchone()[0]
print(f"📝 Review Requests in MySQL: {request_count}")

# Show users
print("\n📋 Users in MySQL:")
mysql_cursor.execute("SELECT id, username, email, role, created_at FROM users ORDER BY id DESC")
for row in mysql_cursor.fetchall():
    print(f"   ID: {row[0]}, Username: {row[1]}, Email: {row[2]}, Role: {row[3]}")

# ============ CLOSE CONNECTIONS ============
sqlite_conn.close()
mysql_cursor.close()
mysql_conn.close()

print("\n✅ Migration complete! Check MySQL Workbench now.")