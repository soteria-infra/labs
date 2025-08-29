const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const protectionToggle = document.getElementById('protectionToggle');
const statusTag = document.getElementById('statusTag');

let ws;
let isConnected = false;

function connectWebSocket() {
  ws = new WebSocket('ws://localhost:8000/ws');
 
  ws.addEventListener('open', () => {
    isConnected = true;
    sendButton.disabled = false;
    console.log('Connected to WebSocket');
  });
 
  ws.addEventListener('close', () => {
    isConnected = false;
    sendButton.disabled = true;
    displaySystemMessage('Connection lost. Attempting to reconnect...');
    setTimeout(connectWebSocket, 3000);
  });
 
  ws.addEventListener('error', (error) => {
    console.error('WebSocket error:', error);
    displaySystemMessage('Connection error occurred');
  });

  ws.addEventListener('message', (event) => {
    const message = event.data;
    displayMessage(message, false);
  });
}

// Initialize WebSocket connection
connectWebSocket();

// Toggle protection mode
protectionToggle.addEventListener('change', () => {
  const isProtected = protectionToggle.checked;
  updateStatusTag(isProtected);
 
  if (isConnected) {
    const toggleMessage = JSON.stringify({
      type: 'toggle',
      protected: isProtected
    });
    ws.send(toggleMessage);
  }
});

function updateStatusTag(isProtected) {
  if (isProtected) {
    statusTag.textContent = 'Protected';
    statusTag.className = 'status-tag status-protected';
  } else {
    statusTag.textContent = 'Vulnerable';
    statusTag.className = 'status-tag status-vulnerable';
  }
}

sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    sendMessage();
  }
});

function sendMessage() {
  const message = messageInput.value.trim();
  if (!message || !isConnected) return;
 
  const chatMessage = JSON.stringify({
    type: 'chat',
    message: message
  });
 
  ws.send(chatMessage);
  displayMessage(message, true);
  messageInput.value = '';
}

function displayMessage(message, isSender = false) {
  const messageContainer = document.createElement('div');
  const messageElement = document.createElement('div');
  messageElement.textContent = message;
 
  messageContainer.classList.add('message-container');
 
  if (isSender) {
    messageContainer.classList.add('sender-message-container');
    messageElement.classList.add('message-bubble', 'sender-message-bubble');
  } else {
    messageElement.classList.add('message-bubble');
  }
 
  messageContainer.appendChild(messageElement);
  messagesDiv.appendChild(messageContainer);
 
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function displaySystemMessage(message) {
  const systemMessage = document.createElement('div');
  systemMessage.classList.add('system-message');
  systemMessage.textContent = message;
  messagesDiv.appendChild(systemMessage);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Initialize status tag
updateStatusTag(true);