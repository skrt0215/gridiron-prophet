import pymysql

railway_config = {
    'host': 'centerbeam.proxy.rlwy.net',
    'port': 50199,
    'user': 'root',
    'password': 'SxRnFTLycoHlOtsIXQNhWypViXiVCoVV',
    'database': 'railway'
}

print("🔍 Debugging Roster Data...\n")

conn = pymysql.connect(**railway_config)
cursor = conn.cursor()

print("1. Checking player_seasons table structure...")
cursor.execute("DESCRIBE player_seasons")
columns = cursor.fetchall()
print("Columns in player_seasons:")
for col in columns:
    print(f"   - {col[0]} ({col[1]})")

print("\n2. Checking available seasons...")
cursor.execute("SELECT DISTINCT season FROM player_seasons ORDER BY season")
seasons = cursor.fetchall()
print(f"Available seasons: {[s[0] for s in seasons]}")

print("\n3. Checking roster_status values...")
cursor.execute("SELECT DISTINCT roster_status FROM player_seasons WHERE roster_status IS NOT NULL")
statuses = cursor.fetchall()
print(f"Roster statuses: {[s[0] for s in statuses]}")

print("\n4. Checking player count for ARI in 2025...")
cursor.execute("""
    SELECT COUNT(*) 
    FROM player_seasons ps
    JOIN teams t ON ps.team_id = t.team_id
    WHERE t.abbreviation = 'ARI' AND ps.season = 2025
""")
count = cursor.fetchone()[0]
print(f"Total ARI players in 2025: {count}")

print("\n5. Checking player count for ARI in 2024...")
cursor.execute("""
    SELECT COUNT(*) 
    FROM player_seasons ps
    JOIN teams t ON ps.team_id = t.team_id
    WHERE t.abbreviation = 'ARI' AND ps.season = 2024
""")
count_2024 = cursor.fetchone()[0]
print(f"Total ARI players in 2024: {count_2024}")

print("\n6. Sample players (any season, any status)...")
cursor.execute("""
    SELECT 
        p.name,
        ps.position,
        ps.season,
        ps.roster_status,
        t.abbreviation as team
    FROM player_seasons ps
    JOIN players p ON ps.player_id = p.player_id
    JOIN teams t ON ps.team_id = t.team_id
    WHERE t.abbreviation = 'ARI'
    LIMIT 10
""")
samples = cursor.fetchall()
for sample in samples:
    print(f"   {sample}")

print("\n7. Checking if roster_status field exists and has data...")
cursor.execute("""
    SELECT roster_status, COUNT(*) 
    FROM player_seasons 
    GROUP BY roster_status
""")
status_counts = cursor.fetchall()
print("Roster status counts:")
for status, count in status_counts:
    print(f"   {status}: {count}")

cursor.close()
conn.close()

print("\n✅ Debug complete!")
print("\n💡 RECOMMENDATIONS:")
print("   - If 2025 has 0 players, use season 2024 instead")
print("   - If roster_status is NULL, remove that condition from query")
print("   - Check what the actual roster_status values are")
