import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
import pymysql

class SchemaV2Migration:
    """Migrate from V1 to V2 schema with multi-season support"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def backup_existing_data(self):
        """Create backup tables before migration"""
        print("\n" + "="*70)
        print("STEP 1: BACKING UP EXISTING DATA")
        print("="*70)
        
        tables_to_backup = ['players', 'injuries', 'depth_charts']
        
        for table in tables_to_backup:
            backup_table = f"{table}_backup_v1"
            
            try:
                self.db.execute_update(f"DROP TABLE IF EXISTS {backup_table}")
                self.db.execute_update(f"CREATE TABLE {backup_table} AS SELECT * FROM {table}")
                
                count = self.db.execute_query(f"SELECT COUNT(*) as count FROM {backup_table}")
                print(f"✓ Backed up {table}: {count[0]['count']} records -> {backup_table}")
                
            except Exception as e:
                print(f"✗ Error backing up {table}: {e}")
                return False
        
        return True
    
    def create_new_tables(self):
        """Create new V2 tables"""
        print("\n" + "="*70)
        print("STEP 2: CREATING NEW V2 TABLES")
        print("="*70)
        
        with open('src/database/schema_v2_multi_season.sql', 'r') as f:
            schema_sql = f.read()
        
        statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
        
        for statement in statements:
            if statement.startswith('CREATE TABLE'):
                try:
                    table_name = statement.split('CREATE TABLE IF NOT EXISTS ')[1].split(' ')[0]
                    
                    if table_name not in ['teams', 'games', 'betting_lines']:
                        self.db.execute_update(f"DROP TABLE IF EXISTS {table_name}")
                    
                    self.db.execute_update(statement)
                    print(f"✓ Created/updated table: {table_name}")
                    
                except Exception as e:
                    print(f"✗ Error creating table: {e}")
                    return False
        
        return True
    
    def migrate_players_data(self):
        """Migrate players from V1 to V2 structure"""
        print("\n" + "="*70)
        print("STEP 3: MIGRATING PLAYER DATA")
        print("="*70)
        
        old_players = self.db.execute_query("SELECT * FROM players_backup_v1")
        print(f"Found {len(old_players)} player records to migrate")
        
        player_mapping = {}
        migrated = 0
        skipped = 0
        
        for old_player in old_players:
            try:
                existing = self.db.execute_query(
                    "SELECT player_id FROM players WHERE name = %s AND position = %s",
                    (old_player['name'], old_player['position'])
                )
                
                if existing:
                    new_player_id = existing[0]['player_id']
                else:
                    new_player_id = self.db.execute_insert("""
                        INSERT INTO players (name, position, height, weight, college)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        old_player['name'],
                        old_player['position'],
                        old_player['height'],
                        old_player['weight'],
                        old_player['college']
                    ))
                    migrated += 1
                
                player_mapping[old_player['player_id']] = new_player_id
                
                if old_player['team_id']:
                    season_guess = 2024
                    
                    try:
                        self.db.execute_insert("""
                            INSERT INTO player_seasons 
                            (player_id, season, team_id, position, jersey_number, age, years_in_league, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            new_player_id,
                            season_guess,
                            old_player['team_id'],
                            old_player['position'],
                            old_player['jersey_number'],
                            old_player['age'],
                            old_player['years_in_league'],
                            old_player['status']
                        ))
                    except pymysql.err.IntegrityError:
                        skipped += 1
                
                if migrated % 500 == 0:
                    print(f"  Progress: {migrated} unique players created...")
                    
            except Exception as e:
                if "Duplicate entry" not in str(e):
                    print(f"  Error migrating {old_player['name']}: {e}")
        
        print(f"\n✓ Migrated {migrated} unique players")
        print(f"✓ Created player_season records (skipped {skipped} duplicates)")
        print(f"✓ Player ID mapping created: {len(player_mapping)} entries")
        
        return player_mapping
    
    def migrate_injuries_data(self, player_mapping):
        """Migrate injuries from V1 to V2 with season tracking"""
        print("\n" + "="*70)
        print("STEP 4: MIGRATING INJURY DATA")
        print("="*70)
        
        old_injuries = self.db.execute_query("SELECT * FROM injuries_backup_v1")
        print(f"Found {len(old_injuries)} injury records to migrate")
        
        migrated = 0
        skipped = 0
        
        for old_injury in old_injuries:
            try:
                old_player_id = old_injury['player_id']
                new_player_id = player_mapping.get(old_player_id)
                
                if not new_player_id:
                    skipped += 1
                    continue
                
                date_reported = old_injury['date_reported']
                season = date_reported.year if date_reported else 2024
                
                self.db.execute_insert("""
                    INSERT INTO injuries 
                    (player_id, season, game_id, injury_status, body_part, 
                     date_reported, expected_return_date, practice_status, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    new_player_id,
                    season,
                    old_injury['game_id'],
                    old_injury['injury_status'],
                    old_injury['body_part'],
                    old_injury['date_reported'],
                    old_injury['expected_return_date'],
                    old_injury['practice_status'],
                    old_injury['notes']
                ))
                
                migrated += 1
                
                if migrated % 500 == 0:
                    print(f"  Progress: {migrated} injuries migrated...")
                    
            except Exception as e:
                if "Duplicate entry" not in str(e):
                    print(f"  Error migrating injury: {e}")
                skipped += 1
        
        print(f"\n✓ Migrated {migrated} injury records")
        print(f"✓ Skipped {skipped} records")
    
    def migrate_depth_charts_data(self, player_mapping):
        """Migrate depth charts from V1 to V2"""
        print("\n" + "="*70)
        print("STEP 5: MIGRATING DEPTH CHART DATA")
        print("="*70)
        
        try:
            old_depth = self.db.execute_query("SELECT * FROM depth_charts_backup_v1")
            print(f"Found {len(old_depth)} depth chart records to migrate")
            
            migrated = 0
            skipped = 0
            
            for old_entry in old_depth:
                try:
                    old_player_id = old_entry['player_id']
                    new_player_id = player_mapping.get(old_player_id)
                    
                    if not new_player_id:
                        skipped += 1
                        continue
                    
                    self.db.execute_insert("""
                        INSERT INTO depth_charts 
                        (team_id, player_id, season, week, position, depth_order, snap_percentage)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        old_entry['team_id'],
                        new_player_id,
                        old_entry.get('season', 2024),
                        old_entry.get('week', 1),
                        old_entry['position'],
                        old_entry.get('depth_order', 99),
                        old_entry.get('snap_percentage', 0)
                    ))
                    
                    migrated += 1
                    
                except pymysql.err.IntegrityError:
                    skipped += 1
                except Exception as e:
                    if "Duplicate entry" not in str(e):
                        print(f"  Error migrating depth chart entry: {e}")
                    skipped += 1
            
            print(f"\n✓ Migrated {migrated} depth chart records")
            print(f"✓ Skipped {skipped} records")
            
        except Exception as e:
            print(f"No depth chart data to migrate: {e}")
    
    def verify_migration(self):
        """Verify the migration was successful"""
        print("\n" + "="*70)
        print("STEP 6: VERIFICATION")
        print("="*70)
        
        tables = {
            'players': 'SELECT COUNT(*) as count FROM players',
            'player_seasons': 'SELECT COUNT(*) as count FROM player_seasons',
            'injuries': 'SELECT COUNT(*) as count FROM injuries'
        }
        
        for table, query in tables.items():
            result = self.db.execute_query(query)
            print(f"✓ {table}: {result[0]['count']} records")
        
        unique_players = self.db.execute_query(
            "SELECT COUNT(DISTINCT player_id) as count FROM player_seasons"
        )
        print(f"\n✓ Unique players with season data: {unique_players[0]['count']}")
        
        seasons = self.db.execute_query("""
            SELECT season, COUNT(*) as count 
            FROM player_seasons 
            GROUP BY season 
            ORDER BY season
        """)
        print("\nPlayer seasons breakdown:")
        for s in seasons:
            print(f"  {s['season']}: {s['count']} player-season records")
    
    def run_migration(self):
        """Execute full migration"""
        print("="*70)
        print("GRIDIRON PROPHET - SCHEMA V2 MIGRATION")
        print("Multi-Season Architecture for Historical Injury Tracking")
        print("="*70)
        
        confirm = input("\n⚠️  This will modify your database structure. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Migration cancelled.")
            return
        
        if not self.backup_existing_data():
            print("\n✗ Backup failed. Migration aborted.")
            return
        
        if not self.create_new_tables():
            print("\n✗ Table creation failed. Migration aborted.")
            return
        
        player_mapping = self.migrate_players_data()
        
        self.migrate_injuries_data(player_mapping)
        
        self.migrate_depth_charts_data(player_mapping)
        
        self.verify_migration()
        
        print("\n" + "="*70)
        print("✓ MIGRATION COMPLETE!")
        print("="*70)
        print("\nNext steps:")
        print("1. Run: python src/data_collection/update_rosters.py")
        print("2. Run: python src/data_collection/fetch_snap_counts.py")
        print("3. Run: python src/data_collection/fetch_injuries.py")
        print("\nBackup tables (can be deleted after verification):")
        print("  - players_backup_v1")
        print("  - injuries_backup_v1")
        print("  - depth_charts_backup_v1")

if __name__ == "__main__":
    migration = SchemaV2Migration()
    migration.run_migration()