# db_utils.py - Database utilities

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json

def get_db_connection():
    """Get SQLite connection"""
    return sqlite3.connect('data/reviewshield.db')

def export_reviews_to_csv(filename="reviews_export.csv"):
    """Export all reviews to CSV"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM reviews", conn)
    df.to_csv(filename, index=False)
    conn.close()
    print(f"✅ Exported {len(df)} reviews to {filename}")
    return filename

def get_review_statistics():
    """Get detailed statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total reviews
    cursor.execute("SELECT COUNT(*) FROM reviews")
    total = cursor.fetchone()[0]
    
    # Spam vs verified
    cursor.execute("SELECT COUNT(*) FROM reviews WHERE is_spam=1")
    spam = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM reviews WHERE is_spam=0 AND status='approved'")
    verified = cursor.fetchone()[0]
    
    # Average rating
    cursor.execute("SELECT AVG(rating) FROM reviews WHERE is_spam=0")
    avg_rating = cursor.fetchone()[0] or 0
    
    # Sentiment distribution
    cursor.execute("""
        SELECT sentiment, COUNT(*) FROM reviews 
        WHERE is_spam=0 
        GROUP BY sentiment
    """)
    sentiment = dict(cursor.fetchall())
    
    # Rating distribution
    cursor.execute("""
        SELECT rating, COUNT(*) FROM reviews 
        WHERE is_spam=0 
        GROUP BY rating
    """)
    ratings = dict(cursor.fetchall())
    
    conn.close()
    
    return {
        'total_reviews': total,
        'spam_reviews': spam,
        'verified_reviews': verified,
        'average_rating': round(avg_rating, 2),
        'sentiment_breakdown': sentiment,
        'rating_distribution': ratings
    }

def delete_old_reviews(days=30):
    """Delete reviews older than specified days"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    cursor.execute("DELETE FROM reviews WHERE created_at < ?", (cutoff_date,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ Deleted {deleted} reviews older than {days} days")
    return deleted

def backup_database():
    """Create database backup"""
    import shutil
    from datetime import datetime
    
    backup_name = f"data/backup_reviewshield_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2('data/reviewshield.db', backup_name)
    print(f"✅ Database backed up to {backup_name}")
    return backup_name

def view_all_data():
    """View all data in database (for debugging)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"\n📋 Table: {table_name}")
        print("-" * 40)
        
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 10")
        rows = cursor.fetchall()
        
        if rows:
            # Get column names
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"Columns: {', '.join(columns)}")
            print(f"Sample data: {len(rows)} rows")
            for row in rows[:3]:
                print(f"  {row}")
        else:
            print("  (empty)")
    
    conn.close()

if __name__ == "__main__":
    print("🛠️  Database Utilities")
    print("=" * 40)
    print("1. Export reviews to CSV")
    print("2. View statistics")
    print("3. View all data")
    print("4. Backup database")
    
    choice = input("\nSelect option (1-4): ")
    
    if choice == '1':
        export_reviews_to_csv()
    elif choice == '2':
        stats = get_review_statistics()
        print(json.dumps(stats, indent=2))
    elif choice == '3':
        view_all_data()
    elif choice == '4':
        backup_database()
        