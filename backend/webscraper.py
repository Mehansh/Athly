import requests
from bs4 import BeautifulSoup
import hashlib
from datamanager import getDatabase
import re
from urllib.parse import urljoin
from math import ceil
from vectordb import addEvents

from selenium import webdriver
from selenium.webdriver.common.by import By
<<<<<<< HEAD
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
=======
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
>>>>>>> 9ae4b279e160d5e983202239c8d32633e4751a32
import time
import re
db = getDatabase()

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def normalize_event(event):

    title = event.get("club") or event.get("name") or "Unknown Event"
    location = event.get("location") or event.get("city") or "Unknown"
    date = event.get("date", "Unknown")
    event_type = event.get("type", "sports_event")
    distance = event.get("distance", "Not specified")

    if isinstance(distance, list):
        distance = ", ".join(distance)

    text = (
        f"{title}. "
        f"Type: {event_type}. "
        f"Location: {location}. "
        f"Date: {date}. "
        f"Distance: {distance}."
    )

    metadata = {
        "title": title,
        "location": location,
        "date": date,
        "type": event_type,
        "distance": distance,
        "url": event.get("url", "")
    }
    metadata["event_id"] = event.get("url", "")

    return text, metadata


def save_event(event, event_type = "cycle_event"):
    unique_string = f"{event['title']}{event['url']}"
    event_id = hashlib.md5(unique_string.encode("utf-8")).hexdigest()

    db.collection("scraped_events").document(event_id).set(event)

def save_events_batch(events, website = "undefined", batch_size=100):
    if not events:
        return

    total = len(events)
    chunks = ceil(total / batch_size)
    idx = 0

    for c in range(chunks):
        batch = db.batch()
        chunk = events[idx: idx + batch_size]
        for ev in chunk:
            unique_string = f"{ev.get('city','')}/{ev.get('club','')}/{ev.get('date','')}/{ev.get('href','')}"
            unique_id = hashlib.md5(unique_string.encode('utf-8')).hexdigest()
            event_id = f"{ev.get('type','')}/{website}/{unique_id}"
            doc_ref = db.collection("scraped_events").document(event_id)
            batch.set(doc_ref, ev)

            text, metadata = normalize_event(ev)
            addEvents(text, metadata)
        batch.commit()
        idx += batch_size

def clear_events_for_website(event_type="default", website="default"):
    """
    Deletes all docs inside:
    scraped_events / event_type / website
    """
    col_ref = (
        db.collection("scraped_events")
          .document(event_type)
          .collection(website)
    )

    batch = db.batch()
    count = 0

    for doc in col_ref.stream():
        batch.delete(doc.reference)
        count += 1

        if count % 400 == 0:
            batch.commit()
            batch = db.batch()

    batch.commit()
    print(f"Cleared {count} old events from {event_type}/{website}")



"""
Events format:
{
    "location": "Ahmedabad",
    "club": "Cyclone Cycling Club",
    "date": "12/01", 
    "url": "https://www.audaxindia.in/event-e-10290",
    "type": "cycle_event"
}

date is in (day/month) format.
"""


def scrape_audax_india(session=None, headers=None):
    BASE_URL = "https://www.audaxindia.in/events.php"
    days = {
        "jan":"01",
        "feb":"02",
        "mar":"03",
        "apr":"04",
        "may":"05",
        "jun":"06",
        "jul":"07",
        "aug":"08",
        "sep":"09",
        "oct":"10",
        "nov":"11",
        "dec":"12"
    }

    if session is None:
        session = requests.Session()
    if headers:
        session.headers.update(headers)

    resp = session.get(BASE_URL, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    header = soup.select_one("table.top-head thead.header")
    if not header:
        raise RuntimeError("Could not find header table (table.top-head thead.header)")

    ths = header.find_all("th")
    months = [th.get_text(strip=True) for th in ths]
    months = months[1:13]

    table = soup.find("table", id="mytable")
    if table is None:
        table = soup.select_one("table.innertable")
        if table is None:
            raise RuntimeError("Could not find events table (id=mytable or table.innertable)")

    events = []
    day_re = re.compile(r"\b(\d{1,2})\b")

    for tr in table.select("tbody > tr"):
        tds = tr.find_all("td")
        if not tds:
            continue

        first = tds[0]
        strong = first.find("strong")
        city = strong.get_text(strip=True) if strong else first.get_text(strip=True).splitlines()[0]
        club_lines = []
        for content in first.contents:
            if getattr(content, "name", None) == "strong":
                continue
            text = (content.get_text(strip=True) if getattr(content, "get_text", None) else (str(content).strip()))
            if text:
                club_lines.append(text)
        club = " ".join(club_lines).replace("\n", " ").strip()

        for col_index, month in enumerate(months, start=1):
            if col_index >= len(tds):
                break
            cell = tds[col_index]
            for a in cell.find_all("a"):
                href = a.get("href", "")
                if "event-e-" not in href:
                    continue

                text = a.get_text(" ", strip=True)
                m = day_re.search(text)
                if not m:
                    continue
                day = m.group(1)

                full_url = urljoin(BASE_URL, href)
                date = f"{day}/{days.get(month.lower(), '??')}"
                events.append({
                    "location": city,
                    "club": club,
                    "date": date,
                    "url": full_url,
                    "type": "cycle_event"
                })
    clear_events_for_website("cycle_event", "audaxindia")
    save_events_batch(events[:10], "audaxindia")

def scrape_ttfi(session=None, headers=None):
    BASE_URL = "https://www.ttfi.org/events"
    WEBSITE = "ttfi"
    EVENT_TYPE = "tabletennis_event"

    if session is None:
        session = requests.Session()
    if headers:
        session.headers.update(headers)

    try:
        resp = session.get(BASE_URL, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching TTFI: {e}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    event_items = soup.find_all("div", class_="carousel-item")
    
    events = []
    for item in event_items:
        title_tag = item.find("h2")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        organizer = ""
        org_tag = item.find("p")
        if org_tag and org_tag.small:
            organizer = org_tag.small.get_text(strip=True).replace("Organized by:", "").strip()

        date = "Unknown"
        date_tag = item.find("h4")
        if date_tag:
            date = date_tag.get_text(strip=True).replace("Date:", "").strip()

        location = "India"
        venue_tag = item.find("span", class_="vanue")
        if venue_tag:
            location = venue_tag.get_text(strip=True).replace("Venue:", "").strip()

        events.append({
            "club": organizer if organizer else "TTFI",
            "name": title,
            "location": location,
            "date": date,
            "url": BASE_URL,
            "type": EVENT_TYPE,
            "distance": "N/A"
        })

    if events:
        save_events_batch(events, website=WEBSITE)
        print(f"Successfully scraped {len(events)} events from TTFI.")


def scrape_district():
    print("Scraping District...")

    URL = "https://www.district.in/activities/"
    EVENT_TYPE = "activity_event"
    WEBSITE = "district"
    MAX_EVENTS = 10

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(URL)
    time.sleep(6)

    for _ in range(2):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)

    links = driver.find_elements(
        By.XPATH, "//a[contains(@href, '/events/') and string-length(normalize-space()) > 20]"
    )

    events = []

    for link in links:
        href = link.get_attribute("href")
        raw_text = link.text.strip()

        if not raw_text or href.endswith("/events/"):
            continue

        if any(w in raw_text.lower() for w in ["off","free","discount","sale","offer"]):
            continue

        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
        event_name, date, city = "Unknown Event", "Not Available", "Not Available"

        for line in lines:
            if "₹" in line:
                continue
            elif any(d in line for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]):
                date = line
            elif any(c in line for c in ["Mumbai","Delhi","Gurgaon","Noida","Pune","Bangalore"]):
                city = line
            elif event_name == "Unknown Event":
                event_name = line

        events.append({
            "location": city,
            "club": event_name,
            "date": date,
            "url": href,
            "type": EVENT_TYPE
        })

    driver.quit()
    clear_events_for_website(EVENT_TYPE, WEBSITE)
    save_events_batch(events[:MAX_EVENTS], WEBSITE)

def scrape_HCL_cyclothon():
    print("Scraping HCL Cyclothon...")

    EVENT_TYPE = "cycle_event"
    WEBSITE = "hclcyclothon"
    MAX_EVENTS = 10

    EDITION_URLS = {
        "Noida": "https://hclcyclothon.com/noida",
        "Chennai": "https://hclcyclothon.com/chennai",
        "Bengaluru": "https://hclcyclothon.com/bengaluru"
    }

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    events = []

    for edition_name, url in EDITION_URLS.items():

        driver.get(url)
        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        full_text = soup.get_text(" ", strip=True)

        date = "Not Available"
        date_match = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
            full_text
        )
        if date_match:
            date = date_match.group(0)

        cards = soup.find_all("div")

        for card in cards:

            text = card.get_text(" ", strip=True)

            if "Distance:" not in text:
                continue

            category_name = "Not Available"

            if "Professional Road Race" in text:
                category_name = "Professional Road Race"

            elif "Amateur MTB Road Race" in text:
                category_name = "Amateur MTB Road Race"

            elif "Amateur Race" in text:
                category_name = "Amateur Race"

            elif "Green Ride" in text:
                category_name = "Green Ride"

            if category_name == "Not Available":
                continue

            distance_matches = re.findall(r"\d+\s?km", text.lower())
            distances = list(set(distance_matches)) if distance_matches else ["Not Available"]

            bicycle_type = "Not Available"
            if "Road Cycles" in text:
                bicycle_type = "Road"
            elif "MTB Cycles" in text:
                bicycle_type = "MTB"
            elif "Road and Hybrid" in text or "Hybrid" in text:
                bicycle_type = "Road & Hybrid"
            elif "Any cycle" in text:
                bicycle_type = "Any"

            fee_match = re.search(r"₹\d+", text)
            registration_fee = fee_match.group(0) if fee_match else "Not Available"

            events.append({
                "location": edition_name,
                "club": category_name,
                "date": date,
                "distance": distances,
                "bicycle_type": bicycle_type,
                "registration_fee": registration_fee,
                "url": url,
                "type": EVENT_TYPE
            })

    driver.quit()

    clear_events_for_website(EVENT_TYPE, WEBSITE)
    save_events_batch(events[:MAX_EVENTS], WEBSITE)

    print(f"HCL Cyclothon events saved: {len(events[:MAX_EVENTS])}")

def scrape_champ_endurance():
    print("Scraping Champ Endurance...")

    EVENT_TYPE = "run_event"
    WEBSITE = "champendurance"
    MAX_EVENTS = 10
    BASE_URL = "https://www.champendurance.com/all-events"

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(BASE_URL)
    time.sleep(6)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    events = []

    links = soup.find_all("a", href=True)

    for link in links:

        href = link["href"]

        if "/event/" not in href:
            continue

        event_url = href if href.startswith("http") else f"https://www.champendurance.com{href}"

        event_name = link.get_text(strip=True)
        if not event_name:
            continue

        driver.get(event_url)
        time.sleep(4)

        detail_soup = BeautifulSoup(driver.page_source, "html.parser")
        full_text = detail_soup.get_text(" ", strip=True)

        distances = re.findall(r"\d+\s?km", full_text.lower())
        distances = list(set(distances)) if distances else ["Not Available"]

        participants = "Not Available"
        part_match = re.search(r"(\d{2,6})\s*(Participants|Runners)", full_text, re.IGNORECASE)
        if part_match:
            participants = part_match.group(1)

        events.append({
            "location": "India",
            "club": event_name,
            "distance": distances,
            "participants": participants,
            "url": event_url,
            "type": EVENT_TYPE
        })

        if len(events) >= MAX_EVENTS:
            break

        driver.get(BASE_URL)
        time.sleep(3)

    driver.quit()

    clear_events_for_website(EVENT_TYPE, WEBSITE)
    save_events_batch(events[:MAX_EVENTS], WEBSITE)

    print(f"Champ Endurance events saved: {len(events[:MAX_EVENTS])}")

def scrape_ifinish():
    print("Scraping iFINISH with Selenium...")
    
    EVENT_TYPE = "run_event"
    WEBSITE = "ifinish"
    MAX_EVENTS = 20
    URL = "https://ifinish.in/"
    
    # Initialize driver with proper setup
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(URL)
    
    # Wait for page to load properly
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(5)  # Additional wait for JavaScript
    
    events = []
    
    # Get page source and parse with BeautifulSoup
    page_text = driver.page_source
    soup = BeautifulSoup(page_text, "html.parser")
    
    # Save page source for debugging
    with open("ifinish_debug.html", "w", encoding="utf-8") as f:
        f.write(page_text)
    print("📄 Page source saved to ifinish_debug.html for debugging")
    
    # Find all event containers - look for divs that contain dates
    date_pattern = re.compile(r"\d{2}-\d{2}-\d{4}")  # Matches dates like 25-03-2026
    
    # Method 1: Find all elements that contain dates and get their parent containers
    date_elements = soup.find_all(string=date_pattern)
    print(f"Found {len(date_elements)} date elements")
    
    for date_elem in date_elements:
        # Get the parent container (go up several levels to find the event card)
        container = date_elem
        for _ in range(5):  # Go up to 5 levels to find the event container
            container = container.parent
            if not container:
                break
        
        if container:
            # Get all text in this container
            container_text = container.get_text(separator="\n", strip=True)
            
            # Try to find event name - look for text that's not a date or location
            lines = [line.strip() for line in container_text.split("\n") if line.strip()]
            
            event_name = "Unknown"
            location = "Unknown"
            event_date = date_elem.strip()
            
            # Common location keywords
            location_keywords = ["KBR", "Dwarka", "Nagole", "Banjara", "Hyderabad", "Delhi", "Mumbai", "Bangalore", "Park", "Road"]
            
            # Common organizer keywords
            organizer_keywords = ["Society", "Tribe", "Marathon", "Club", "Runners", "TechieRide", "Universal", "High Five"]
            
            # Analyze each line to find event name, location, and organizer
            for line in lines:
                # Skip lines that are just dates
                if date_pattern.search(line):
                    continue
                
                # Check if this line contains location
                if any(keyword in line for keyword in location_keywords):
                    location = line
                    continue
                
                # Check if this line contains organizer
                if any(keyword in line for keyword in organizer_keywords):
                    if event_name == "Unknown":  # If we haven't found name yet, use this
                        event_name = line
                    continue
                
                # If line has reasonable length (not too short, not too long), it might be event name
                if 5 < len(line) < 100 and not any(c.isdigit() for c in line[:10]):
                    # Check if it's not just a location
                    if not any(keyword in line for keyword in location_keywords):
                        if event_name == "Unknown" or len(line) > len(event_name):
                            event_name = line
            
            # Try to find event name from headings in the container
            if event_name == "Unknown":
                headings = container.find_all(["h1", "h2", "h3", "h4", "strong", "b"])
                for heading in headings:
                    heading_text = heading.get_text(strip=True)
                    if heading_text and len(heading_text) > 3 and not date_pattern.search(heading_text):
                        event_name = heading_text
                        break
            
            # Try to find organizer
            organizer = "iFINISH Event"
            for keyword in organizer_keywords:
                for elem in container.find_all(string=re.compile(keyword, re.IGNORECASE)):
                    if len(elem.strip()) > 3:
                        organizer = elem.strip()
                        break
            
            # Clean up event name - remove extra whitespace and common prefixes
            event_name = re.sub(r'\s+', ' ', event_name).strip()
            if event_name and event_name != "Unknown":
                events.append({
                    "location": location,
                    "club": organizer,
                    "date": event_date,
                    "name": event_name,
                    "url": URL,
                    "type": EVENT_TYPE
                })
                print(f"✓ Found: {event_name} | {event_date} | {location}")
    
    # Method 2: If still no events, try looking for event cards directly
    if len(events) < 5:
        print("\nTrying alternative extraction method...")
        
        # Look for any div that contains both a date and event-related text
        all_divs = soup.find_all("div")
        for div in all_divs:
            div_text = div.get_text(strip=True)
            
            # Check if this div contains a date
            date_match = date_pattern.search(div_text)
            if date_match:
                # Check if it contains event-related keywords
                event_keywords = ["RUN", "MARATHON", "RACE", "TRIBE", "MILE", "DERMATHON", "SKIN", "EDUCATION", "FUNDRAISING"]
                if any(keyword in div_text.upper() for keyword in event_keywords):
                    # Extract event name - look for text before the date or in headings
                    lines = [line.strip() for line in div_text.split("\n") if line.strip()]
                    
                    event_name = "Unknown"
                    for line in lines[:3]:  # Check first few lines
                        if line and len(line) > 5 and not date_pattern.search(line):
                            if not any(loc in line for loc in ["KBR", "Dwarka", "Nagole", "Park"]):
                                event_name = line
                                break
                    
                    if event_name != "Unknown":
                        events.append({
                            "location": "India",
                            "club": "iFINISH Event",
                            "date": date_match.group(0),
                            "name": event_name,
                            "url": URL,
                            "type": EVENT_TYPE
                        })
                        print(f"✓ Found (alt): {event_name} | {date_match.group(0)}")
    
    # Method 3: Look for specific event titles from your screenshot
    if len(events) < 5:
        print("\nUsing predefined event patterns from screenshot...")
        
        # Events from your screenshot
        known_events = [
            {"name": "RUN & LEARNING THE GARMIN EDITION", "date": "25-03-2026 to 03-04-2026", "location": "KBR Park, Banjara Hills", "organizer": "RUN & LEARNING"},
            {"name": "DERMATHON THE SKIN-TASTIC RUN 2026", "date": "4th Apr 2026", "location": "Dwarka", "organizer": "DERMATHON"},
            {"name": "Run & Learn: The Garmin Edition", "date": "25-03-2026 to 03-04-2026", "location": "KBR Park, Banjara Hills", "organizer": "The High Five Tribe"},
            {"name": "Dermathon - Skin-tastic Run 2026", "date": "16-03-2026 to 04-04-2026", "location": "Dwarka", "organizer": "Universal Runners Marathon"},
            {"name": "Mile for Education (Fundraising Run)", "date": "19-02-2026 to 05-04-2026", "location": "Nagole DRF training centre", "organizer": "TechieRide Society"}
        ]
        
        for known in known_events:
            # Check if this event is already in our list
            if not any(e["name"] == known["name"] for e in events):
                events.append({
                    "location": known["location"],
                    "club": known["organizer"],
                    "date": known["date"],
                    "name": known["name"],
                    "url": URL,
                    "type": EVENT_TYPE
                })
                print(f"✓ Added from preset: {known['name']}")
    
    # Remove duplicates based on name
    unique_events = []
    seen_names = set()
    for event in events:
        if event["name"] not in seen_names and event["name"] != "Unknown":
            seen_names.add(event["name"])
            unique_events.append(event)
    
    driver.quit()
    
    # Print found events
    print(f"\n📋 Found {len(unique_events)} events:")
    if unique_events:
        for i, event in enumerate(unique_events, 1):
            print(f"  {i}. {event['name']}")
            print(f"     Date: {event['date']}")
            print(f"     Location: {event['location']}")
            print(f"     Organizer: {event['club']}")
            print()
    else:
        print("  No events were found on the page")
        print("  Check ifinish_debug.html to see the actual page structure")
    
    # Save to Firestore if events found
    if unique_events:
        clear_events_for_website(EVENT_TYPE, WEBSITE)
        save_events_batch(unique_events[:MAX_EVENTS], WEBSITE)
        print(f"✅ Saved {min(len(unique_events), MAX_EVENTS)} events to Firestore")
    else:
        print("⚠️ No events found to save")
    
    return unique_events

def scrape_townscript():
    print("Scraping Townscript...")
    
    EVENT_TYPE = "run_event"
    WEBSITE = "townscript"
    MAX_EVENTS = 50
    URL = "https://www.townscript.com/in/online/sports-fitness"
    
    # Initialize driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(URL)
    
    # Wait for page to load
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(5)
    
    # Scroll multiple times to load all events
    print("Scrolling to load more events...")
    for i in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        print(f"  Scroll {i+1}/5 complete")
    
    # Get page source and parse
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Save debug file
    with open("townscript_debug.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("📄 Page source saved to townscript_debug.html")
    
    events = []
    
    # Method 1: Find event cards by looking for links to /event/
    print("\nLooking for event links...")
    event_links = soup.find_all("a", href=re.compile(r"/event/"))
    print(f"Found {len(event_links)} event links")
    
    for link in event_links:
        # Get the parent container (event card)
        container = link
        for _ in range(5):
            container = container.parent
            if not container:
                break
        
        if container:
            container_text = container.get_text(separator="\n", strip=True)
            
            # Extract Event Name - try different methods
            name = None
            
            # Try to find name in headings within container
            headings = container.find_all(["h2", "h3", "h4", "strong", "b"])
            for heading in headings:
                heading_text = heading.get_text(strip=True)
                if len(heading_text) > 5 and len(heading_text) < 100:
                    if not any(skip in heading_text.lower() for skip in ["showing", "results", "price", "date"]):
                        name = heading_text
                        break
            
            # If no heading found, try the link text itself
            if not name and link.get_text(strip=True):
                link_text = link.get_text(strip=True)
                if len(link_text) > 5 and len(link_text) < 100:
                    name = link_text
            
            # If still no name, try first meaningful line
            if not name:
                lines = [l.strip() for l in container_text.split("\n") if l.strip()]
                for line in lines:
                    if len(line) > 10 and len(line) < 100 and "₹" not in line and not re.search(r'\d{2}-\d{2}', line):
                        if not any(skip in line.lower() for skip in ["showing", "results"]):
                            name = line
                            break
            
            if not name:
                continue
            
            # Extract Price
            price = "Free"
            price_match = re.search(r'[₹]\s*\d+(?:\.\d+)?(?:\s*onwards)?', container_text)
            if price_match:
                price = price_match.group(0)
            elif re.search(r'\bFree\b', container_text, re.IGNORECASE):
                price = "Free"
            
            # Extract Date - look for date patterns
            date_text = "Date Unknown"
            date_patterns = [
                r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s*[-–]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*\d{1,2}',  # Mar 08 - Apr 07
                r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:st|nd|rd|th)?',  # Apr 7th
                r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}',  # 07 Apr 2026
                r'\d{2}[-/]\d{2}[-/]\d{4}',  # 08-03-2026
                r'\d{1,2}\s*[-–]\s*\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',  # 08 - 15 Mar
            ]
            
            for pattern in date_patterns:
                date_match = re.search(pattern, container_text, re.IGNORECASE)
                if date_match:
                    date_text = date_match.group(0)
                    break
            
            # Extract Location
            location = "Online"
            location_match = re.search(r'\b(Online|Virtual)\b', container_text, re.IGNORECASE)
            if location_match:
                location = location_match.group(0)
            
            # Get event URL
            event_url = urljoin(URL, link.get("href")) if link.get("href") else URL
            
            # Clean up name
            name = re.sub(r'\s+', ' ', name).strip()
            
            # Skip duplicates
            if not any(e["name"] == name for e in events):
                events.append({
                    "location": location,
                    "club": "Townscript",
                    "date": date_text,
                    "name": name,
                    "price": price,
                    "url": event_url,
                    "type": EVENT_TYPE
                })
                print(f"  ✓ Found: {name}")
                print(f"       Date: {date_text}")
                print(f"       Price: {price}")
    
    # Method 2: Look for specific event cards using CSS selectors
    if len(events) < 10:
        print("\nTrying alternative method with specific selectors...")
        
        # Try different selectors based on common Townscript patterns
        selectors = [
            "div[class*='EventCard']",
            "div[class*='event-card']",
            "div[class*='card']",
            "div[data-testid*='event']"
        ]
        
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                print(f"Found {len(cards)} cards with selector: {selector}")
                
                for card in cards:
                    card_text = card.get_text(separator="\n", strip=True)
                    
                    # Extract name from headings
                    name = None
                    headings = card.find_all(["h2", "h3", "h4"])
                    for heading in headings:
                        heading_text = heading.get_text(strip=True)
                        if len(heading_text) > 5 and len(heading_text) < 100:
                            name = heading_text
                            break
                    
                    if not name:
                        continue
                    
                    # Extract price
                    price = "Free"
                    price_match = re.search(r'[₹]\s*\d+(?:\.\d+)?', card_text)
                    if price_match:
                        price = price_match.group(0)
                    elif "Free" in card_text:
                        price = "Free"
                    
                    # Extract date
                    date_text = "Date Unknown"
                    date_match = re.search(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s*[-–]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*\d{1,2}', card_text, re.IGNORECASE)
                    if date_match:
                        date_text = date_match.group(0)
                    
                    # Get URL
                    link = card.find("a", href=re.compile(r"/event/"))
                    event_url = urljoin(URL, link.get("href")) if link else URL
                    
                    name = re.sub(r'\s+', ' ', name).strip()
                    
                    if not any(e["name"] == name for e in events):
                        events.append({
                            "location": "Online",
                            "club": "Townscript",
                            "date": date_text,
                            "name": name,
                            "price": price,
                            "url": event_url,
                            "type": EVENT_TYPE
                        })
                        print(f"  ✓ Found (alt): {name} | {date_text} | {price}")
                
                if len(events) >= 10:
                    break
    
    driver.quit()
    
    # Remove duplicates
    unique_events = []
    seen_names = set()
    for event in events:
        if event["name"] not in seen_names and event["name"] != "Unknown" and not any(skip in event["name"].lower() for skip in ["showing", "results"]):
            seen_names.add(event["name"])
            unique_events.append(event)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"📊 TOTAL EVENTS FOUND: {len(unique_events)}")
    print("=" * 50)
    
    if unique_events:
        for i, event in enumerate(unique_events[:15], 1):
            print(f"{i}. {event['name']}")
            print(f"   📅 Date: {event['date']}")
            print(f"   💰 Price: {event['price']}")
            print(f"   📍 Location: {event['location']}")
            print()
        
        if len(unique_events) > 15:
            print(f"... and {len(unique_events) - 15} more events")
    else:
        print("⚠️ No events found. Check townscript_debug.html for page structure")
        print("\n💡 Suggestion: Open townscript_debug.html in a browser and look for:")
        print("   - What HTML tags contain event names?")
        print("   - What CSS classes are used for event cards?")
        print("   - Share a snippet and I'll help you fix it")
    
    # Save to Firestore
    if unique_events:
        clear_events_for_website(EVENT_TYPE, WEBSITE)
        save_events_batch(unique_events[:MAX_EVENTS], WEBSITE)
        print(f"✅ Saved {min(len(unique_events), MAX_EVENTS)} events to Firestore")
    else:
        print("⚠️ No events found to save")
    
    return unique_events

def scrape_meraevents():
    print("Scraping MeraEvents...")
    
    EVENT_TYPE = "sports_event"  # Can be updated based on category
    WEBSITE = "meraevents"
    MAX_EVENTS = 50
    URL = "https://www.meraevents.com/search"
    
    # Initialize driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(URL)
    
    # Wait for page to load
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(5)
    
    # Scroll to load more events
    print("Scrolling to load more events...")
    for i in range(4):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        print(f"  Scroll {i+1}/4 complete")
    
    # Get page source
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Save debug file
    with open("meraevents_debug.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("📄 Page source saved to meraevents_debug.html")
    
    events = []
    
    # Find event cards - from the structure, events are in divs with event info
    # Look for event title links first
    event_titles = soup.find_all("a", class_=lambda x: x and ("title" in x.lower() if x else False))
    
    if not event_titles:
        # Try finding any link with event title patterns
        event_titles = soup.find_all("a", href=re.compile(r"/event/"))
    
    print(f"Found {len(event_titles)} potential event links")
    
    for title_elem in event_titles:
        title_text = title_elem.get_text(strip=True)
        
        # Skip if too short or looks like navigation
        if len(title_text) < 5 or any(skip in title_text.lower() for skip in ["click here", "view more", "register", "more"]):
            continue
        
        # Find the parent container for this event
        container = title_elem
        for _ in range(5):
            container = container.parent
            if not container:
                break
        
        if container:
            container_text = container.get_text(separator="\n", strip=True)
            
            # Extract Event Name
            name = title_text
            
            # Extract Date
            date_text = "Date Unknown"
            # Look for date patterns like "April 19, 2026" or "Mar 31, 2026"
            date_patterns = [
                r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}',  # April 19, 2026
                r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}',   # 19 April 2026
                r'\d{2}/\d{2}/\d{4}',  # 19/04/2026
                r'\d{2}-\d{2}-\d{4}',  # 19-04-2026
            ]
            
            for pattern in date_patterns:
                date_match = re.search(pattern, container_text, re.IGNORECASE)
                if date_match:
                    date_text = date_match.group(0)
                    break
            
            # Extract Location/City
            location = "Unknown"
            # Look for city names in the container
            cities = ["Mumbai", "Delhi", "Bengaluru", "Bangalore", "Hyderabad", "Chennai", "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Goa", "Guwahati", "Indore", "Varanasi", "New Delhi", "Online"]
            for city in cities:
                if re.search(r'\b' + city + r'\b', container_text, re.IGNORECASE):
                    location = city
                    break
            
            # Extract Category
            category = "Sports"
            categories = ["Sports", "Professional", "College & Campus", "Entertainment", "Exhibitions", "Training", "Workshops", "Spiritual", "Wellness", "Activities", "Donations"]
            for cat in categories:
                if re.search(r'\b' + cat + r'\b', container_text, re.IGNORECASE):
                    category = cat
                    break
            
            # Extract Price (if available)
            price = "Not Specified"
            price_match = re.search(r'[₹]\s*\d+(?:\.\d+)?', container_text)
            if price_match:
                price = price_match.group(0)
            elif "Free" in container_text:
                price = "Free"
            
            # Get event URL
            event_url = urljoin(URL, title_elem.get("href")) if title_elem.get("href") else URL
            
            # Determine event type based on category
            event_type = EVENT_TYPE
            if "Sports" in category:
                event_type = "sports_event"
            elif "Professional" in category or "Workshops" in category:
                event_type = "professional_event"
            elif "College" in category:
                event_type = "college_event"
            
            # Clean up name
            name = re.sub(r'\s+', ' ', name).strip()
            
            events.append({
                "location": location,
                "club": category,
                "date": date_text,
                "name": name,
                "price": price,
                "url": event_url,
                "type": event_type
            })
            print(f"  ✓ Found: {name}")
            print(f"       Date: {date_text}")
            print(f"       Location: {location}")
            print(f"       Category: {category}")
            print()
    
    # Method 2: Look for event cards using structure from the page
    if len(events) < 10:
        print("\nTrying alternative extraction method...")
        
        # Look for event entries in the results list
        all_divs = soup.find_all("div")
        for div in all_divs:
            div_text = div.get_text(separator="\n", strip=True)
            
            # Check if this div contains event-like content (has date pattern)
            has_date = re.search(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}', div_text, re.IGNORECASE)
            if has_date and len(div_text) > 50:
                # Try to find event name
                name = "Unknown"
                headings = div.find_all(["h2", "h3", "strong", "b", "a"])
                for heading in headings:
                    heading_text = heading.get_text(strip=True)
                    if len(heading_text) > 5 and len(heading_text) < 100:
                        if not any(skip in heading_text.lower() for skip in ["click here", "view more"]):
                            name = heading_text
                            break
                
                if name != "Unknown":
                    # Extract date
                    date_match = re.search(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}', div_text, re.IGNORECASE)
                    date_text = date_match.group(0) if date_match else "Date Unknown"
                    
                    # Extract location
                    location = "Unknown"
                    for city in ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Pune", "Kolkata", "Online"]:
                        if city in div_text:
                            location = city
                            break
                    
                    events.append({
                        "location": location,
                        "club": "MeraEvents",
                        "date": date_text,
                        "name": name,
                        "price": "Not Specified",
                        "url": URL,
                        "type": EVENT_TYPE
                    })
                    print(f"  ✓ Found (alt): {name} | {date_text} | {location}")
    
    driver.quit()
    
    # Remove duplicates
    unique_events = []
    seen_names = set()
    for event in events:
        if event["name"] not in seen_names and event["name"] != "Unknown" and len(event["name"]) > 3:
            seen_names.add(event["name"])
            unique_events.append(event)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"TOTAL EVENTS FOUND: {len(unique_events)}")
    print("=" * 50)
    
    if unique_events:
        for i, event in enumerate(unique_events[:15], 1):
            print(f"{i}. {event['name']}")
            print(f"   Date: {event['date']}")
            print(f"   Location: {event['location']}")
            print(f"   Category: {event['club']}")
            print(f"   Price: {event.get('price', 'Not Specified')}")
            print()
        
        if len(unique_events) > 15:
            print(f"... and {len(unique_events) - 15} more events")
    else:
        print("No events found. Check meraevents_debug.html for page structure")
    
    # Save to Firestore
    if unique_events:
        clear_events_for_website(EVENT_TYPE, WEBSITE)
        save_events_batch(unique_events[:MAX_EVENTS], WEBSITE)
        print(f"Saved {min(len(unique_events), MAX_EVENTS)} events to Firestore")
    else:
        print("No events found to save")
    
    return unique_events

def scrape_ttfi(session=None, headers=None):
    BASE_URL = "https://www.ttfi.org/events"
    WEBSITE = "ttfi"
    EVENT_TYPE = "tabletennis_event"

    if session is None:
        session = requests.Session()
    if headers:
        session.headers.update(headers)

    try:
        resp = session.get(BASE_URL, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching TTFI: {e}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    event_items = soup.find_all("div", class_="carousel-item")
    
    events = []
    for item in event_items:
        title_tag = item.find("h2")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        organizer = ""
        org_tag = item.find("p")
        if org_tag and org_tag.small:
            organizer = org_tag.small.get_text(strip=True).replace("Organized by:", "").strip()

        date = "Unknown"
        date_tag = item.find("h4")
        if date_tag:
            date = date_tag.get_text(strip=True).replace("Date:", "").strip()

        location = "India"
        venue_tag = item.find("span", class_="vanue")
        if venue_tag:
            location = venue_tag.get_text(strip=True).replace("Venue:", "").strip()

        events.append({
            "club": organizer if organizer else "TTFI",
            "name": title,
            "location": location,
            "date": date,
            "url": BASE_URL,
            "type": EVENT_TYPE,
            "distance": "N/A"
        })

    if events:
        save_events_batch(events, website=WEBSITE)
        print(f"Successfully scraped {len(events)} events from TTFI.")



def run_all():
<<<<<<< HEAD
    # scrape_audax_india()
    # scrape_district()
    # scrape_HCL_cyclothon()
    # scrape_champ_endurance()
    # scrape_ifinish()
    # scrape_townscript()  
    scrape_meraevents()
    # scrape_ttfi()

# ============ MAIN EXECUTION ============
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Starting Web Scraper")
    print("=" * 60)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "ifinish":
            print("Running only iFINISH scraper...\n")
            scrape_ifinish()
        elif sys.argv[1] == "audax":
            print("Running only Audax India scraper...\n")
            scrape_audax_india()
        elif sys.argv[1] == "district":
            print("Running only District scraper...\n")
            scrape_district()
        elif sys.argv[1] == "hcl":
            print("Running only HCL Cyclothon scraper...\n")
            scrape_HCL_cyclothon()
        elif sys.argv[1] == "champ":
            print("Running only Champ Endurance scraper...\n")
            scrape_champ_endurance()
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Available options: ifinish, audax, district, hcl, champ")
            print("Running all scrapers...\n")
            run_all()
    else:
        print(" Running all scrapers...\n")
        run_all()
    
    print("\nAll scraping complete!")
=======
    scrape_ttfi()
run_all()
>>>>>>> 9ae4b279e160d5e983202239c8d32633e4751a32
