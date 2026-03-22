# Athly

> **"Uncover the sports the world forgot"**

Athly is a full-stack web application for discovering, discussing, and organising sports events of all kinds. It aggregates events from multiple external sources via web scraping, enables AI-powered natural language search through a local LLM, and provides community features for athletes and organisers.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Directory Structure](#directory-structure)
- [Key Technologies](#key-technologies)
- [Code Organisation](#code-organisation)
  - [Frontend](#frontend)
  - [Backend](#backend)
- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [Getting Started](#getting-started)

---

## Project Overview

Athly solves the problem of sports event discoverability. Niche events — obscure cycling challenges, ultra-marathons, triathlons — are scattered across many small websites and are hard to find. Athly:

- **Scrapes** events from multiple external sports websites and stores them centrally.
- **Searches** events semantically using a local LLM and vector embeddings, letting users query in plain English (e.g. *"marathons in Mumbai for beginners"*).
- **Hosts** user-created events and organiser profiles.
- **Connects** a community through discussion threads.

---

## Directory Structure

```
Athly/
├── FrontendCode/               # Static frontend (HTML / CSS / JS)
│   ├── Assets/                 # Images and graphics
│   ├── icons/                  # SVG icon set (13 files)
│   ├── *.html                  # One HTML file per page (see list below)
│   ├── events.css              # Global stylesheet
│   └── events.js               # All client-side logic & Firebase SDK calls
│
├── backend/                    # Python backend
│   ├── app.py                  # Flask API server (entry point)
│   ├── model.py                # LLM query-parsing via LangChain + Mistral
│   ├── vectordb.py             # Chroma vector store (semantic search)
│   ├── datamanager.py          # Firebase Firestore client + helper queries
│   ├── webscraper.py           # Selenium / BeautifulSoup event scrapers
│   └── chroma_db_events/       # Persisted Chroma vector database (local)
│
├── firestore.rules             # Firebase security rules
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── read.txt                    # Developer notes on architecture split
```

---

## Key Technologies

### Frontend
| Technology | Purpose |
|---|---|
| HTML5 / CSS3 / Vanilla JS | UI — no framework used |
| Firebase SDK v10.8 (Firestore, Auth, Storage) | Real-time database, user authentication |
| Inter (Google Fonts) | Typography |

### Backend
| Technology | Purpose |
|---|---|
| Python 3 | Backend language |
| Flask + Flask-CORS | REST API server |
| LangChain + LangChain-Ollama | LLM orchestration |
| Mistral (via Ollama) | Natural language query parsing |
| mxbai-embed-large (via Ollama) | Text embeddings for semantic search |
| LangChain-Chroma / Chroma | Local vector database |
| Firebase Admin SDK | Server-side Firestore access |
| Selenium + BeautifulSoup4 | Dynamic and static web scraping |
| Pandas | Data processing utilities |

---

## Code Organisation

### Frontend

Located in `FrontendCode/`.

**Pages (`*.html`)**

| File | Description |
|---|---|
| `index.html` | Landing / home page |
| `events.html` | Main event discovery page with AI chat assistant |
| `login.html` | Sign-in page |
| `register.html` | New user registration |
| `community.html` | Discussion threads |
| `dashboard.html` | Organiser dashboard (manage own events) |
| `add_event.html` | Create a new event |
| `event-details.html` | Full event detail view |
| `profile.html` | Athlete profile |
| `organizer-profile.html` | Organiser profile |

**`events.js`** — all client-side logic (~600 lines):
- Firebase initialisation and configuration.
- Fetches events from both `events` and `scraped_events` Firestore collections.
- Renders event cards and handles filter interactions (drag-and-drop chips).
- Drives the AI chat widget — sends the user's query to `POST /chat` and displays results.
- Manages authentication state across pages.
- Tracks event clicks and participant counts.

**`events.css`** — global styles:
- Dark theme (`background: #09090b`).
- Gradient accents (blue → purple).
- Responsive grid layouts and chat widget styling.

---

### Backend

Located in `backend/`.

#### `app.py` — Flask entry point
Starts the API server on `http://localhost:5000`. Exposes a single route:

```
POST /chat   { "message": "<user query>" }
```

Calls `model.py` to parse the query, then `vectordb.py` to retrieve matching events, and returns both.

#### `model.py` — LLM query parsing
- Loads the **Mistral** model through LangChain-Ollama (falls back to `phi3:mini`).
- Sends the user's natural-language message through a structured prompt.
- Returns a JSON object of extracted filters: `Relevance`, `Difficulty`, `Distance`, `Type`, `Location`, `Organizer`.

#### `vectordb.py` — semantic vector search
- Wraps a **Chroma** collection persisted in `chroma_db_events/`.
- `addEvents(events)` — embeds and stores event documents with metadata.
- `retrieveEvents(query, k=5)` — similarity search; returns the `k` most relevant events for a given query string.

#### `datamanager.py` — Firestore client
- Initialises the Firebase Admin SDK using a service-account key (`serviceAccountKey.json`, git-ignored).
- `getDatabase()` — returns the Firestore client.
- `get_db_filters()` — reads the live list of locations and organiser names from Firestore (used to prime the LLM prompt context).

#### `webscraper.py` — event aggregation (~450 lines)
Scrapes four external sources and writes events to both Firestore and Chroma:

| Scraper | Source | Method |
|---|---|---|
| Audax India | Cycling events | HTTP + BeautifulSoup |
| HCL Cyclothon | Multi-city cycling | Selenium |
| District.in | Activity events | Selenium + JS rendering |
| Champ Endurance | Running events | Selenium |

Events are normalised to a common schema before being batch-uploaded to Firestore (100 documents per batch) and stored in Chroma for semantic search.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Browser (HTML / CSS / JS)                    │
│                                                                  │
│   index / login / register  ──►  events  ──►  community         │
│                                  (AI chat, filter chips)        │
│                   dashboard / add_event / profiles              │
└───────────────────────┬──────────────────────────────────────────┘
                        │  Firebase SDK  (Auth + Firestore)
          ┌─────────────▼──────────────────┐
          │         Firebase Cloud          │
          │  ┌────────────┐ ┌───────────┐  │
          │  │  Firestore │ │   Auth    │  │
          │  └────────────┘ └───────────┘  │
          └─────────────────────────────────┘

          (Backend scraper also writes to Firestore via Admin SDK)

┌──────────────────────────────────────────────────────────────────┐
│              Backend  (Flask  –  localhost:5000)                  │
│                                                                  │
│  POST /chat                                                      │
│    │                                                             │
│    ├─► model.py  (Mistral via Ollama)  → structured filters      │
│    │                                                             │
│    └─► vectordb.py  (Chroma)  → top-K matching events            │
│                                                                  │
│  webscraper.py  (Selenium + BeautifulSoup)                       │
│    └─► Audax India / HCL Cyclothon / District.in / Champ End.   │
│          │                      │                               │
│          ▼                      ▼                               │
│     Firestore              chroma_db_events/                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Firestore Collections

**`users/{userId}`**
```
name        : string
email       : string
role        : "athlete" | "organizer"
profileData : map
```

**`events/{eventId}`** — user-created events
```
title        : string
description  : string
location     : string
date         : string
type         : "Marathon" | "Cycling" | "Triathlon" | "Swimming" | "Sports"
difficulty   : "Beginner" | "Intermediate" | "Pro/Elite"
distance     : string
organizerId  : string   (→ users)
clicks       : number
participants : number
```

**`scraped_events/{eventType}/{source}/{eventId}`** — external events
```
location          : string
club              : string   (organiser name)
date              : string   (DD/MM)
url               : string   (link to original page)
type              : string   (e.g. "cycle_event", "run_event")
distance          : string[]
bicycle_type?     : string
registration_fee? : string
participants?     : number
```

Example sub-collection paths:
- `scraped_events/cycle_event/audaxindia/`
- `scraped_events/cycle_event/hclcyclothon/`
- `scraped_events/run_event/champendurance/`

**`threads/{threadId}`** — community discussions
```
title     : string
content   : string
authorUid : string
likes     : number
createdAt : timestamp
```

**`registrations/{regId}`** — event sign-ups
```
userId       : string
eventId      : string
registeredAt : timestamp
```

### Local Chroma DB (`backend/chroma_db_events/`)

Stores vector embeddings of scraped events (using `mxbai-embed-large`) for similarity search. Each document includes event metadata as Chroma metadata fields.

---

## API Reference

### `POST /chat`

Send a natural-language query. Returns structured filters extracted by the LLM and the top matching events from the vector store.

**Request**
```json
{ "message": "cycling events near Pune for intermediate riders" }
```

**Response**
```json
{
  "reply": {
    "filters": {
      "Location": "Pune",
      "Type": "Cycling",
      "Difficulty": "Intermediate",
      "Relevance": null,
      "Distance": null,
      "Organizer": null
    },
    "reasoning": "Looking for cycling events in Pune suited for intermediate riders."
  },
  "events": [
    {
      "title": "Pune Cyclothon 2025",
      "location": "Pune",
      "date": "15/04",
      "distance": "100km",
      "url": "https://example.com/event",
      "type": "cycle_event"
    }
  ]
}
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running locally with `mistral` and `mxbai-embed-large` models pulled
- A Firebase project with Firestore enabled and a `serviceAccountKey.json` downloaded into `backend/`

### Install Python dependencies

```bash
pip install -r requirements.txt
```

### Run the web scraper (populate the database)

```bash
python backend/webscraper.py
```

### Start the backend API

```bash
python backend/app.py
```

The API will be available at `http://localhost:5000`.

### Open the frontend

Open `FrontendCode/index.html` in your browser, or serve the `FrontendCode/` directory with any static file server.

> **Note:** The Firebase configuration embedded in `events.js` points to the project's own Firebase instance. To use your own Firebase project, replace the `firebaseConfig` object in `events.js` and update `firestore.rules`.