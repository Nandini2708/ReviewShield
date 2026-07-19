import mysql.connector

# JO PASSWORD MYSQL WORKBENCH MEIN USE KARTE HO WOH DAALO
PASSWORD = "admins"  # ← Yahan apna password daalo

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password=PASSWORD,
        database='reviewshield'
    )
    print("✅ MySQL Connected Successfully!")
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()
    print(f"📊 MySQL Version: {version[0]}")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\n💡 Check:")
    print("   1. MySQL server running hai? (services.msc → MySQL80)")
    print("   2. Password sahi hai?")