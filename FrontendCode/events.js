import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getFirestore, collection, getDocs, doc, updateDoc, increment } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";
// 1. ADD AUTH IMPORTS
import { getAuth, onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

// YOUR CONFIG
const firebaseConfig = {
    apiKey: "AIzaSyCo8N5TfHzWq5PXELyTXoHb_SrzikweBwo",
    authDomain: "minor-project-a5077.firebaseapp.com",
    projectId: "minor-project-a5077",
    storageBucket: "minor-project-a5077.firebasestorage.app",
    messagingSenderId: "525600101149",
    appId: "1:525600101149:web:f98570a47b3e6e582047f4"
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app); // 2. INITIALIZE AUTH

const EVENT_SOURCES = [
    { type: 'organizer', collectionPath: 'events', sourceName: 'Platform Organizers' },
    { type: 'cycle_event', collectionPath: 'scraped_events/cycle_event/audaxindia', sourceName: 'Audax India' },
    { type: 'cycle_event', collectionPath: 'scraped_events/cycle_event/hclcyclothon', sourceName: 'HCL Cyclothon' },
    { type: 'run_event', collectionPath: 'scraped_events/run_event/champendurance', sourceName: 'Champ Endurance' },
    { type: 'sports_event', collectionPath: 'scraped_events/sports_event/bookmyshow', sourceName: 'BookMyShow' }
];

const ICONS = {
    cycle: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 12h18M3 6h18M3 18h18"/></svg>`,
    run: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M14.31 8l5.74 9.94M9.69 8h11.48M7.38 12l5.74-9.94M9.69 16L3.95 6.06M14.31 16H2.83M16.62 12l-5.74 9.94"/></svg>`,
    default: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>`
};

let allEvents = [];

// ==========================================
// AI CHATBOT LOGIC
// ==========================================
const chatRoot = document.getElementById('ai-chat');
const bodyEl = document.getElementById('chat-body');
const input = document.getElementById('chat-input');
const sendBtn = document.getElementById('chat-send');
const toggleBtn = chatRoot ? chatRoot.querySelector('.chat-toggle') : null;
const closeBtn = chatRoot ? chatRoot.querySelector('.chat-close') : null;

function toggleChat(isOpen) {
    if (!chatRoot) return;
    chatRoot.classList.toggle('expanded', isOpen);
    chatRoot.classList.toggle('collapsed', !isOpen);

    if (isOpen) {
        toggleBtn.style.display = "none";
        input.focus();
    } else {
        toggleBtn.style.display = "block";
    }
}

if (toggleBtn) toggleBtn.addEventListener('click', () => toggleChat(true));
if (closeBtn) closeBtn.addEventListener('click', () => toggleChat(false));

function addMessageBox(text, sender) {
    const box = document.createElement('div');
    box.className = `message-box ${sender}`;
    box.textContent = text;
    bodyEl.appendChild(box);
    bodyEl.scrollTop = bodyEl.scrollHeight;
}

async function handleSend() {
    const message = input.value.trim();
    if (!message) return;

    addMessageBox(message, 'user');
    input.value = '';

    sendBtn.disabled = true;
    try {
        const res = await triggerModel(message);
        if (res.reply) {
            addMessageBox(res.reply.reasoning, 'bot');
            setFilters(res.reply.filters);
        }
    } catch (e) {
        console.error(e);
        addMessageBox("Error connecting to AI.", 'bot');
    }
    sendBtn.disabled = false;
}

if (sendBtn) sendBtn.addEventListener('click', handleSend);
if (input) input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSend();
});

async function triggerModel(message) {
    const res = await fetch("http://localhost:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
    });
    return await res.json();
}

function setFilters(filters) {
    for (const [key, value] of Object.entries(filters)) {
        const select = document.getElementById(key);
        if (!select) continue;

        const cleanValue = value.toString().trim().toLowerCase();

        for (let i = 0; i < select.options.length; i++) {
            const optionVal = select.options[i].value;
            if (optionVal.toLowerCase() === cleanValue) {
                select.value = optionVal;
                break;
            }
        }
    }
    applyFilters();
}

// ==========================================
// INITIALIZATION
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    fetchAndRenderEvents();
    setupFilters();
    setupAuth(); // 3. CALL AUTH SETUP
});

// ==========================================
// CLICK TRACKING
// ==========================================
window.trackEventClick = async function (eventId, isOrganizerEvent, redirectUrl) {
    if (isOrganizerEvent) {
        let clickedEvents = JSON.parse(localStorage.getItem('athlyUserClicks') || '[]');

        if (!clickedEvents.includes(eventId)) {
            clickedEvents.push(eventId);
            localStorage.setItem('athlyUserClicks', JSON.stringify(clickedEvents));

            try {
                const eventRef = doc(db, 'events', eventId);
                // Wait for the write to complete, but cap at 500ms so UI doesn't hang
                await Promise.race([
                    updateDoc(eventRef, { clicks: increment(1) }),
                    new Promise(resolve => setTimeout(resolve, 500))
                ]);
            } catch (error) {
                console.error("Error tracking click:", error);
            }
        }
    }

    // Navigate after the write has been sent
    if (redirectUrl && redirectUrl !== '#') {
        window.location.href = redirectUrl;
    }
};

// 4. AUTH FUNCTION
function setupAuth() {
    // Note: events.html uses 'btnLogin' class (no hyphen)
    const loginBtn = document.querySelector('.btnLogin');
    const signupBtn = document.querySelector('.btnSignup');

    // Monitor Login State
    onAuthStateChanged(auth, (user) => {
        if (user) {
            // User is signed in
            const name = user.displayName ? user.displayName.split(' ')[0] : user.email.split('@')[0];
            if (loginBtn) loginBtn.textContent = `Hi, ${name}`;
            if (signupBtn) signupBtn.textContent = "Sign Out";

            // Optional: Disable login click if already logged in
            if (loginBtn) loginBtn.onclick = () => { /* Do nothing or go to profile */ };
        } else {
            // User is signed out
            if (loginBtn) loginBtn.textContent = "Log in";
            if (signupBtn) signupBtn.textContent = "Sign Up";

            // Reset clicks
            if (loginBtn) loginBtn.onclick = () => window.location.href = 'login.html';
        }
    });

    // Handle Sign Out / Sign Up Click
    if (signupBtn) {
        signupBtn.addEventListener('click', () => {
            const user = auth.currentUser;
            if (user) {
                signOut(auth).then(() => {
                    window.location.reload(); // Refresh to update UI
                });
            } else {
                window.location.href = 'login.html?mode=signup';
            }
        });
    }
}

// ==========================================
// DATA FETCHING
// ==========================================

async function fetchAndRenderEvents() {
    const container = document.getElementById('eventsContainer');
    if (!container) return;

    container.innerHTML = '<p style="color:#888; text-align:center; padding:20px;">Loading events...</p>';
    allEvents = [];

    try {
        const promises = EVENT_SOURCES.map(async (source) => {
            const colRef = collection(db, source.collectionPath);
            const snapshot = await getDocs(colRef);
            return snapshot.docs.map(docSnap => {
                const data = docSnap.data();
                return normalizeEventData(data, source, docSnap.id);
            });
        });

        const results = await Promise.all(promises);
        allEvents = results.flat();

        populateFilterOptions();
        renderEvents(allEvents);

    } catch (error) {
        console.error("Error fetching events:", error);
        container.innerHTML = '<p style="color:red; text-align:center;">Error loading events.</p>';
    }
}

function normalizeEventData(data, sourceConfig, docId) {
    let dist = "N/A";
    if (typeof data.distance === 'string') {
        dist = data.distance;
    } else if (typeof data.distance === 'object' && data.distance !== null) {
        dist = Object.values(data.distance).join(', ');
    }

    let title = data.club;
    if (sourceConfig.type === 'organizer') {
        title = data.name || data.title;
    } else if (!title || title === "Not Available") {
        if (sourceConfig.type === 'cycle_event') title = "Cycling Event";
        else if (sourceConfig.type === 'run_event') title = "Running Event";
        else title = "Sports Event";
    }

    if (title && sourceConfig.type !== 'organizer') {
        title = title.split(' ').slice(0, 4).join(' ');
    }

    let difficulty = "Medium";
    if (dist.includes('km')) {
        const distVal = parseInt(dist);
        if (distVal > 100) difficulty = "Difficult";
        else if (distVal < 20) difficulty = "Easy";
    }

    let displayType = "Sports";
    if (sourceConfig.type === 'organizer') {
        displayType = data.sport || "Sports";
    } else if (sourceConfig.type === 'cycle_event') {
        displayType = "Cycling";
    } else if (sourceConfig.type === 'run_event') {
        displayType = "Marathon";
    } else if (sourceConfig.type === 'sports_event') {
        displayType = "Sports";
    }

    const views = Math.floor(Math.random() * (50000 - 1000 + 1)) + 1000;

    // Cards only show City, State
    let locationStr = "Location TBD";
    if (sourceConfig.type === 'organizer') {
        let parts = [];
        if (data.city) parts.push(data.city);
        if (data.state) parts.push(data.state);
        if (parts.length > 0) locationStr = parts.join(', ');
    } else {
        locationStr = data.location || "Online";
    }

    // Use the actual Firestore document ID for organizer events
    const eventId = sourceConfig.type === 'organizer' ? docId : (data.url || docId || Math.random().toString(36));

    return {
        id: eventId,
        title: title,
        organizer: sourceConfig.type === 'organizer' ? (data.organizerName || 'Local Organizer') : sourceConfig.sourceName,
        date: data.date || "Date TBA",
        location: locationStr,
        type: sourceConfig.type,
        displayType: displayType,
        distance: dist,
        difficulty: difficulty,
        price: data.registration_fee || "Check Link",
        url: sourceConfig.type === 'organizer' ? `event-details.html?id=${docId}` : (data.url || "#"),
        views: views,
    };
}

function populateFilterOptions() {
    const locations = new Set();
    const organizers = new Set();
    const types = new Set();
    const difficulties = new Set();

    allEvents.forEach(event => {
        if (event.location && event.location !== "Online") locations.add(event.location);
        if (event.organizer) organizers.add(event.organizer);
        if (event.displayType) types.add(event.displayType);
        if (event.difficulty) difficulties.add(event.difficulty);
    });

    fillSelect('Location', Array.from(locations).sort());
    fillSelect('Organizer', Array.from(organizers).sort());
    fillSelect('Type', Array.from(types).sort());

    const diffOrder = ["Beginner", "Intermediate", "Pro / Elite"];
    const sortedDiff = Array.from(difficulties).sort((a, b) => {
        return diffOrder.indexOf(a) - diffOrder.indexOf(b);
    });
    fillSelect('Difficulty', sortedDiff);
}

function fillSelect(id, items) {
    const select = document.getElementById(id);
    if (!select) return;

    const firstOption = select.options[0];
    select.innerHTML = '';
    select.appendChild(firstOption);

    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item;
        opt.textContent = item;
        select.appendChild(opt);
    });
}

function renderEvents(eventsToRender) {
    const container = document.getElementById('eventsContainer');
    if (!container) return;

    container.innerHTML = '';

    if (eventsToRender.length === 0) {
        container.innerHTML = '<p style="text-align:center; padding:20px; color:#666;">No events found matching filters.</p>';
        return;
    }

    eventsToRender.forEach((event, index) => {
        const cardHTML = createCardHTML(event, index);
        container.insertAdjacentHTML('beforeend', cardHTML);
    });
}

function createCardHTML(event, index) {
    let slideImage = 'Assets/CycleSlideIn.png';
    let iconSvg = ICONS.cycle;

    let difficultyClass = 'diff-med';
    if (event.difficulty === "Pro / Elite") difficultyClass = 'diff-hard';
    else if (event.difficulty === "Beginner") difficultyClass = 'diff-easy';

    if (event.type === 'run_event') {
        slideImage = 'Assets/RunningSlideIn.png';
        iconSvg = ICONS.run;
    } else if (event.type === 'sports_event') {
        iconSvg = ICONS.default;
    }

    const viewString = event.views > 1000 ? (event.views / 1000).toFixed(1) + 'k' : event.views;
    const animationDelay = index * 0.05;

    return `
    <div class="card" style="animation-delay: ${animationDelay}s; cursor: pointer;" onclick="trackEventClick('${event.id}', ${event.type === 'organizer'}, '${event.url}')">
        <img src="${slideImage}" alt="" class="cardBgIcon">
        <div class="cardLeftCol">
            <div class="cardIcon">${iconSvg}</div>
            <div class="meterWrapper">
                <div class="difficultyMeter ${difficultyClass}">
                    <span class="difficultyText">${event.difficulty}</span>
                </div>
            </div>
        </div>
        
        <div class="cardContent">
            <div class="cardHeader">
                <span class="cardTitle" style="font-size: 1.125rem; font-weight: 600;">${event.title}</span>
                <span class="cardAuthor">by <span style="color: #a1a1aa;">${event.organizer}</span></span>
            </div>
            <p class="cardDesc">${event.location} • ${event.date}</p>
            <div class="cardTags">
                 <button class="btnCardLink" style="font-family: inherit;">${event.type === 'organizer' ? 'Register' : 'Link'}</button>
            </div>
        </div>

        <div class="cardStats">
            <div class="statRow">
                <svg class="statIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
                <span>${event.distance}</span>
            </div>
            <div class="statRow updateInfo">
                <svg class="statIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                <span>${viewString}</span>
            </div>
        </div>
    </div>
    `;
}

function setupFilters() {
    const relevanceDropdown = document.getElementById('Relevance');
    if (relevanceDropdown) {
        relevanceDropdown.addEventListener('change', () => applyFilters());
    }

    const filters = {
        type: document.getElementById('Type'),
        location: document.getElementById('Location'),
        organizer: document.getElementById('Organizer'),
        distance: document.getElementById('Distance'),
        difficulty: document.getElementById('Difficulty')
    };

    Object.values(filters).forEach(select => {
        if (select) {
            select.addEventListener('change', () => applyFilters());
        }
    });
}

window.applyFilters = function () {
    const relevanceVal = document.getElementById('Relevance')?.value || 'None';
    const typeVal = document.getElementById('Type')?.value || 'None';
    const locVal = document.getElementById('Location')?.value || 'None';
    const orgVal = document.getElementById('Organizer')?.value || 'None';
    const diffVal = document.getElementById('Difficulty')?.value || 'None';

    let filtered = allEvents.filter(event => {
        if (typeVal !== 'None' && event.displayType !== typeVal) return false;
        if (locVal !== 'None' && event.location !== locVal) return false;
        if (orgVal !== 'None' && event.organizer !== orgVal) return false;
        if (diffVal !== 'None' && event.difficulty !== diffVal) return false;
        return true;
    });

    if (relevanceVal === 'Most Popular') {
        filtered.sort((a, b) => b.views - a.views);
    }

    renderEvents(filtered);
}