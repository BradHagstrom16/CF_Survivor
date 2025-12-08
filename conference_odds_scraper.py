"""
Precise ESPN Conference Championship Odds Scraper
More accurate extraction of conference championship odds
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import re
from datetime import datetime

class PreciseConferenceOddsScraper:
    """
    More precise scraper that targets conference championship odds specifically
    """
    
    def __init__(self, headless=False):
        self.url = "https://www.espn.com/college-football/futures/_/group/conference"
        
        # Chrome options
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--window-size=1920,1080")
        
        # Your pool teams with proper mappings
        self.team_mappings = {
            # Big 12
            'Texas Tech Red Raiders': 'Texas Tech',
            'Arizona State Sun Devils': 'Arizona State',
            'TCU Horned Frogs': 'TCU',
            'Iowa State Cyclones': 'Iowa State',
            'Kansas Jayhawks': 'Kansas State',  # Check if this is Kansas or Kansas State
            'Kansas State Wildcats': 'Kansas State',
            'Utah Utes': 'Utah',
            'Baylor Bears': 'Baylor',
            'Houston Cougars': None,  # Not in pool
            'BYU Cougars': 'BYU',
            'Arizona Wildcats': None,  # Not in pool
            'Cincinnati Bearcats': None,  # Not in pool
            'Colorado Buffaloes': 'Colorado',
            'UCF Knights': None,  # Not in pool
            'Oklahoma State Cowboys': None,  # Not in pool
            'West Virginia Mountaineers': None,  # Not in pool
            
            # ACC
            'Miami Hurricanes': 'Miami',
            'Georgia Tech Yellow Jackets': 'Georgia Tech',
            'Florida State Seminoles': 'Florida State',
            'Louisville Cardinals': 'Louisville',
            'California Golden Bears': None,  # Not in pool
            'SMU Mustangs': 'SMU',
            'Duke Blue Devils': 'Duke',
            'Virginia Cavaliers': None,  # Not in pool
            'NC State Wolfpack': None,  # Not in pool
            'Clemson Tigers': 'Clemson',
            'Boston College Eagles': None,  # Not in pool
            'North Carolina Tar Heels': None,  # Not in pool
            'Virginia Tech Hokies': None,  # Not in pool
            'Syracuse Orange': None,  # Not in pool
            'Wake Forest Demon Deacons': None,  # Not in pool
            'Stanford Cardinal': None,  # Not in pool
            'Pittsburgh Panthers': 'Pittsburgh',
            
            # SEC
            'Texas Longhorns': 'Texas',
            'Georgia Bulldogs': 'Georgia',
            'Alabama Crimson Tide': 'Alabama',
            'Tennessee Volunteers': 'Tennessee',
            'LSU Tigers': 'LSU',
            'Ole Miss Rebels': 'Ole Miss',
            'Missouri Tigers': 'Missouri',
            'Texas A&M Aggies': 'Texas A&M',
            'South Carolina Gamecocks': 'South Carolina',
            'Florida Gators': 'Florida',
            'Oklahoma Sooners': 'Oklahoma',
            'Auburn Tigers': 'Auburn',
            
            # Big Ten
            'Ohio State Buckeyes': 'Ohio State',
            'Oregon Ducks': 'Oregon',
            'Penn State Nittany Lions': 'Penn State',
            'Indiana Hoosiers': 'Indiana',
            'Michigan Wolverines': 'Michigan',
            'Illinois Fighting Illini': 'Illinois',
            'Iowa Hawkeyes': 'Iowa',
            'USC Trojans': 'USC',
            'Nebraska Cornhuskers': 'Nebraska',
            
            # Other conferences
            'Notre Dame Fighting Irish': 'Notre Dame',
            'Boise State Broncos': 'Boise State',
            'UNLV Rebels': 'UNLV',
            'Toledo Rockets': 'Toledo',
            'James Madison Dukes': 'James Madison',
            'Memphis Tigers': 'Memphis',
            'Tulane Green Wave': 'Tulane',
            'Liberty Flames': 'Liberty',
            'Navy Midshipmen': 'Navy',
            'Army Black Knights': 'Army',
            'Louisiana Ragin\' Cajuns': 'Louisiana-Lafayette',
            'Louisiana': 'Louisiana-Lafayette'
        }
        
        self.pool_teams = set(filter(None, self.team_mappings.values()))
    
    def fetch_odds(self):
        """
        Fetch odds with precise extraction
        """
        driver = None
        try:
            print("Starting Chrome driver...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.chrome_options)
            
            print(f"Loading ESPN futures page...")
            driver.get(self.url)
            
            # Wait for page to load
            print("Waiting for page to load...")
            time.sleep(5)
            
            # Make sure we're on the Conference tab
            try:
                conference_tab = driver.find_element(By.XPATH, "//button[contains(text(), 'Conference')]")
                if conference_tab:
                    conference_tab.click()
                    time.sleep(2)
                    print("Clicked on Conference tab")
            except:
                print("Conference tab already selected or not found")
            
            # Method 1: Extract structured data from rows
            print("\nExtracting conference championship odds...")
            odds_data = self.extract_structured_odds(driver)
            
            # Method 2: If that fails, try parsing visible text more carefully
            if not odds_data:
                print("Trying alternative extraction method...")
                odds_data = self.extract_by_text_blocks(driver)
            
            return odds_data
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return None
            
        finally:
            if driver:
                driver.quit()
                print("Chrome driver closed")
    
    def extract_structured_odds(self, driver):
        """
        Extract odds by finding team-odds pairs in the table structure
        """
        odds_data = {}
        
        try:
            # Find all elements that look like table rows
            # ESPN uses various class names, so we'll try multiple approaches
            
            # Look for conference championship sections
            sections = driver.find_elements(By.XPATH, "//div[contains(., 'Conference Champion')]")
            print(f"Found {len(sections)} conference sections")
            
            # Try to find team rows
            # ESPN typically shows teams on the left and odds on the right
            team_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/college-football/team/')]")
            print(f"Found {len(team_elements)} team links")
            
            for team_element in team_elements:
                try:
                    team_text = team_element.text.strip()
                    if not team_text:
                        continue
                    
                    # Map to pool team
                    pool_team = self.team_mappings.get(team_text)
                    if not pool_team:
                        continue
                    
                    # Find the odds - usually in a sibling or parent's sibling element
                    parent = team_element.find_element(By.XPATH, "./ancestor::tr | ./ancestor::div[contains(@class, 'Table')]")
                    if parent:
                        # Look for odds pattern in the parent row
                        parent_text = parent.text
                        odds_match = re.search(r'([+-]\d{3,5})', parent_text)
                        if odds_match:
                            odds_value = int(odds_match.group(1))
                            
                            # Validate the odds are reasonable for conference championships
                            if -10000 <= odds_value <= 100000:
                                odds_data[pool_team] = {
                                    'odds': odds_value,
                                    'raw_team': team_text
                                }
                                print(f"Found: {pool_team} at {odds_value:+d}")
                
                except Exception as e:
                    continue
            
            # Alternative: Look for rows with both team name and odds
            if not odds_data:
                print("\nTrying row-based extraction...")
                rows = driver.find_elements(By.CSS_SELECTOR, "tr, div[class*='Table__TR'], div[class*='Row']")
                
                for row in rows:
                    try:
                        row_text = row.text.strip()
                        if not row_text:
                            continue
                        
                        # Check if this row contains a team we care about
                        for espn_name, pool_name in self.team_mappings.items():
                            if pool_name and espn_name in row_text:
                                # Extract odds from the same row
                                # Look for pattern like +500, -110, etc.
                                odds_matches = re.findall(r'([+-]\d{3,5})', row_text)
                                
                                if odds_matches:
                                    # Take the last odds value (usually the conference championship odds)
                                    odds_value = int(odds_matches[-1])
                                    
                                    # Skip if this looks like a spread (typically -1 to -20)
                                    if -50 <= odds_value <= -1:
                                        continue
                                    
                                    odds_data[pool_name] = {
                                        'odds': odds_value,
                                        'raw_text': row_text[:100]
                                    }
                                    print(f"Found: {pool_name} at {odds_value:+d}")
                                    break
                    
                    except Exception as e:
                        continue
            
        except Exception as e:
            print(f"Error in structured extraction: {e}")
        
        return odds_data
    
    def extract_by_text_blocks(self, driver):
        """
        Extract by parsing text content in blocks
        """
        odds_data = {}
        
        try:
            # Get all text content
            body = driver.find_element(By.TAG_NAME, "body")
            full_text = body.text
            
            # Split into lines
            lines = full_text.split('\n')
            
            # Look for conference championship sections
            in_conference_section = False
            current_conference = None
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Check if we're entering a conference championship section
                if 'Conference Champion' in line:
                    in_conference_section = True
                    # Extract conference name
                    if 'Big 12' in line:
                        current_conference = 'Big 12'
                    elif 'Atlantic Coast' in line or 'ACC' in line:
                        current_conference = 'ACC'
                    elif 'SEC' in line:
                        current_conference = 'SEC'
                    elif 'Big Ten' in line:
                        current_conference = 'Big Ten'
                    continue
                
                if not in_conference_section:
                    continue
                
                # Check if line contains a team name
                for espn_name, pool_name in self.team_mappings.items():
                    if pool_name and espn_name in line:
                        # Look for odds in next few lines
                        for j in range(i, min(i + 5, len(lines))):
                            odds_match = re.search(r'^([+-]\d{3,5})$', lines[j].strip())
                            if odds_match:
                                odds_value = int(odds_match.group(1))
                                odds_data[pool_name] = {
                                    'odds': odds_value,
                                    'conference': current_conference
                                }
                                print(f"Found: {pool_name} ({current_conference}) at {odds_value:+d}")
                                break
                        break
        
        except Exception as e:
            print(f"Error in text block extraction: {e}")
        
        return odds_data
    
    def display_results(self, odds_data):
        """
        Display results grouped by conference
        """
        if not odds_data:
            print("\n❌ No odds data found")
            return
        
        print("\n" + "="*70)
        print(f"✅ CONFERENCE CHAMPIONSHIP ODDS - {len(odds_data)} TEAMS FOUND")
        print("="*70)
        
        # Sort by odds
        sorted_teams = sorted(odds_data.items(), 
                            key=lambda x: x[1].get('odds', 99999))
        
        print("\nYour Pool Teams with Conference Championship Odds:")
        print("-" * 50)
        
        for team, data in sorted_teams:
            odds = data.get('odds')
            conference = data.get('conference', '')
            
            if odds:
                odds_str = f"{odds:+d}"
                print(f"{team:25} {odds_str:>8}  {conference}")
        
        # Save to JSON
        filename = f"conference_odds_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            clean_data = {team: {'odds': data.get('odds'), 'timestamp': datetime.now().isoformat()} 
                         for team, data in odds_data.items()}
            json.dump(clean_data, f, indent=2)
        print(f"\n💾 Saved to {filename}")
        
        # Show which teams weren't found
        missing_teams = self.pool_teams - set(odds_data.keys())
        if missing_teams:
            print(f"\n⚠️ Teams not found ({len(missing_teams)}):")
            for team in sorted(missing_teams):
                print(f"  - {team}")

def main():
    print("="*70)
    print("ESPN Conference Championship Odds Scraper (Precise Version)")
    print("="*70)
    
    headless_input = input("\nRun in headless mode? (y/n, default=n): ").strip().lower()
    headless = headless_input == 'y'
    
    if not headless:
        print("\n👀 Watch the browser to see what's happening...")
    
    scraper = PreciseConferenceOddsScraper(headless=headless)
    odds_data = scraper.fetch_odds()
    scraper.display_results(odds_data)
    
    print("\n" + "="*70)
    print("Complete!")

if __name__ == "__main__":
    main()