/**
 * I NEMI Backend Integration JavaScript
 * This file provides functions to interact with the Python Flask backend
 */

// Backend API configuration
const BACKEND_URL = 'http://localhost:5000';

// API utility functions
class INEMIBackend {
    constructor() {
        this.baseUrl = BACKEND_URL;
    }

    // Generic API call function
    async apiCall(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                }
            };

            if (data) {
                options.body = JSON.stringify(data);
            }

            const response = await fetch(`${this.baseUrl}${endpoint}`, options);
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'API call failed');
            }

            return result;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // Health check
    async healthCheck() {
        return await this.apiCall('/api/health');
    }

    // Generate text using AI
    async generateText(prompt) {
        return await this.apiCall('/api/generate-text', 'POST', { prompt });
    }

    // Generate creative content
    async generateCreativeContent(type, topic, style = 'creative') {
        return await this.apiCall('/api/generate-creative-content', 'POST', {
            type,
            topic,
            style
        });
    }

    // Analyze sentiment
    async analyzeSentiment(text) {
        return await this.apiCall('/api/analyze-sentiment', 'POST', { text });
    }

    // Translate text
    async translateText(text, targetLanguage, sourceLanguage = 'auto') {
        return await this.apiCall('/api/translate', 'POST', {
            text,
            target_language: targetLanguage,
            source_language: sourceLanguage
        });
    }

    // Chat with AI
    async chat(message, userId = 'default') {
        return await this.apiCall('/api/chat', 'POST', {
            message,
            user_id: userId
        });
    }

    // Analyze image
    async analyzeImage(imageData, prompt = 'Describe this image in detail') {
        return await this.apiCall('/api/generate-image-description', 'POST', {
            image: imageData,
            prompt
        });
    }
}

// Initialize backend instance
const backend = new INEMIBackend();

// UI Helper functions
class INEMIUI {
    constructor() {
        this.backend = backend;
        this.currentUserId = 'user_' + Date.now();
    }

    // Show loading state
    showLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = '<div class="loading">Loading...</div>';
            element.style.opacity = '0.7';
        }
    }

    // Hide loading state
    hideLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.opacity = '1';
        }
    }

    // Show error message
    showError(message, elementId = 'error-message') {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `<div class="error">${message}</div>`;
            element.style.display = 'block';
            setTimeout(() => {
                element.style.display = 'none';
            }, 5000);
        } else {
            alert('Error: ' + message);
        }
    }

    // Show success message
    showSuccess(message, elementId = 'success-message') {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `<div class="success">${message}</div>`;
            element.style.display = 'block';
            setTimeout(() => {
                element.style.display = 'none';
            }, 3000);
        }
    }

    // Generate text content
    async generateTextContent(prompt, outputElementId) {
        try {
            this.showLoading(outputElementId);
            const result = await this.backend.generateText(prompt);
            document.getElementById(outputElementId).innerHTML = result.response;
            this.hideLoading(outputElementId);
        } catch (error) {
            this.showError(error.message);
            this.hideLoading(outputElementId);
        }
    }

    // Generate creative content
    async generateCreativeContent(type, topic, style, outputElementId) {
        try {
            this.showLoading(outputElementId);
            const result = await this.backend.generateCreativeContent(type, topic, style);
            document.getElementById(outputElementId).innerHTML = result.content;
            this.hideLoading(outputElementId);
        } catch (error) {
            this.showError(error.message);
            this.hideLoading(outputElementId);
        }
    }

    // Send chat message
    async sendChatMessage(message, chatContainerId) {
        try {
            const chatContainer = document.getElementById(chatContainerId);
            
            // Add user message
            const userMessage = document.createElement('div');
            userMessage.className = 'chat-message user-message';
            userMessage.innerHTML = `<p>${message}</p>`;
            chatContainer.appendChild(userMessage);

            // Add loading indicator for AI response
            const loadingMessage = document.createElement('div');
            loadingMessage.className = 'chat-message ai-message loading';
            loadingMessage.innerHTML = '<p>AI is typing...</p>';
            chatContainer.appendChild(loadingMessage);

            // Get AI response
            const result = await this.backend.chat(message, this.currentUserId);
            
            // Replace loading with AI response
            loadingMessage.innerHTML = `<p>${result.response}</p>`;
            loadingMessage.classList.remove('loading');

            // Scroll to bottom
            chatContainer.scrollTop = chatContainer.scrollHeight;
        } catch (error) {
            this.showError(error.message);
        }
    }

    // Analyze image
    async analyzeImageContent(imageFile, outputElementId) {
        try {
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    this.showLoading(outputElementId);
                    const result = await this.backend.analyzeImage(e.target.result);
                    document.getElementById(outputElementId).innerHTML = result.description;
                    this.hideLoading(outputElementId);
                } catch (error) {
                    this.showError(error.message);
                    this.hideLoading(outputElementId);
                }
            };
            reader.readAsDataURL(imageFile);
        } catch (error) {
            this.showError(error.message);
        }
    }

    // Analyze sentiment
    async analyzeTextSentiment(text, outputElementId) {
        try {
            this.showLoading(outputElementId);
            const result = await this.backend.analyzeSentiment(text);
            document.getElementById(outputElementId).innerHTML = result.analysis;
            this.hideLoading(outputElementId);
        } catch (error) {
            this.showError(error.message);
            this.hideLoading(outputElementId);
        }
    }

    // Translate text
    async translateTextContent(text, targetLanguage, outputElementId) {
        try {
            this.showLoading(outputElementId);
            const result = await this.backend.translateText(text, targetLanguage);
            document.getElementById(outputElementId).innerHTML = result.translation;
            this.hideLoading(outputElementId);
        } catch (error) {
            this.showError(error.message);
            this.hideLoading(outputElementId);
        }
    }
}

// Initialize UI instance
const inemiUI = new INEMIUI();

// Example usage functions for HTML integration
function generateTextFromPrompt() {
    const prompt = document.getElementById('prompt-input').value;
    if (prompt.trim()) {
        inemiUI.generateTextContent(prompt, 'output-container');
    } else {
        inemiUI.showError('Please enter a prompt');
    }
}

function generateCreativeContent() {
    const type = document.getElementById('content-type').value;
    const topic = document.getElementById('content-topic').value;
    const style = document.getElementById('content-style').value;
    
    if (topic.trim()) {
        inemiUI.generateCreativeContent(type, topic, style, 'creative-output');
    } else {
        inemiUI.showError('Please enter a topic');
    }
}

function sendChatMessage() {
    const messageInput = document.getElementById('chat-input');
    const message = messageInput.value.trim();
    
    if (message) {
        inemiUI.sendChatMessage(message, 'chat-container');
        messageInput.value = '';
    } else {
        inemiUI.showError('Please enter a message');
    }
}

function handleImageUpload() {
    const fileInput = document.getElementById('image-upload');
    const file = fileInput.files[0];
    
    if (file) {
        inemiUI.analyzeImageContent(file, 'image-analysis-output');
    } else {
        inemiUI.showError('Please select an image');
    }
}

function analyzeSentiment() {
    const text = document.getElementById('sentiment-text').value;
    if (text.trim()) {
        inemiUI.analyzeTextSentiment(text, 'sentiment-output');
    } else {
        inemiUI.showError('Please enter text to analyze');
    }
}

function translateText() {
    const text = document.getElementById('translate-text').value;
    const targetLanguage = document.getElementById('target-language').value;
    
    if (text.trim()) {
        inemiUI.translateTextContent(text, targetLanguage, 'translation-output');
    } else {
        inemiUI.showError('Please enter text to translate');
    }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('I NEMI Backend Integration loaded');
    
    // Test backend connection
    backend.healthCheck()
        .then(() => console.log('✅ Backend connected successfully'))
        .catch(() => console.warn('⚠️ Backend not available - make sure to run: python app.py'));
}); 