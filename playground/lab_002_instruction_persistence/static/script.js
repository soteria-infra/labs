const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const protectionToggle = document.getElementById('protectionToggle');
const statusTag = document.getElementById('statusTag');

let ws;
let isConnected = false;

function connectWebSocket() {
  // Use the current host and port for WebSocket connection
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
  ws = new WebSocket(wsUrl);

  ws.addEventListener('open', () => {
    isConnected = true;
    sendButton.disabled = false;
    console.log('Connected to WebSocket');
    displaySystemMessage('Connected to chat.');
    // Send initial toggle state to server if checkbox is not default checked
    if (!protectionToggle.checked) {
      sendToggleState(false);
    }
  });

  ws.addEventListener('close', () => {
    isConnected = false;
    sendButton.disabled = true;
    console.log('Disconnected from WebSocket. Attempting to reconnect...');
    displaySystemMessage('Connection lost. Attempting to reconnect...');
    setTimeout(connectWebSocket, 3000); // Attempt to reconnect after 3 seconds
  });

  ws.addEventListener('error', (error) => {
    console.error('WebSocket error:', error);
    displaySystemMessage('Connection error occurred');
    ws.close(); // Force close to trigger reconnect logic
  });

  ws.addEventListener('message', (event) => {
    const message = event.data;
    // Check if the message is a system message about mode change
    if (message.startsWith("Mode switched to:")) {
      displaySystemMessage(message);
    } else {
      displayMessage(message, false); // Display as AI message
    }
  });
}

// Initialize WebSocket connection
connectWebSocket();

// Function to send toggle state to the server
function sendToggleState(isProtected) {
  if (isConnected) {
    const toggleMessage = JSON.stringify({
      type: 'toggle',
      protected: isProtected
    });
    ws.send(toggleMessage);
    console.log(`Sent toggle message: ${toggleMessage}`);
  }
}

// Toggle protection mode
protectionToggle.addEventListener('change', () => {
  const isProtected = protectionToggle.checked;
  updateStatusTag(isProtected);
  sendToggleState(isProtected); // Send the new state to the server
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
  displayMessage(message, true); // Display user's message immediately
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

  // Scroll to the bottom of the messages container
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function displaySystemMessage(message) {
  const systemMessage = document.createElement('div');
  systemMessage.classList.add('system-message');
  systemMessage.textContent = message;
  messagesDiv.appendChild(systemMessage);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Initialize status tag on page load
updateStatusTag(protectionToggle.checked);