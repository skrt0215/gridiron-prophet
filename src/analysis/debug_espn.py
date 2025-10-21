import requests
from bs4 import BeautifulSoup

ESPN_INJURY_URL = "https://www.espn.com/nfl/injuries"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("Fetching ESPN injuries page...")
response = requests.get(ESPN_INJURY_URL, headers=headers, timeout=30)
soup = BeautifulSoup(response.text, 'html.parser')

print("\n=== ANALYZING ESPN STRUCTURE ===\n")

wrappers = soup.find_all('div', class_='Wrapper')
print(f"Found {len(wrappers)} Wrapper divs\n")

for i, wrapper in enumerate(wrappers[:5], 1):
    print(f"\n--- WRAPPER {i} ---")
    
    team_title = wrapper.find('div', class_='Table__Title')
    if team_title:
        print(f"Team Title in Wrapper: {team_title.text.strip()}")
    
    tables = wrapper.find_all('div', class_='ResponsiveTable')
    print(f"Tables in this wrapper: {len(tables)}")
    
    for j, table in enumerate(tables[:2], 1):
        print(f"\n  Table {j} - First 2 players:")
        rows = table.find_all('tr')[1:3]
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                print(f"    - {cols[0].text.strip()} ({cols[1].text.strip()})")

print("\n\n=== TRYING DIFFERENT APPROACH ===")
print("Looking for team containers with Accordion or article tags...\n")

articles = soup.find_all('article')
print(f"Found {len(articles)} article tags")

accordions = soup.find_all('div', class_='ContentList')
print(f"Found {len(accordions)} ContentList divs")

divs_with_tables = soup.find_all('div', class_='Card')
print(f"Found {len(divs_with_tables)} Card divs")

print("\n\n=== CHECKING PARENT STRUCTURE ===")
first_table = soup.find('div', class_='ResponsiveTable')
if first_table:
    current = first_table
    depth = 0
    print("Parent hierarchy of first ResponsiveTable:")
    while current.parent and depth < 6:
        parent = current.parent
        classes = parent.get('class', [])
        print(f"  {'  ' * depth}↑ {parent.name} {classes}")
        current = parent
        depth += 1