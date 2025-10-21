import requests
from bs4 import BeautifulSoup

response = requests.get("https://www.espn.com/nfl/injuries", 
                       headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
soup = BeautifulSoup(response.text, 'html.parser')

main_wrapper = soup.find('div', class_='Wrapper')
all_elements = main_wrapper.find_all(['div'], class_=['Table__Title', 'ResponsiveTable'])

print("=== ELEMENT ORDER (first 20) ===\n")
for i, element in enumerate(all_elements[:20], 1):
    if 'Table__Title' in element.get('class', []):
        print(f"{i:3}. TEAM: {element.text.strip()}")
    elif 'ResponsiveTable' in element.get('class', []):
        rows = element.find_all('tr')[1:]
        player_count = len(rows)
        if rows:
            first_player = rows[0].find_all('td')[0].text.strip() if rows[0].find_all('td') else "?"
            print(f"{i:3}.   TABLE: {player_count} injuries (first: {first_player})")
        else:
            print(f"{i:3}.   TABLE: empty")

print("\n=== CHECKING ARIZONA'S STRUCTURE ===")
print("Looking for all Arizona Cardinals sections/tables...\n")

ari_found = False
for i, element in enumerate(all_elements, 1):
    if 'Table__Title' in element.get('class', []):
        team_name = element.text.strip()
        if 'Arizona' in team_name:
            print(f"Position {i}: ARIZONA TITLE FOUND")
            ari_found = True
        elif ari_found and 'Atlanta' in team_name:
            print(f"Position {i}: Atlanta title (Arizona section ended)")
            break
    elif 'ResponsiveTable' in element.get('class', []) and ari_found:
        rows = element.find_all('tr')[1:]
        if rows:
            first_two = [row.find_all('td')[0].text.strip() for row in rows[:2] if row.find_all('td')]
            print(f"Position {i}:   Arizona Table - Players: {', '.join(first_two)}")