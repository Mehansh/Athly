import requests
from bs4 import BeautifulSoup
import hashlib
from datamanager import getDatabase
import re
from urllib.parse import urljoin
from math import ceil
db = getDatabase()

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
def save_event(event, event_type = "cycle_event"):
    unique_string = f"{event['title']}|{event['date']}|{event['location']}"
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

        # Firestore batch safety (max 500)
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

def run_all():
    scrape_audax_india()

run_all()