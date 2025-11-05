// Declare global function early to prevent ReferenceError
if (typeof window.toggleMobileNotifications === 'undefined') {
    window.toggleMobileNotifications = function() {
        console.log('🔔 Global mobile notification toggle called (early fallback)');
        console.log('🔔 Window notification system exists:', !!window.notificationSystem);
        
        if (window.notificationSystem) {
            console.log('🔔 Calling toggleNotifications()');
            window.notificationSystem.toggleNotifications();
        } else {
            console.log('🔔 Notification system not ready, will be handled by proper initialization');
        }
    };
}

// Notification System
class NotificationSystem {
    constructor() {
        this.notificationCount = 0;
        this.notifications = [];
        this.isOpen = false;
        this.isProcessing = false;
        this.isInitialized = false;
        
        console.log('🔧 NotificationSystem constructor - no loading state');
        
        // Add resize listener to maintain center positioning
        window.addEventListener('resize', () => this.handleResize());
        window.addEventListener('orientationchange', () => this.handleResize());
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
        this.init();
        }
    }

    init() {
        if (this.isInitialized) {
            console.log('Notification system already initialized, skipping...');
            return;
        }
        
        console.log('Initializing notification system...');
        
        this.createNotificationUI();
        this.loadNotifications();
        this.startPolling();
        
        // Add mobile nav event listeners with multiple attempts
        this.ensureMobileNavListeners();
        
        this.isInitialized = true;
        console.log('Notification system initialized successfully');
    }
    
    ensureMobileNavListeners() {
        // Try multiple times to ensure mobile nav listeners are added
        let attempts = 0;
        const maxAttempts = 5;
        
        const tryAddMobileNav = () => {
            attempts++;
            console.log(`Attempt ${attempts} to add mobile nav listeners`);
            
            const mobileBell = document.getElementById('notification-bell-mobile');
            if (mobileBell) {
                this.addToMobileNav();
                console.log('Mobile nav listeners added successfully');
            } else if (attempts < maxAttempts) {
                console.log('Mobile bell not found, retrying in 200ms...');
                setTimeout(tryAddMobileNav, 200);
            } else {
                console.error('Mobile bell not found after maximum attempts');
            }
        };
        
        tryAddMobileNav();
    }

    handleResize() {
        // If notifications are open, reposition them
        if (this.isOpen) {
            const dropdown = document.getElementById('notification-dropdown');
            if (dropdown) {
                const isMobile = window.innerWidth <= 768;
                
                // Force repositioning
                dropdown.style.setProperty('position', 'fixed', 'important');
                dropdown.style.setProperty('top', '50%', 'important');
                dropdown.style.setProperty('left', '50%', 'important');
                dropdown.style.setProperty('transform', 'translate(-50%, -50%)', 'important');
                dropdown.style.setProperty('width', isMobile ? '95%' : '90%', 'important');
                dropdown.style.setProperty('max-width', isMobile ? 'none' : '420px', 'important');
                dropdown.style.setProperty('margin', '0', 'important');
                
                console.log('Repositioned notification dropdown after resize');
            }
        }
    }

    createNotificationUI() {
        console.log('Creating notification UI...');
        
        // Create notification bell icon
        const notificationBell = document.createElement('div');
        notificationBell.className = 'notification-bell';
        notificationBell.innerHTML = `
            <div class="notification-icon">
                <i class="bi bi-bell"></i>
                <span class="notification-badge" id="notification-badge">0</span>
            </div>
        `;

        // Create overlay and dropdown separately
        const overlay = document.createElement('div');
        overlay.className = 'notification-overlay';
        overlay.id = 'notification-overlay';
        
        const dropdown = document.createElement('div');
        dropdown.className = 'notification-dropdown';
        dropdown.id = 'notification-dropdown';
        dropdown.innerHTML = `
            <div class="notification-header">
                <h3>Notifikasi</h3>
                <div class="notification-header-actions">
                    <button class="mark-all-read" onclick="notificationSystem.markAllAsRead()">
                        <i class="bi bi-check-all"></i> Tandai Semua Dibaca
                    </button>
                    <button class="close-notifications" onclick="notificationSystem.closeNotifications()">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
            </div>
            <div class="notification-list" id="notification-list">
                <div class="no-notifications" style="padding: 3rem 1.5rem; text-align: center; color: var(--text-secondary, #ccc);">
                    <i class="bi bi-bell-slash" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                    <p style="margin: 0; font-size: 1rem;">Tidak ada notifikasi</p>
                    <p style="margin: 0.5rem 0 0 0; font-size: 0.875rem; opacity: 0.7;">Anda akan menerima notifikasi di sini</p>
                </div>
            </div>
            <div class="notification-footer">
                <a href="/notifications" class="view-all-notifications">
                    Lihat Semua Notifikasi
                </a>
            </div>
        `;
        
        // Add mobile-specific CSS for better touch interaction
        const style = document.createElement('style');
        style.textContent = `
            .notification-item {
                transition: background-color 0.2s ease, transform 0.1s ease;
                user-select: none;
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
            }
            
            .notification-item:active {
                transform: scale(0.98);
                background-color: rgba(168, 85, 247, 0.1) !important;
            }
            
            .notification-item:hover {
                background-color: rgba(168, 85, 247, 0.05);
            }
            
            @media (max-width: 768px) {
                .notification-item {
                    min-height: 60px;
                    padding: 12px 16px;
                }
                
                .notification-item:active {
                    background-color: rgba(168, 85, 247, 0.15) !important;
                }
            }
        `;
        document.head.appendChild(style);

        // Add click event to notification bell
        notificationBell.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('Notification bell clicked!');
            this.toggleNotifications();
        });

        // Close dropdown when clicking overlay
        overlay.addEventListener('click', (e) => {
            console.log('Overlay clicked, closing notifications');
            this.closeNotifications();
        });

        // Add swipe gesture for mobile
        this.addSwipeGesture();

        // Add elements to body
        document.body.appendChild(overlay);
        document.body.appendChild(dropdown);
        
        // Clear any loading state in the newly created dropdown
        this.clearLoadingState();

        // Try to add to header next to upgrade button (mobile-friendly)
        this.addToHeader();
        
        // Also try to add to sidebar navigation for desktop
        this.addToSidebar();

        // Setup event listeners for existing notification bells in HTML
        // Use setTimeout to ensure DOM is ready and dropdown is created
        setTimeout(() => {
            console.log('Setting up notification system...');
            this.setupExistingNotificationBells();
            // Clear any loading state first
            this.clearLoadingState();
            // Load notifications after setup
            this.loadNotifications();
            this.loadUnreadCount();
            console.log('Notification system setup completed');
        }, 500);
    }

    addToHeader() {
        // Try to find header and add notification bell next to upgrade button
        const header = document.querySelector('header') || document.querySelector('.header') || document.querySelector('.navbar');
        if (header) {
            console.log('Header found, adding notification bell');
            
            // Look for upgrade button
            const upgradeButton = header.querySelector('.upgrade-btn') || 
                                 header.querySelector('[class*="upgrade"]') || 
                                 header.querySelector('button');
            
            if (upgradeButton) {
                console.log('Upgrade button found, adding notification bell next to it');
                
                // Create notification bell for header
                const headerNotificationBell = document.createElement('div');
                headerNotificationBell.className = 'notification-bell-header';
                headerNotificationBell.innerHTML = `
                    <div class="notification-icon-header">
                        <i class="bi bi-bell"></i>
                        <span class="notification-badge-header" id="notification-badge-header">0</span>
                    </div>
                `;
                
                // Add click event
                headerNotificationBell.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Header notification clicked!');
                    this.toggleNotifications();
                });
                
                // Insert before upgrade button
                upgradeButton.parentNode.insertBefore(headerNotificationBell, upgradeButton);
            } else {
                // If no upgrade button, add to header anyway
                console.log('No upgrade button found, adding notification bell to header');
                const headerNotificationBell = document.createElement('div');
                headerNotificationBell.className = 'notification-bell-header';
                headerNotificationBell.innerHTML = `
                    <div class="notification-icon-header">
                        <i class="bi bi-bell"></i>
                        <span class="notification-badge-header" id="notification-badge-header">0</span>
                    </div>
                `;
                
                headerNotificationBell.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Header notification clicked!');
                    this.toggleNotifications();
                });
                
                header.appendChild(headerNotificationBell);
            }
        } else {
            console.log('No header found, trying mobile navigation');
            this.addToMobileNav();
        }
    }

    addToSidebar() {
        // Notification bell is already in HTML sidebar, just add click event
        const sidebarBell = document.getElementById('notification-bell-sidebar');
        if (sidebarBell) {
            console.log('Sidebar notification bell found, adding click event');
            
            // Remove any existing event listeners first
            const newSidebarBell = sidebarBell.cloneNode(true);
            sidebarBell.parentNode.replaceChild(newSidebarBell, sidebarBell);
            
            // Add click event to the new element
            newSidebarBell.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Sidebar notification clicked!', e.target);
                this.toggleNotifications();
            });
            
            // Also add click event to the inner icon
            const iconElement = newSidebarBell.querySelector('#notification-icon-sidebar');
            if (iconElement) {
                iconElement.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Sidebar notification icon clicked!', e.target);
                    this.toggleNotifications();
                });
            }
        } else {
            console.log('Sidebar notification bell not found!');
        }
    }

    addToMobileNav() {
        // Notification bell is already in HTML mobile navbar with onclick attribute
        const mobileBell = document.getElementById('notification-bell-mobile');
        if (mobileBell) {
            console.log('Mobile notification bell found, setting up event handlers');
            
            // Remove any existing event listeners to prevent duplication
            const newMobileBell = mobileBell.cloneNode(true);
            mobileBell.parentNode.replaceChild(newMobileBell, mobileBell);
            
            // Only use onclick attribute, remove event listeners to prevent double execution
            newMobileBell.setAttribute('onclick', 'toggleMobileNotifications()');
            newMobileBell.setAttribute('ontouchstart', 'toggleMobileNotifications()');
            
            // Remove onclick and ontouchstart to prevent double execution
            newMobileBell.removeAttribute('onclick');
            newMobileBell.removeAttribute('ontouchstart');
            
            // Use only event listeners with proper debouncing
            let clickTimeout = null;
            
            newMobileBell.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Mobile notification clicked!');
                
                // Debounce to prevent double execution
                if (clickTimeout) {
                    clearTimeout(clickTimeout);
                }
                
                clickTimeout = setTimeout(() => {
                    if (typeof window.toggleMobileNotifications === 'function') {
                        window.toggleMobileNotifications();
                    } else {
                        console.error('toggleMobileNotifications function not available');
                    }
                }, 100);
            });
            
            console.log('Mobile notification bell event handlers added (single execution)');
        } else {
            console.log('Mobile notification bell not found!');
        }
    }

    setupExistingNotificationBells() {
        // Setup event listeners for notification bells that already exist in HTML
        const notificationBells = [
            'notification-bell-header',
            'notification-bell-sidebar'
            // Removed 'notification-bell-mobile' to avoid duplication with addToMobileNav()
        ];

        notificationBells.forEach(bellId => {
            const bell = document.getElementById(bellId);
            if (bell) {
                console.log(`Setting up event listener for ${bellId}`);
                
                // Check if event listener is already attached
                if (bell.hasAttribute('data-event-attached')) {
                    console.log(`Event listener already attached to ${bellId}`);
                    return;
                }

                // Add click event listener
                bell.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log(`${bellId} clicked!`);
                    console.log('Event target:', e.target);
                    console.log('Event currentTarget:', e.currentTarget);
                    this.toggleNotifications();
                });

                // Add touch event listener for mobile
                bell.addEventListener('touchstart', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log(`${bellId} touched!`);
                    console.log('Touch event target:', e.target);
                    console.log('Touch event currentTarget:', e.currentTarget);
                    this.toggleNotifications();
                });

                // Mark as having event listener attached
                bell.setAttribute('data-event-attached', 'true');
            } else {
                console.log(`Notification bell ${bellId} not found in HTML`);
            }
        });
    }

    async loadNotifications() {
        try {
            console.log('Fetching notifications...');
            
            // If we already have notifications, just render them
            if (this.notifications.length > 0) {
                console.log('✅ Already have notifications, rendering immediately');
                this.renderNotifications();
                return;
            }
            
            // Load notifications from API
            const response = await fetch('/api/notifications');
            const data = await response.json();
            
            console.log('Notifications response:', data);
            
            if (data.success) {
                this.notifications = data.notifications || [];
                console.log('Loaded notifications:', this.notifications);
                this.updateNotificationBadge();
                
                // Clear any loading state and render notifications immediately
                this.clearLoadingState();
                console.log('✅ Rendering notifications after load');
                this.renderNotifications();
            } else {
                console.error('Failed to load notifications:', data.error);
                this.clearLoadingState();
                this.renderErrorState('Gagal memuat notifikasi');
            }
        } catch (error) {
            console.error('Error fetching notifications:', error);
            this.clearLoadingState();
            this.renderErrorState('Terjadi kesalahan saat memuat notifikasi');
        }
    }
    
    clearLoadingState() {
        const notificationList = document.getElementById('notification-list');
        if (notificationList) {
            console.log('🧹 Clearing loading state from notification list');
            
            // Remove any loading spinners or loading text
            const loadingElements = notificationList.querySelectorAll('.loading-spinner, .loading-text, [class*="loading"]');
            loadingElements.forEach(element => element.remove());
            
            // Clear any loading-related content by replacing the entire content if it contains loading text
            if (notificationList.innerHTML.includes('Memuat notifikasi') || 
                notificationList.innerHTML.includes('Loading notifications') ||
                notificationList.innerHTML.includes('spinner') ||
                notificationList.innerHTML.includes('bi-arrow-clockwise') ||
                notificationList.innerHTML.includes('bi-arrow-repeat')) {
                console.log('🧹 Found loading content, clearing it');
                // Replace loading content with empty state
                notificationList.innerHTML = `
                    <div class="no-notifications" style="padding: 3rem 1.5rem; text-align: center; color: var(--text-secondary, #ccc);">
                        <i class="bi bi-bell-slash" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                        <p style="margin: 0; font-size: 1rem;">Tidak ada notifikasi</p>
                        <p style="margin: 0.5rem 0 0 0; font-size: 0.875rem; opacity: 0.7;">Anda akan menerima notifikasi di sini</p>
                    </div>
                `;
            }
        }
    }

    renderErrorState(message) {
        const notificationList = document.getElementById('notification-list');
        if (notificationList) {
            notificationList.innerHTML = `
                <div class="no-notifications" style="padding: 3rem 1.5rem; text-align: center;">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem; margin-bottom: 1rem; color: #ff6b6b;"></i>
                    <p style="margin: 0; font-size: 1rem; color: #ff6b6b;">${message}</p>
                    <button onclick="window.notificationSystem.loadNotifications()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: var(--primary-color, #a855f7); color: white; border: none; border-radius: 8px; cursor: pointer;">
                        Coba Lagi
                    </button>
                </div>
            `;
        }
    }

    async loadUnreadCount() {
        try {
            const response = await fetch('/api/notifications/unread-count');
            
            // Check if response is OK and is JSON
            if (!response.ok) {
                console.warn(`Failed to fetch unread count: ${response.status} ${response.statusText}`);
                return;
            }
            
            // Check content type before parsing
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                console.warn('Response is not JSON, skipping unread count update');
                return;
            }
            
            const data = await response.json();
            
            if (data && data.success) {
                this.notificationCount = data.unread_count || 0;
                this.updateNotificationBadge();
            } else {
                console.warn('Failed to load unread count:', data?.error || 'Unknown error');
            }
        } catch (error) {
            // Only log error if it's not a JSON parse error (which is expected if endpoint doesn't exist)
            if (error.name !== 'SyntaxError') {
                console.error('Error fetching unread count:', error);
            }
            // Silently fail - don't spam console with expected errors
        }
    }

    updateNotificationBadge() {
        // Update all badge elements
        const badges = [
            document.getElementById('notification-badge'),
            document.getElementById('notification-badge-sidebar'),
            document.getElementById('notification-badge-mobile'),
            document.getElementById('notification-badge-header')
        ];
        
        badges.forEach(badge => {
            if (badge) {
                badge.textContent = this.notificationCount;
                badge.style.display = this.notificationCount > 0 ? 'block' : 'none';
            }
        });
        
        console.log('Updated notification badges, count:', this.notificationCount);
    }

    renderNotifications() {
        const notificationList = document.getElementById('notification-list');
        if (!notificationList) {
            console.error('Notification list element not found!');
            return;
        }

        console.log('🔄 renderNotifications called - notifications:', this.notifications.length);

        // Clear any existing loading state first
        this.clearLoadingState();

        // Direct render based on data availability
        if (this.notifications.length === 0) {
            console.log('No notifications to display');
            notificationList.innerHTML = `
                <div class="no-notifications" style="padding: 3rem 1.5rem; text-align: center; color: var(--text-secondary, #ccc);">
                    <i class="bi bi-bell-slash" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                    <p style="margin: 0; font-size: 1rem;">Tidak ada notifikasi</p>
                    <p style="margin: 0.5rem 0 0 0; font-size: 0.875rem; opacity: 0.7;">Anda akan menerima notifikasi di sini</p>
                </div>
            `;
            return;
        }

        // Render notifications directly without any loading state
        console.log('✅ Rendering notifications directly');
        this.renderNotificationItems(notificationList);
    }

    renderNotificationItems(notificationList) {
        console.log('🎯 renderNotificationItems called - notifications:', this.notifications.length);
        
        notificationList.innerHTML = this.notifications.map(notification => `
            <div class="notification-item ${notification.is_read ? 'read' : 'unread'}" 
                 data-id="${notification.id}" 
                 data-content-type="${notification.content_type}"
                 data-content-id="${notification.content_id}"
                 style="cursor: pointer; touch-action: manipulation; -webkit-tap-highlight-color: transparent;">
                <div class="notification-avatar">
                    <img src="${notification.sender_avatar || '/static/assets/image/default.jpg'}" 
                         alt="${notification.sender_username || 'User'}" 
                         onerror="this.src='/static/assets/image/default.jpg'"
                         style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; pointer-events: none;">
                </div>
                <div class="notification-content">
                    <div class="notification-text">
                        <strong style="color: var(--text-primary, #fff);">${notification.sender_username || 'User'}</strong>
                        <span style="color: var(--text-secondary, #ccc);">${this.getNotificationText(notification)}</span>
                    </div>
                    <div class="notification-time" style="color: var(--text-secondary, #888); font-size: 0.75rem; margin-top: 0.25rem;">
                        ${notification.time_ago || 'Baru saja'}
                    </div>
                </div>
                <div class="notification-status" style="display: flex; align-items: center;">
                    ${!notification.is_read ? '<div class="unread-dot" style="width: 8px; height: 8px; background: var(--primary-color, #a855f7); border-radius: 50%; flex-shrink: 0;"></div>' : ''}
                </div>
            </div>
        `).join('');
        
        // Add event listeners to notification items
        this.addNotificationClickListeners();

        console.log('✅ Notifications rendered successfully, count:', this.notifications.length);
    }

    addNotificationClickListeners() {
        const notificationItems = document.querySelectorAll('.notification-item');
        console.log(`Adding click listeners to ${notificationItems.length} notification items`);
        
        notificationItems.forEach(item => {
            // Remove any existing listeners to prevent duplication
            const newItem = item.cloneNode(true);
            item.parentNode.replaceChild(newItem, item);
            
            // Add both click and touchstart events for better mobile support
            newItem.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.handleNotificationItemClick(newItem);
            });
            
            newItem.addEventListener('touchstart', (e) => {
                e.preventDefault();
                e.stopPropagation();
                // Add visual feedback for touch
                newItem.style.backgroundColor = 'rgba(168, 85, 247, 0.1)';
                setTimeout(() => {
                    newItem.style.backgroundColor = '';
                }, 150);
            });
            
            newItem.addEventListener('touchend', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.handleNotificationItemClick(newItem);
            });
        });
    }

    handleNotificationItemClick(item) {
        const notificationId = item.getAttribute('data-id');
        const contentType = item.getAttribute('data-content-type');
        const contentId = item.getAttribute('data-content-id');
        
        console.log('Notification item clicked:', { notificationId, contentType, contentId });
        
        if (notificationId && contentType && contentId) {
            this.handleNotificationClick(notificationId, contentType, contentId);
        } else {
            console.error('Missing notification data:', { notificationId, contentType, contentId });
        }
    }

    getNotificationText(notification) {
        switch (notification.type) {
            case 'like':
                return `menyukai ${this.getContentTypeText(notification.content_type)} Anda <span class="notification-type-icon">❤️</span>`;
            case 'comment':
                return `mengomentari ${this.getContentTypeText(notification.content_type)} Anda: "${notification.text}" <span class="notification-type-icon">💬</span>`;
            case 'comment_reply':
                return `membalas komentar Anda: "${notification.text}" <span class="notification-type-icon">↩️</span>`;
            case 'follow':
                return 'mulai mengikuti Anda <span class="notification-type-icon">👥</span>';
            default:
                return 'berinteraksi dengan konten Anda <span class="notification-type-icon">✨</span>';
        }
    }

    getContentTypeText(contentType) {
        switch (contentType) {
            case 'image':
                return 'foto';
            case 'video':
                return 'video';
            case 'song':
                return 'musik';
            case 'video_iklan':
                return 'video iklan';
            default:
                return 'konten';
        }
    }

    async handleNotificationClick(notificationId, contentType, contentId) {
        // Mark as read
        await this.markAsRead(notificationId);
        
        // Navigate to content
        let url = '';
        switch (contentType) {
            case 'image':
                url = `/post_image/${contentId}`;
                break;
            case 'video':
                url = `/post_video/${contentId}`;
                break;
            case 'song':
                url = `/post_musik/${contentId}`;
                break;
            case 'video_iklan':
                url = `/post_video_iklan/${contentId}`;
                break;
        }
        
        if (url) {
            window.location.href = url;
        }
    }

    async markAsRead(notificationId) {
        try {
            await fetch('/api/notifications/mark-read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ notification_id: notificationId })
            });
            
            // Update local state
            const notification = this.notifications.find(n => n.id == notificationId);
            if (notification) {
                notification.is_read = true;
                this.notificationCount = Math.max(0, this.notificationCount - 1);
                this.updateNotificationBadge();
                this.renderNotifications();
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }

    async markAllAsRead() {
        try {
            await fetch('/api/notifications/mark-read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });
            
            // Update local state
            this.notifications.forEach(n => n.is_read = true);
            this.notificationCount = 0;
            this.updateNotificationBadge();
            this.renderNotifications();
        } catch (error) {
            console.error('Error marking all notifications as read:', error);
        }
    }

    toggleNotifications() {
        console.log('🔔 Toggle notifications called, isOpen:', this.isOpen);
        console.log('🔔 Processing flag:', this.isProcessing);
        console.log('🔔 Notification system instance:', this);
        
        // Prevent multiple rapid toggles
        if (this.isProcessing) {
            console.log('🔔 Already processing toggle, ignoring');
            return;
        }
        
        this.isProcessing = true;
        console.log('🔔 Set processing flag to true');
        
        // Ensure notification elements exist
        this.ensureNotificationElements();
        
        const dropdown = document.getElementById('notification-dropdown');
        const overlay = document.getElementById('notification-overlay');
        
        if (!dropdown || !overlay) {
            console.error('Dropdown or overlay not found after creation attempt!');
            this.isProcessing = false;
            return;
        }

        if (this.isOpen) {
            this.closeNotifications();
        } else {
            this.openNotifications();
        }
        
        // Reset processing flag after a shorter delay for better mobile experience
        setTimeout(() => {
            this.isProcessing = false;
            console.log('🔔 Reset processing flag to false');
        }, 300);
    }
    
    ensureNotificationElements() {
        // Create overlay if it doesn't exist
        if (!document.getElementById('notification-overlay')) {
            console.log('Creating notification overlay...');
            const overlay = document.createElement('div');
            overlay.className = 'notification-overlay';
            overlay.id = 'notification-overlay';
            overlay.style.cssText = `
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 100% !important;
                height: 100% !important;
                background: rgba(0, 0, 0, 0.7) !important;
                z-index: 9999 !important;
                display: none !important;
                opacity: 0 !important;
                transition: opacity 0.3s ease !important;
                backdrop-filter: blur(5px) !important;
                -webkit-backdrop-filter: blur(5px) !important;
            `;
            document.body.appendChild(overlay);
            
            overlay.addEventListener('click', (e) => {
                console.log('Overlay clicked, closing notifications');
                this.closeNotifications();
            });
        }
        
        // Create dropdown if it doesn't exist
        if (!document.getElementById('notification-dropdown')) {
            console.log('Creating notification dropdown...');
            const dropdown = document.createElement('div');
            dropdown.className = 'notification-dropdown';
            dropdown.id = 'notification-dropdown';
            
            // Check if mobile
            const isMobile = window.innerWidth <= 768;
            
            // Set initial styles with !important
            dropdown.style.setProperty('position', 'fixed', 'important');
            dropdown.style.setProperty('top', '50%', 'important');
            dropdown.style.setProperty('left', '50%', 'important');
            dropdown.style.setProperty('transform', 'translate(-50%, -50%)', 'important');
            dropdown.style.setProperty('background', 'var(--bg-secondary, #1a1a2e)', 'important');
            dropdown.style.setProperty('border', '1px solid var(--border-color, #333)', 'important');
            dropdown.style.setProperty('border-radius', isMobile ? '20px' : '16px', 'important');
            dropdown.style.setProperty('box-shadow', '0 20px 60px rgba(0, 0, 0, 0.5)', 'important');
            dropdown.style.setProperty('z-index', '10000', 'important');
            dropdown.style.setProperty('width', isMobile ? '95%' : '90%', 'important');
            dropdown.style.setProperty('max-width', isMobile ? 'none' : '420px', 'important');
            dropdown.style.setProperty('max-height', isMobile ? '90vh' : '85vh', 'important');
            dropdown.style.setProperty('overflow', 'hidden', 'important');
            dropdown.style.setProperty('display', 'none', 'important');
            dropdown.style.setProperty('opacity', '0', 'important');
            dropdown.style.setProperty('transition', 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)', 'important');
            dropdown.style.setProperty('backdrop-filter', 'blur(20px)', 'important');
            dropdown.style.setProperty('-webkit-backdrop-filter', 'blur(20px)', 'important');
            dropdown.style.setProperty('margin', '0', 'important');
            dropdown.innerHTML = `
                <div class="notification-header">
                    <h3>Notifikasi</h3>
                    <div class="notification-header-actions">
                        <button class="mark-all-read" id="mark-all-read-btn">
                            <i class="bi bi-check-all"></i>
                            <span>Tandai Semua</span>
                        </button>
                        <button class="close-notifications" id="close-notifications-btn">
                            <i class="bi bi-x-lg"></i>
                        </button>
                    </div>
                </div>
                <div class="notification-list" id="notification-list">
                    <div class="no-notifications" style="padding: 3rem 1.5rem; text-align: center; color: var(--text-secondary, #ccc);">
                        <i class="bi bi-bell-slash" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                        <p style="margin: 0; font-size: 1rem;">Tidak ada notifikasi</p>
                        <p style="margin: 0.5rem 0 0 0; font-size: 0.875rem; opacity: 0.7;">Anda akan menerima notifikasi di sini</p>
                    </div>
                </div>
                <div class="notification-footer">
                    <a href="/notifications" class="view-all-notifications">
                        <i class="bi bi-arrow-right"></i>
                        Lihat Semua Notifikasi
                    </a>
                </div>
            `;
            document.body.appendChild(dropdown);
            
            // Add event listeners for buttons
            this.addNotificationButtonListeners();
            
            // Clear any loading state in the newly created dropdown
            this.clearLoadingState();
        }
    }
    
    addNotificationButtonListeners() {
        // Add event listener for close button
        const closeBtn = document.getElementById('close-notifications-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Close button clicked');
                this.closeNotifications();
            });
        }
        
        // Add event listener for mark all read button
        const markAllBtn = document.getElementById('mark-all-read-btn');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Mark all read button clicked');
                this.markAllAsRead();
            });
        }
    }

    createNotificationElements() {
        console.log('Creating notification elements...');
        
        // Create overlay if it doesn't exist
        if (!document.getElementById('notification-overlay')) {
            const overlay = document.createElement('div');
            overlay.className = 'notification-overlay';
            overlay.id = 'notification-overlay';
            document.body.appendChild(overlay);
            
            overlay.addEventListener('click', (e) => {
                console.log('Overlay clicked, closing notifications');
                this.closeNotifications();
            });
        }
        
        // Create dropdown if it doesn't exist
        if (!document.getElementById('notification-dropdown')) {
            const dropdown = document.createElement('div');
            dropdown.className = 'notification-dropdown';
            dropdown.id = 'notification-dropdown';
            dropdown.innerHTML = `
                <div class="notification-header">
                    <h3>Notifikasi</h3>
                    <div class="notification-header-actions">
                        <button class="mark-all-read" onclick="notificationSystem.markAllAsRead()">
                            <i class="bi bi-check-all"></i> Tandai Semua Dibaca
                        </button>
                        <button class="close-notifications" onclick="notificationSystem.closeNotifications()">
                            <i class="bi bi-x-lg"></i>
                        </button>
                    </div>
                </div>
                <div class="notification-list" id="notification-list">
                    <div class="no-notifications" style="padding: 3rem 1.5rem; text-align: center; color: var(--text-secondary, #ccc);">
                        <i class="bi bi-bell-slash" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                        <p style="margin: 0; font-size: 1rem;">Tidak ada notifikasi</p>
                        <p style="margin: 0.5rem 0 0 0; font-size: 0.875rem; opacity: 0.7;">Anda akan menerima notifikasi di sini</p>
                    </div>
                </div>
                <div class="notification-footer">
                    <a href="/notifications" class="view-all-notifications">
                        Lihat Semua Notifikasi
                    </a>
                </div>
            `;
            document.body.appendChild(dropdown);
            
            // Add swipe gesture for mobile
            this.addSwipeGesture();
            
            // Clear any loading state in the newly created dropdown
            this.clearLoadingState();
        }
    }

    openNotifications() {
        console.log('🔔 Opening notifications...');
        
        // Clear any existing loading state first
        this.clearLoadingState();
        
        const dropdown = document.getElementById('notification-dropdown');
        const overlay = document.getElementById('notification-overlay');
        
        console.log('🔔 Dropdown element:', dropdown);
        console.log('🔔 Overlay element:', overlay);
        
        if (dropdown && overlay) {
            // Check if mobile for responsive adjustments
            const isMobile = window.innerWidth <= 768;
            console.log('Is mobile:', isMobile, 'Window width:', window.innerWidth);
            
            // Force positioning with !important
            dropdown.style.setProperty('position', 'fixed', 'important');
            dropdown.style.setProperty('top', '50%', 'important');
            dropdown.style.setProperty('left', '50%', 'important');
            dropdown.style.setProperty('transform', 'translate(-50%, -50%) scale(0.8)', 'important');
            dropdown.style.setProperty('z-index', '10000', 'important');
            dropdown.style.setProperty('width', isMobile ? '95%' : '90%', 'important');
            dropdown.style.setProperty('max-width', isMobile ? 'none' : '420px', 'important');
            dropdown.style.setProperty('margin', '0', 'important');
            dropdown.style.setProperty('visibility', 'visible', 'important');
            
            console.log('Dropdown positioning set:', {
                position: dropdown.style.position,
                top: dropdown.style.top,
                left: dropdown.style.left,
                transform: dropdown.style.transform,
                width: dropdown.style.width,
                maxWidth: dropdown.style.maxWidth,
                visibility: dropdown.style.visibility
            });
            
            // Show overlay first
            overlay.style.setProperty('display', 'block', 'important');
            overlay.style.setProperty('opacity', '0', 'important');
            overlay.style.setProperty('visibility', 'visible', 'important');
            
            // Show dropdown
            dropdown.style.setProperty('display', 'block', 'important');
            dropdown.style.setProperty('opacity', '0', 'important');
            dropdown.style.setProperty('visibility', 'visible', 'important');
            
            // Force reflow
            dropdown.offsetHeight;
            
            // Animate in with proper positioning
            requestAnimationFrame(() => {
                overlay.style.setProperty('opacity', '1', 'important');
                dropdown.style.setProperty('opacity', '1', 'important');
                dropdown.style.setProperty('transform', 'translate(-50%, -50%) scale(1)', 'important');
                dropdown.style.setProperty('visibility', 'visible', 'important');
                
                console.log('Animation complete, final position:', {
                    position: dropdown.style.position,
                    top: dropdown.style.top,
                    left: dropdown.style.left,
                    transform: dropdown.style.transform,
                    width: dropdown.style.width,
                    visibility: dropdown.style.visibility
                });
            });
            
            this.isOpen = true;
            console.log('Notifications opened successfully');
            
            // Add button event listeners
            this.addNotificationButtonListeners();
            
            // Load notifications if not already loaded
            if (this.notifications.length === 0) {
                console.log('📥 No notifications loaded, fetching...');
                this.loadNotifications();
            } else {
                // If notifications already loaded, clear loading state and render them immediately
                console.log('📤 Notifications already loaded, clearing loading state and rendering...');
                this.clearLoadingState();
                this.renderNotifications();
            }
        } else {
            console.error('Failed to open notifications - elements not found');
            console.log('Dropdown exists:', !!dropdown);
            console.log('Overlay exists:', !!overlay);
        }
    }

    closeNotifications() {
        console.log('Closing notifications...');
        const dropdown = document.getElementById('notification-dropdown');
        const overlay = document.getElementById('notification-overlay');
        
        if (dropdown && overlay) {
            // Animate out
            overlay.style.setProperty('opacity', '0', 'important');
            dropdown.style.setProperty('opacity', '0', 'important');
            dropdown.style.setProperty('transform', 'translate(-50%, -50%) scale(0.8)', 'important');
            
            // Hide after animation
            setTimeout(() => {
                overlay.style.setProperty('display', 'none', 'important');
                overlay.style.setProperty('visibility', 'hidden', 'important');
                dropdown.style.setProperty('display', 'none', 'important');
                dropdown.style.setProperty('visibility', 'hidden', 'important');
            }, 300);
            
            this.isOpen = false;
            console.log('Notifications closed successfully');
        } else {
            console.error('Failed to close notifications - elements not found');
        }
    }

    startPolling() {
        // Poll for new notifications every 30 seconds
        setInterval(() => {
            this.loadUnreadCount();
        }, 30000);
    }

    addSwipeGesture() {
        const dropdown = document.getElementById('notification-dropdown');
        if (!dropdown) return;

        let startY = 0;
        let currentY = 0;

        dropdown.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
        });

        dropdown.addEventListener('touchmove', (e) => {
            currentY = e.touches[0].clientY;
            const diff = currentY - startY;
            
            if (diff > 50) { // Swipe down
                dropdown.style.transform = `translateY(${diff}px)`;
            }
        });

        dropdown.addEventListener('touchend', (e) => {
            const diff = currentY - startY;
            
            if (diff > 100) { // Swipe down enough to close
                this.closeNotifications();
            } else {
                dropdown.style.transform = 'translateY(0)';
            }
        });
    }



    // Show toast notification
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `notification-toast ${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="bi bi-${this.getToastIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <i class="bi bi-x"></i>
            </button>
        `;

        // Add to page
        if (!document.getElementById('toast-container')) {
            const container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }
        
        document.getElementById('toast-container').appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }

    getToastIcon(type) {
        switch (type) {
            case 'success':
                return 'check-circle';
            case 'error':
                return 'exclamation-circle';
            case 'warning':
                return 'exclamation-triangle';
            default:
                return 'info-circle';
        }
    }
}

// Initialize notification system when DOM is loaded
let notificationSystem;

function initNotificationSystem() {
    console.log('Initializing notification system...');
    if (typeof notificationSystem === 'undefined') {
        notificationSystem = new NotificationSystem();
        // Make sure it's available globally
        window.notificationSystem = notificationSystem;
    }
}

// Update the global function with better error handling
window.toggleMobileNotifications = function() {
    console.log('🔔 Global mobile notification toggle called (updated)');
    console.log('🔔 Window notification system exists:', !!window.notificationSystem);
    
    if (window.notificationSystem) {
        console.log('🔔 Calling toggleNotifications()');
        window.notificationSystem.toggleNotifications();
    } else {
        console.log('🔔 Notification system not ready, initializing...');
        // Try to initialize it
        if (typeof NotificationSystem !== 'undefined') {
            try {
                window.notificationSystem = new NotificationSystem();
                notificationSystem = window.notificationSystem;
                // Wait a bit for initialization to complete
                setTimeout(() => {
                    if (window.notificationSystem) {
                        console.log('🔔 Notification system initialized, toggling...');
                        window.notificationSystem.toggleNotifications();
                    }
                }, 200);
            } catch (error) {
                console.error('❌ Error initializing notification system:', error);
            }
        } else {
            console.error('❌ NotificationSystem class not available');
        }
    }
};

// Try multiple ways to initialize
document.addEventListener('DOMContentLoaded', initNotificationSystem);

// Also try when window loads
window.addEventListener('load', initNotificationSystem);

// Fallback: try after a short delay
setTimeout(initNotificationSystem, 1000);
