/**
 * Chat Service Integration
 * Integrasi frontend dengan backend chat service untuk generate prompt
 */

class ChatService {
    constructor() {
        this.baseUrl = '/api/chat';
        this.endpoints = {
            music: '/generate-music-prompt',
            video: '/generate-video-prompt',
            photo: '/generate-photo-prompt',
            general: '/generate-prompt'
        };
    }

    /**
     * Generate prompt berdasarkan tipe
     * @param {string} input - Input dari user
     * @param {string} type - Tipe prompt (music, video, photo)
     * @returns {Promise<Object>} - Hasil generate prompt
     */
    async generatePrompt(input, type = 'music') {
        try {
            const endpoint = this.endpoints[type] || this.endpoints.general;
            const url = `${this.baseUrl}${endpoint}`;
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    input: input,
                    type: type 
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return result;
        } catch (error) {
            console.error('ChatService Error:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Generate music prompt untuk Suno AI
     * @param {string} input - Deskripsi musik
     * @returns {Promise<Object>} - Hasil generate prompt musik
     */
    async generateMusicPrompt(input) {
        return this.generatePrompt(input, 'music');
    }

    /**
     * Generate video prompt
     * @param {string} input - Deskripsi video
     * @returns {Promise<Object>} - Hasil generate prompt video
     */
    async generateVideoPrompt(input) {
        return this.generatePrompt(input, 'video');
    }

    /**
     * Generate photo prompt
     * @param {string} input - Deskripsi foto
     * @returns {Promise<Object>} - Hasil generate prompt foto
     */
    async generatePhotoPrompt(input) {
        return this.generatePrompt(input, 'photo');
    }

    /**
     * Copy text ke clipboard
     * @param {string} text - Text yang akan di-copy
     * @returns {Promise<boolean>} - True jika berhasil
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (error) {
            console.error('Copy to clipboard failed:', error);
            return false;
        }
    }

    /**
     * Show notification
     * @param {string} message - Pesan notifikasi
     * @param {string} type - Tipe notifikasi (success, error, warning)
     */
    showNotification(message, type = 'success') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'warning'} alert-dismissible fade show position-fixed`;
        notification.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Add to body
        document.body.appendChild(notification);

        // Auto remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }

    /**
     * Create loading spinner
     * @returns {HTMLElement} - Loading spinner element
     */
    createLoadingSpinner() {
        const spinner = document.createElement('div');
        spinner.className = 'loading';
        spinner.style.cssText = `
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #6c63ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        `;
        return spinner;
    }

    /**
     * Show typing indicator
     * @param {HTMLElement} container - Container untuk typing indicator
     */
    showTypingIndicator(container) {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator show';
        indicator.innerHTML = `
            <span class="loading me-2"></span>
            AI sedang memproses...
        `;
        
        if (container) {
            container.appendChild(indicator);
            container.scrollTop = container.scrollHeight;
        }
    }

    /**
     * Hide typing indicator
     * @param {HTMLElement} container - Container untuk typing indicator
     */
    hideTypingIndicator(container) {
        const indicator = container.querySelector('.typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * Add message ke chat container
     * @param {string} content - Konten pesan
     * @param {string} sender - Pengirim (user/bot)
     * @param {HTMLElement} container - Container chat
     */
    addMessage(content, sender, container) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = content.replace(/\n/g, '<br>');
        
        messageDiv.appendChild(contentDiv);
        container.appendChild(messageDiv);
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    /**
     * Set loading state untuk button
     * @param {HTMLElement} button - Button element
     * @param {boolean} loading - Loading state
     */
    setButtonLoading(button, loading) {
        const textSpan = button.querySelector('.btn-text');
        const loadingSpan = button.querySelector('.loading');
        
        if (loading) {
            button.disabled = true;
            if (textSpan) textSpan.style.display = 'none';
            if (loadingSpan) loadingSpan.classList.remove('d-none');
        } else {
            button.disabled = false;
            if (textSpan) textSpan.style.display = 'inline';
            if (loadingSpan) loadingSpan.classList.add('d-none');
        }
    }
}

// Export untuk penggunaan global
window.ChatService = ChatService;

// Auto-initialize jika ada form chat
document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chatForm');
    if (chatForm) {
        const chatService = new ChatService();
        
        chatForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const userInput = document.getElementById('userInput');
            const promptType = document.getElementById('promptType');
            const sendBtn = document.getElementById('sendBtn');
            const chatMessages = document.getElementById('chatMessages');
            const promptResult = document.getElementById('promptResult');
            const generatedPrompt = document.getElementById('generatedPrompt');
            
            const input = userInput.value.trim();
            const type = promptType.value;
            
            if (!input) {
                chatService.showNotification('Silakan masukkan deskripsi yang Anda inginkan!', 'warning');
                return;
            }
            
            // Set loading state
            chatService.setButtonLoading(sendBtn, true);
            
            // Add user message
            chatService.addMessage(input, 'user', chatMessages);
            
            // Show typing indicator
            chatService.showTypingIndicator(chatMessages);
            
            try {
                // Generate prompt
                const result = await chatService.generatePrompt(input, type);
                
                if (result.success) {
                    // Add bot response
                    chatService.addMessage(
                        `Berikut adalah prompt yang saya buat untuk Anda:\n\n**${result.prompt}**`, 
                        'bot', 
                        chatMessages
                    );
                    
                    // Show prompt result
                    if (promptResult && generatedPrompt) {
                        generatedPrompt.textContent = result.prompt;
                        promptResult.classList.add('show');
                        
                        // Store current prompt for copy function
                        window.currentPrompt = result.prompt;
                    }
                    
                    chatService.showNotification('Prompt berhasil dibuat!', 'success');
                } else {
                    chatService.addMessage(
                        'Maaf, terjadi kesalahan saat generate prompt. Silakan coba lagi.', 
                        'bot', 
                        chatMessages
                    );
                    chatService.showNotification(result.error || 'Terjadi kesalahan', 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                chatService.addMessage(
                    'Maaf, terjadi kesalahan. Silakan coba lagi.', 
                    'bot', 
                    chatMessages
                );
                chatService.showNotification('Terjadi kesalahan jaringan', 'error');
            } finally {
                // Hide loading state
                chatService.setButtonLoading(sendBtn, false);
                chatService.hideTypingIndicator(chatMessages);
                
                // Clear input
                userInput.value = '';
                userInput.focus();
            }
        });
    }
});

// Global copy function
window.copyPrompt = async function() {
    if (window.currentPrompt) {
        const chatService = new ChatService();
        const success = await chatService.copyToClipboard(window.currentPrompt);
        
        if (success) {
            chatService.showNotification('Prompt berhasil disalin!', 'success');
            
            // Update button text temporarily
            const copyBtn = document.getElementById('copyBtn');
            if (copyBtn) {
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="bi bi-check me-1"></i>Copied!';
                copyBtn.style.background = '#28a745';
                
                setTimeout(() => {
                    copyBtn.innerHTML = originalText;
                    copyBtn.style.background = '#6c63ff';
                }, 2000);
            }
        } else {
            chatService.showNotification('Gagal menyalin prompt. Silakan copy manual.', 'error');
        }
    }
}; 