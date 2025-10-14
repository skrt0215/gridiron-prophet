import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager

def populate_nfl_teams():
    """Populate the database with all 32 NFL teams"""
    
    db = DatabaseManager()
    
    teams = [
        # AFC East
        ("Buffalo Bills", "BUF", "Buffalo", "AFC", "East", "Highmark Stadium", "Sean McDermott"),
        ("Miami Dolphins", "MIA", "Miami", "AFC", "East", "Hard Rock Stadium", "Mike McDaniel"),
        ("New England Patriots", "NE", "Foxborough", "AFC", "East", "Gillette Stadium", "Jerod Mayo"),
        ("New York Jets", "NYJ", "East Rutherford", "AFC", "East", "MetLife Stadium", "Robert Saleh"),
        
        # AFC North
        ("Baltimore Ravens", "BAL", "Baltimore", "AFC", "North", "M&T Bank Stadium", "John Harbaugh"),
        ("Cincinnati Bengals", "CIN", "Cincinnati", "AFC", "North", "Paycor Stadium", "Zac Taylor"),
        ("Cleveland Browns", "CLE", "Cleveland", "AFC", "North", "Cleveland Browns Stadium", "Kevin Stefanski"),
        ("Pittsburgh Steelers", "PIT", "Pittsburgh", "AFC", "North", "Acrisure Stadium", "Mike Tomlin"),
        
        # AFC South
        ("Houston Texans", "HOU", "Houston", "AFC", "South", "NRG Stadium", "DeMeco Ryans"),
        ("Indianapolis Colts", "IND", "Indianapolis", "AFC", "South", "Lucas Oil Stadium", "Shane Steichen"),
        ("Jacksonville Jaguars", "JAX", "Jacksonville", "AFC", "South", "EverBank Stadium", "Doug Pederson"),
        ("Tennessee Titans", "TEN", "Nashville", "AFC", "South", "Nissan Stadium", "Brian Callahan"),
        
        # AFC West
        ("Denver Broncos", "DEN", "Denver", "AFC", "West", "Empower Field at Mile High", "Sean Payton"),
        ("Kansas City Chiefs", "KC", "Kansas City", "AFC", "West", "GEHA Field at Arrowhead Stadium", "Andy Reid"),
        ("Las Vegas Raiders", "LV", "Las Vegas", "AFC", "West", "Allegiant Stadium", "Antonio Pierce"),
        ("Los Angeles Chargers", "LAC", "Los Angeles", "AFC", "West", "SoFi Stadium", "Jim Harbaugh"),
        
        # NFC East
        ("Dallas Cowboys", "DAL", "Arlington", "NFC", "East", "AT&T Stadium", "Mike McCarthy"),
        ("New York Giants", "NYG", "East Rutherford", "NFC", "East", "MetLife Stadium", "Brian Daboll"),
        ("Philadelphia Eagles", "PHI", "Philadelphia", "NFC", "East", "Lincoln Financial Field", "Nick Sirianni"),
        ("Washington Commanders", "WAS", "Landover", "NFC", "East", "Northwest Stadium", "Dan Quinn"),
        
        # NFC North
        ("Chicago Bears", "CHI", "Chicago", "NFC", "North", "Soldier Field", "Matt Eberflus"),
        ("Detroit Lions", "DET", "Detroit", "NFC", "North", "Ford Field", "Dan Campbell"),
        ("Green Bay Packers", "GB", "Green Bay", "NFC", "North", "Lambeau Field", "Matt LaFleur"),
        ("Minnesota Vikings", "MIN", "Minneapolis", "NFC", "North", "U.S. Bank Stadium", "Kevin O'Connell"),

        # NFC South
        ("Atlanta Falcons", "ATL", "Atlanta", "NFC", "South", "Mercedes-Benz Stadium", "Raheem Morris"),
        ("Carolina Panthers", "CAR", "Charlotte", "NFC", "South", "Bank of America Stadium", "Dave Canales"),
        ("New Orleans Saints", "NO", "New Orleans", "NFC", "South", "Caesars Superdome", "Dennis Allen"),
        ("Tampa Bay Buccaneers", "TB", "Tampa", "NFC", "South", "Raymond James Stadium", "Todd Bowles"),
        
        # NFC West
        ("Arizona Cardinals", "ARI", "Glendale", "NFC", "West", "State Farm Stadium", "Jonathan Gannon"),
        ("Los Angeles Rams", "LAR", "Los Angeles", "NFC", "West", "SoFi Stadium", "Sean McVay"),
        ("San Francisco 49ers", "SF", "Santa Clara", "NFC", "West", "Levi's Stadium", "Kyle Shanahan"),
        ("Seattle Seahawks", "SEA", "Seattle", "NFC", "West", "Lumen Field", "Mike Macdonald"),
    ]
    
    print("Populating NFL teams...")
    added_count = 0
    
    for team in teams:
        try:
            team_id = db.add_team(*team)
            print(f"✓ Added: {team[0]} ({team[1]})")
            added_count += 1
        except Exception as e:
            if "Duplicate entry" in str(e):
                print(f"- Skipped: {team[0]} (already exists)")
            else:
                print(f"✗ Error adding {team[0]}: {e}")
    
    print(f"\n{added_count} teams added successfully!")
    
    all_teams = db.get_all_teams()
    print(f"Total teams in database: {len(all_teams)}")

if __name__ == "__main__":
    populate_nfl_teams()