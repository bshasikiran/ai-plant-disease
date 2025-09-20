// Chat Widget JavaScript
let chatSession = generateSessionId();
let selectedChatImage = null;
let isChatMinimized = true;

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function toggleChat() {
    const widget = document.getElementById('chatWidget');
    widget.classList.toggle('minimized');
    isChatMinimized = !isChatMinimized;
    
    if (!isChatMinimized) {
        document.getElementById('chatInput').focus();
    }
}

// Initialize chat widget as minimized
document.addEventListener('DOMContentLoaded', function() {
    const widget = document.getElementById('chatWidget');
    if (widget) {
        widget.classList.add('minimized');
    }
    
    // Handle image selection
    const chatImageInput = document.getElementById('chatImageInput');
    if (chatImageInput) {
        chatImageInput.addEventListener('change', handleChatImageSelect);
    }
});

function handleChatImageSelect(e) {
    const file = e.target.files[0];
    if (file) {
        if (file.size > 5 * 1024 * 1024) {
            alert('Image size should be less than 5MB');
            return;
        }
        
        selectedChatImage = file;
        displayChatImagePreview(file);
    }
}

function displayChatImagePreview(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        const preview = document.getElementById('chatImagePreview');
        const container = document.getElementById('imagePreviewContainer');
        
        preview.src = e.target.result;
        container.style.display = 'block';
    };
    reader.readAsDataURL(file);
}

function removeChatImage() {
    selectedChatImage = null;
    document.getElementById('chatImageInput').value = '';
    document.getElementById('imagePreviewContainer').style.display = 'none';
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message && !selectedChatImage) return;
    
    // Display user message
    displayMessage(message, 'user', selectedChatImage);
    
    // Clear input
    input.value = '';
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        const formData = new FormData();
        formData.append('session_id', chatSession);
        formData.append('message', message || 'Please analyze this image');
        formData.append('language', document.getElementById('language')?.value || 'en');
        
        if (selectedChatImage) {
            formData.append('image', selectedChatImage);
        }
        
        const response = await fetch('/chat', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        // Hide typing indicator
        hideTypingIndicator();
        
        if (response.ok) {
            // Display bot response
            displayMessage(data.response, 'bot');
            
            // Update suggestions if provided
            if (data.suggestions && data.suggestions.length > 0) {
                updateSuggestions(data.suggestions);
            }
        } else {
            displayMessage('Sorry, I encountered an error. Please try again.', 'bot');
        }
        
    } catch (error) {
        console.error('Chat error:', error);
        hideTypingIndicator();
        displayMessage('Sorry, I could not process your request. Please try again.', 'bot');
    }
    
    // Clear selected image after sending
    if (selectedChatImage) {
        removeChatImage();
    }
}

function displayMessage(message, sender, imageFile = null) {
    const messagesContainer = document.getElementById('chatMessages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = sender === 'user' ? '👤' : '🤖';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    // Add text
    if (message) {
        const textDiv = document.createElement('div');
        textDiv.innerHTML = formatMessage(message);
        content.appendChild(textDiv);
    }
    
    // Add image if present
    if (imageFile && sender === 'user') {
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = document.createElement('img');
            img.src = e.target.result;
            img.className = 'message-image';
            img.onclick = () => window.open(e.target.result, '_blank');
            content.appendChild(img);
        };
        reader.readAsDataURL(imageFile);
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    messagesContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function formatMessage(message) {
    // Convert line breaks to <br>
    message = message.replace(/\n/g, '<br>');
    
    // Convert numbered lists
    message = message.replace(/(\d+\.\s)/g, '<br>$1');
    
    // Make links clickable
    message = message.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
    
    return message;
}

function showTypingIndicator() {
    const messagesContainer = document.getElementById('chatMessages');
    
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typingIndicator';
    typingDiv.className = 'chat-message bot-message';
    typingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

function updateSuggestions(suggestions) {
    const container = document.getElementById('chatSuggestions');
    if (!container) return;
    
    container.innerHTML = '';
    
    suggestions.forEach(suggestion => {
        const chip = document.createElement('button');
        chip.className = 'suggestion-chip';
        chip.textContent = suggestion;
        chip.onclick = () => sendSuggestion(suggestion);
        container.appendChild(chip);
    });
}

function sendSuggestion(text) {
    document.getElementById('chatInput').value = text;
    sendChatMessage();
}

// Enter key to send
document.addEventListener('keypress', function(e) {
    if (e.target.id === 'chatInput' && e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
    }
});