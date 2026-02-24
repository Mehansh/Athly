const chatRoot = document.getElementById('ai-chat');
const bodyEl = document.getElementById('chat-body');
const input = document.getElementById('chat-input');
const sendBtn = document.getElementById('chat-send');
const toggleBtn = chatRoot.querySelector('.chat-toggle');
const closeBtn = chatRoot.querySelector('.chat-close');

function toggleChat(isOpen) {
    chatRoot.classList.toggle('expanded', isOpen);
    chatRoot.classList.toggle('collapsed', !isOpen);
    
    if (isOpen) {
        toggleBtn.style.display = "none";
        input.focus();
    } else {
        toggleBtn.style.display = "block";
    }
}

toggleBtn.addEventListener('click', () => toggleChat(true));
closeBtn.addEventListener('click', () => toggleChat(false));

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
    const res = await triggerModel(message);
    sendBtn.disabled = false;
    console.log(res);
    addMessageBox(res.reply.reasoning, 'bot');
    setFilters(res.reply.filters);
}

sendBtn.addEventListener('click', handleSend);

input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleSend();
    }
});

async function triggerModel(message) {
    const res = await fetch("http://localhost:5000/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message})
    });

    const data = await res.json();
    return data;
}

function setFilters(filters) {
    for (const [key, value] of Object.entries(filters)) {
        const select = document.getElementById(key);
        if (!select) continue;

        select.value = value;
    }
}