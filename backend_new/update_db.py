import sqlite3

conn = sqlite3.connect("data/reviewshield.db")
cursor = conn.cursor()

try:
    cursor.execute("""
        ALTER TABLE review_requests
        ADD COLUMN token TEXT
    """)

    conn.commit()
    print("✅ Token column added successfully!")

except Exception as e:
    print("❌ Error:", e)

finally:
    conn.close()