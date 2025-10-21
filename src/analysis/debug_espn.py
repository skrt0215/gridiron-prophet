import requests
from bs4 import BeautifulSoup

ESPN_INJURY_URL = "https://www.espn.com/nfl/injuries"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("Fetching ESPN injuries page...")
response = requests.get(ESPN_INJURY_URL, headers=headers, timeout=30)
soup = BeautifulSoup(response.text, 'html.parser')

print("\n=== DEBUGGING ESPN HTML STRUCTURE ===\n")

injury_tables = soup.find_all('div', class_='ResponsiveTable')
print(f"Found {len(injury_tables)} injury tables\n")

for i, table in enumerate(injury_tables[:3], 1):
    print(f"\n--- TABLE {i} ---")
    
    team_header_old = table.find_previous('div', class_='Table__Title')
    if team_header_old:
        print(f"OLD METHOD (find_previous Table__Title): {team_header_old.text.strip()}")
    
    parent = table.parent
    while parent and parent.name != 'section':
        parent = parent.parent
    
    if parent:
        team_div = parent.find('div', class_='Table__Title')
        if team_div:
            print(f"NEW METHOD (find in section): {team_div.text.strip()}")
    
    caption = table.find('caption', class_='Table__Title')
    if caption:
        print(f"CAPTION METHOD: {caption.text.strip()}")
    
    print("\nFirst few rows:")
    rows = table.find_all('tr')[1:3]
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 2:
            player = cols[0].text.strip()
            position = cols[1].text.strip()
            print(f"  - {player} ({position})")

print("\n\n=== HTML SNIPPET (first table parent structure) ===")
if injury_tables:
    print(injury_tables[0].parent.prettify()[:1000])