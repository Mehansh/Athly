import json
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


BASE_URL = "https://www.champendurance.com/all-events"


def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")  # Uncomment for headless mode
    driver = webdriver.Chrome(options=options)
    return driver


def scrape_champ_endurance():

    driver = create_driver()
    driver.get(BASE_URL)

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    events = []

    # Find all anchor tags that link to event pages
    links = soup.find_all("a", href=True)

    for link in links:

        href = link["href"]

        # Filter only event detail links
        if "/event/" not in href:
            continue

        event_url = href if href.startswith("http") else f"https://www.champendurance.com{href}"

        event_name = link.get_text(strip=True)
        if not event_name:
            continue

        # Open event detail page
        driver.get(event_url)
        time.sleep(4)

        detail_soup = BeautifulSoup(driver.page_source, "html.parser")
        full_text = detail_soup.get_text(" ", strip=True)

        # ----------------------
        # Venue Extraction
        # ----------------------
        venue = "Not Available"
        venue_match = re.search(r"(Venue|Location)\s*:\s*(.*?)(?=Date|Distance|Participants)", full_text, re.IGNORECASE)
        if venue_match:
            venue = venue_match.group(2).strip()

        # ----------------------
        # Distance Extraction
        # ----------------------
        distances = re.findall(r"\d+\s?km", full_text.lower())
        distances = list(set(distances)) if distances else ["Not Available"]

        # ----------------------
        # Participants Extraction
        # ----------------------
        participants = "Not Available"
        part_match = re.search(r"(\d{2,5})\s*(Participants|Runners)", full_text, re.IGNORECASE)
        if part_match:
            participants = part_match.group(1)

        events.append({
            "event_name": event_name,
            "event_venue": venue,
            "event_distances": distances,
            "participants": participants,
            "event_url": event_url
        })

        # Go back to main page
        driver.get(BASE_URL)
        time.sleep(3)

    driver.quit()

    # Remove duplicate events
    unique_events = {e["event_url"]: e for e in events}.values()

    with open("champ_endurance_events.json", "w", encoding="utf-8") as f:
        json.dump(list(unique_events), f, indent=4, ensure_ascii=False)

    print("✅ Champ Endurance events scraped successfully!")
    print("Total events:", len(unique_events))


if __name__ == "__main__":
    scrape_champ_endurance()