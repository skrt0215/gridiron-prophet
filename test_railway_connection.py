import os
import pymysql
from dotenv import load_dotenv

load_dotenv('config/.env')

config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
}

print("🔗 Connecting to MySQL...")
try:
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    print("✅ Connected successfully!\n")

    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"✅ Found {len(tables)} tables:")
    for table in tables:
        print(f"   - {table[0]}")
    print()

    for table in ['injuries', 'players', 'teams', 'games', 'player_seasons', 'depth_charts']:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   {table}: {count:,} records")

    print("\n✅ All tests passed! Database is ready!")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
