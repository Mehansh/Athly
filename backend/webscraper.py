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
    #firestore batch limit is 500
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

        #Firestore batch safety (max 500)
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

def scrape_district():
    print("Scraping District...")

    URL = "https://www.district.in/activities/"
    EVENT_TYPE = "activity_event"
    WEBSITE = "district"
    MAX_EVENTS = 10

    driver = webdriver.Chrome()
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

    driver = webdriver.Chrome()
    events = []

    for edition_name, url in EDITION_URLS.items():

        driver.get(url)
        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        full_text = soup.get_text(" ", strip=True)

        # --------------------
        # Extract Date
        # --------------------
        date = "Not Available"
        date_match = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
            full_text
        )
        if date_match:
            date = date_match.group(0)

        # --------------------
        # Extract Categories
        # --------------------
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

            # Extract distance
            distance_matches = re.findall(r"\d+\s?km", text.lower())
            distances = list(set(distance_matches)) if distance_matches else ["Not Available"]

            # Extract bicycle type
            bicycle_type = "Not Available"
            if "Road Cycles" in text:
                bicycle_type = "Road"
            elif "MTB Cycles" in text:
                bicycle_type = "MTB"
            elif "Road and Hybrid" in text or "Hybrid" in text:
                bicycle_type = "Road & Hybrid"
            elif "Any cycle" in text:
                bicycle_type = "Any"

            # Extract registration fee
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

    driver = webdriver.Chrome()
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

        # Open event page
        driver.get(event_url)
        time.sleep(4)

        detail_soup = BeautifulSoup(driver.page_source, "html.parser")
        full_text = detail_soup.get_text(" ", strip=True)

        # ---------------------
        # Extract Distances
        # ---------------------
        distances = re.findall(r"\d+\s?km", full_text.lower())
        distances = list(set(distances)) if distances else ["Not Available"]

        # ---------------------
        # Extract Participants
        # ---------------------
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


def run_all():
    scrape_audax_india()
    scrape_district()
    scrape_HCL_cyclothon()
    scrape_champ_endurance()
run_all()