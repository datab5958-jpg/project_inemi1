// Auto view tracking system
document.addEventListener('DOMContentLoaded', function() {
    // Track views when content is visible
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1 // Trigger when 10% of content is visible
    };

    const viewObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                const contentType = element.getAttribute('data-content-type');
                const contentId = element.getAttribute('data-content-id');
                
                if (contentType && contentId) {
                    // Track view only once per session
                    const viewKey = `viewed_${contentType}_${contentId}`;
                    if (!sessionStorage.getItem(viewKey)) {
                        trackView(contentType, contentId);
                        sessionStorage.setItem(viewKey, 'true');
                    }
                }
            }
        });
    }, observerOptions);

    // Observe all content elements
    const contentElements = document.querySelectorAll('[data-content-type][data-content-id]');
    contentElements.forEach(element => {
        viewObserver.observe(element);
    });

    // Track view when user clicks on content
    document.addEventListener('click', function(e) {
        const contentElement = e.target.closest('[data-content-type][data-content-id]');
        if (contentElement) {
            const contentType = contentElement.getAttribute('data-content-type');
            const contentId = contentElement.getAttribute('data-content-id');
            
            if (contentType && contentId) {
                trackView(contentType, contentId);
            }
        }
    });

    // Track view when video is played
    const videos = document.querySelectorAll('video');
    videos.forEach(video => {
        video.addEventListener('play', function() {
            const contentElement = this.closest('[data-content-type][data-content-id]');
            if (contentElement) {
                const contentType = contentElement.getAttribute('data-content-type');
                const contentId = contentElement.getAttribute('data-content-id');
                
                if (contentType && contentId) {
                    trackView(contentType, contentId);
                }
            }
        });
    });

    // Track view when audio is played
    const audios = document.querySelectorAll('audio');
    audios.forEach(audio => {
        audio.addEventListener('play', function() {
            const contentElement = this.closest('[data-content-type][data-content-id]');
            if (contentElement) {
                const contentType = contentElement.getAttribute('data-content-type');
                const contentId = contentElement.getAttribute('data-content-id');
                
                if (contentType && contentId) {
                    trackView(contentType, contentId);
                }
            }
        });
    });
});

function trackView(contentType, contentId) {
    // Prevent duplicate tracking in the same session
    const viewKey = `viewed_${contentType}_${contentId}`;
    if (sessionStorage.getItem(viewKey)) {
        return;
    }

    // Send view tracking request
    fetch('/admin/api/content/view', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            content_type: contentType,
            content_id: contentId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(`View tracked for ${contentType} ${contentId}`);
            sessionStorage.setItem(viewKey, 'true');
            
            // Update view count in UI if element exists
            const viewCountElement = document.querySelector(`[data-content-type="${contentType}"][data-content-id="${contentId}"] .view-count`);
            if (viewCountElement) {
                viewCountElement.textContent = data.view_count;
            }
        } else {
            console.error('Failed to track view:', data.error);
        }
    })
    .catch(error => {
        console.error('Error tracking view:', error);
    });
}

// Track views on page load for visible content
window.addEventListener('load', function() {
    setTimeout(() => {
        const visibleContent = document.querySelectorAll('[data-content-type][data-content-id]');
        visibleContent.forEach(element => {
            const rect = element.getBoundingClientRect();
            const isVisible = rect.top < window.innerHeight && rect.bottom > 0;
            
            if (isVisible) {
                const contentType = element.getAttribute('data-content-type');
                const contentId = element.getAttribute('data-content-id');
                
                if (contentType && contentId) {
                    trackView(contentType, contentId);
                }
            }
        });
    }, 1000); // Wait 1 second after page load
});







