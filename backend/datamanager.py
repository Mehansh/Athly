import os
import firebase_admin
from firebase_admin import credentials, firestore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(BASE_DIR, "serviceAccountKey.json")

try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate(KEY_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def getDatabase():
    return db

def get_db_filters():
    """
    Fetches all unique Locations and Clubs (Organizers) from the database
    so the AI knows what actually exists.
    """
    try:
        docs = db.collection("scraped_events").stream()
        
        locations = set()
        organizers = set()

        for doc in docs:
            data = doc.to_dict()
            
            if "location" in data and data["location"] and data["location"] != "Online":
                locations.add(data["location"])
                
            if "club" in data and data["club"]:
                organizers.add(data["club"])
            elif "organizer" in data and data["organizer"]:
                organizers.add(data["organizer"])

        return {
            "Location": sorted(list(locations)),
            "Organizer": sorted(list(organizers))
        }
    except Exception as e:
        print(f"Error fetching DB filters: {e}")
        return { 
            "Location": ["Mumbai", "Pune", "Delhi", "Bangalore"], 
            "Organizer": [] 
        }