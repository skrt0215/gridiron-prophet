import pymysql

railway_config = {
    'host': 'centerbeam.proxy.rlwy.net',
    'port': 50199,
    'user': 'root',
    'password': '***REMOVED***',
    'database': 'railway'
}

print("🔗 Connecting to Railway MySQL...")
try:
    conn = pymysql.connect(**railway_config)
    cursor = conn.cursor()
    print("✅ Connected successfully!\n")
    
    print("📊 Checking tables...")
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"✅ Found {len(tables)} tables:")
    for table in tables:
        print(f"   - {table[0]}")
    print()
    
    key_tables = ['injuries', 'players', 'teams', 'games', 'player_seasons', 'depth_charts']
    print("🔢 Counting records in key tables...")
    for table in key_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   {table}: {count:,} records")
    print()
    
    print("🏈 Testing injury queries...")
    cursor.execute("SELECT COUNT(*) FROM injuries WHERE season = 2025 AND week <= 7")
    injuries_week7 = cursor.fetchone()[0]
    print(f"   Injuries through Week 7: {injuries_week7}")
    
    print("\n✅ All tests passed! Railway database is ready!")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
