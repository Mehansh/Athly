import firebase_admin
from firebase_admin import credentials, firestore
import requests
from bs4 import BeautifulSoup
import hashlib  # <--- Added this tool to fix the ID length issue

# --- PART 1: CONNECT TO FIREBASE ---
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
print("Connected to Firestore successfully!")

# --- PART 2: SCRAPE AUDAX INDIA ---
URL = "https://www.audaxindia.in/events.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

print("Visiting Audax India...")
response = requests.get(URL, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

events_found = 0
rows = soup.find_all("tr")

for row in rows:
    cols = row.find_all("td")
    
    if len(cols) > 2:
        event_name = cols[0].text.strip()
        event_date = cols[1].text.strip()
        event_location = cols[2].text.strip()

        # --- THE FIX IS HERE ---
        # We combine name + date to ensure uniqueness
        unique_string = f"{event_name}_{event_date}"
        
        # We turn that long string into a short, unique ID (MD5 hash)
        event_id = hashlib.md5(unique_string.encode('utf-8')).hexdigest()

        event_data = {
            "title": event_name,
            "date": event_date,
            "location": event_location,
            "source": "Audax India"
        }
        
        try:
            db.collection("scraped_events").document(event_id).set(event_data)
            print(f"Saved: {event_name[:30]}...") # Print only first 30 chars to keep screen clean
            events_found += 1
        except Exception as e:
            print(f"Skipped an event due to error: {e}")

print(f"Finished! Saved {events_found} events to Firebase.")