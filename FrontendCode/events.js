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

function handleSend() {
    const message = input.value.trim();
    if (!message) return;
    
    addMessageBox(message, 'user');
    input.value = '';

    setTimeout(() => {
        addMessageBox("I'm a simple bot reply!", 'bot');
    }, 600);
}

sendBtn.addEventListener('click', handleSend);

input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleSend();
    }
});