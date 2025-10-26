/**
 * Contoh Penggunaan API Video Feed dengan Lazy Loading
 * 
 * API Endpoints yang tersedia:
 * 1. GET /api/feed/videos - Pagination tradisional
 * 2. GET /api/feed/videos/cursor - Cursor-based pagination (direkomendasikan)
 * 3. GET /api/feed/video/{id} - Detail video individual
 * 4. POST /api/feed/video/{id}/like - Like/unlike video
 * 5. POST /api/feed/video/{id}/comment - Tambah komentar
 * 6. GET /api/feed/video/{id}/comments - Ambil komentar video
 */

class VideoAPI {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    /**
     * Mengambil video feed dengan pagination tradisional
     * @param {number} page - Halaman yang diminta (default: 1)
     * @param {number} perPage - Jumlah video per halaman (default: 10, max: 20)
     * @returns {Promise<Object>} Response dari API
     */
    async getVideosFeed(page = 1, perPage = 10) {
        try {
            const response = await fetch(`${this.baseUrl}/api/feed/videos?page=${page}&per_page=${perPage}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Gagal memuat video');
            }
            
            return data;
        } catch (error) {
            console.error('Error fetching videos feed:', error);
            throw error;
        }
    }

    /**
     * Mengambil video feed dengan cursor-based pagination (lebih efisien)
     * @param {string} cursor - Cursor untuk pagination (optional)
     * @param {number} limit - Jumlah video yang diminta (default: 10, max: 20)
     * @returns {Promise<Object>} Response dari API
     */
    async getVideosFeedCursor(cursor = null, limit = 10) {
        try {
            let url = `${this.baseUrl}/api/feed/videos/cursor?limit=${limit}`;
            if (cursor) {
                url += `&cursor=${encodeURIComponent(cursor)}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Gagal memuat video');
            }
            
            return data;
        } catch (error) {
            console.error('Error fetching videos feed with cursor:', error);
            throw error;
        }
    }

    /**
     * Mengambil detail video individual
     * @param {number} videoId - ID video
     * @returns {Promise<Object>} Detail video
     */
    async getVideoDetail(videoId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/feed/video/${videoId}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Video tidak ditemukan');
            }
            
            return data;
        } catch (error) {
            console.error('Error fetching video detail:', error);
            throw error;
        }
    }

    /**
     * Like atau unlike video
     * @param {number} videoId - ID video
     * @returns {Promise<Object>} Status like dan jumlah like
     */
    async toggleLike(videoId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/feed/video/${videoId}/like`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Gagal mengubah status like');
            }
            
            return data;
        } catch (error) {
            console.error('Error toggling like:', error);
            throw error;
        }
    }

    /**
     * Menambahkan komentar ke video
     * @param {number} videoId - ID video
     * @param {string} comment - Teks komentar
     * @returns {Promise<Object>} Response komentar
     */
    async addComment(videoId, comment) {
        try {
            const response = await fetch(`${this.baseUrl}/api/feed/video/${videoId}/comment`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ comment })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Gagal menambahkan komentar');
            }
            
            return data;
        } catch (error) {
            console.error('Error adding comment:', error);
            throw error;
        }
    }

    /**
     * Mengambil komentar video
     * @param {number} videoId - ID video
     * @param {number} page - Halaman komentar (default: 1)
     * @param {number} perPage - Jumlah komentar per halaman (default: 10)
     * @returns {Promise<Object>} Daftar komentar
     */
    async getVideoComments(videoId, page = 1, perPage = 10) {
        try {
            const response = await fetch(`${this.baseUrl}/api/feed/video/${videoId}/comments?page=${page}&per_page=${perPage}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Gagal memuat komentar');
            }
            
            return data;
        } catch (error) {
            console.error('Error fetching comments:', error);
            throw error;
        }
    }

    /**
     * Share video
     * @param {number} videoId - ID video
     * @returns {Promise<Object>} Response share
     */
    async shareVideo(videoId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/feed/video/${videoId}/share`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Gagal share video');
            }
            
            return data;
        } catch (error) {
            console.error('Error sharing video:', error);
            throw error;
        }
    }
}

// Contoh penggunaan API
class VideoFeedManager {
    constructor() {
        this.api = new VideoAPI();
        this.videos = [];
        this.nextCursor = null;
        this.hasMore = true;
        this.isLoading = false;
    }

    /**
     * Memuat video pertama kali
     */
    async loadInitialVideos() {
        try {
            this.isLoading = true;
            const response = await this.api.getVideosFeedCursor();
            
            this.videos = response.data;
            this.nextCursor = response.pagination.next_cursor;
            this.hasMore = response.pagination.has_more;
            
            return response;
        } catch (error) {
            console.error('Error loading initial videos:', error);
            throw error;
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Memuat video berikutnya (lazy loading)
     */
    async loadMoreVideos() {
        if (!this.hasMore || this.isLoading) {
            return null;
        }

        try {
            this.isLoading = true;
            const response = await this.api.getVideosFeedCursor(this.nextCursor);
            
            this.videos = [...this.videos, ...response.data];
            this.nextCursor = response.pagination.next_cursor;
            this.hasMore = response.pagination.has_more;
            
            return response;
        } catch (error) {
            console.error('Error loading more videos:', error);
            throw error;
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Mencari video berdasarkan ID
     * @param {number} videoId - ID video
     * @returns {Object|null} Video object atau null jika tidak ditemukan
     */
    findVideoById(videoId) {
        return this.videos.find(video => video.id === videoId) || null;
    }

    /**
     * Update video dalam array setelah interaksi
     * @param {number} videoId - ID video
     * @param {Object} updates - Data yang akan diupdate
     */
    updateVideo(videoId, updates) {
        const videoIndex = this.videos.findIndex(video => video.id === videoId);
        if (videoIndex !== -1) {
            this.videos[videoIndex] = { ...this.videos[videoIndex], ...updates };
        }
    }
}

// Contoh implementasi dengan React (jika menggunakan React)
class ReactVideoFeed extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            videos: [],
            loading: false,
            error: null,
            hasMore: true,
            nextCursor: null
        };
        this.feedManager = new VideoFeedManager();
    }

    async componentDidMount() {
        await this.loadInitialVideos();
    }

    async loadInitialVideos() {
        try {
            this.setState({ loading: true, error: null });
            const response = await this.feedManager.loadInitialVideos();
            
            this.setState({
                videos: response.data,
                hasMore: response.pagination.has_more,
                nextCursor: response.pagination.next_cursor
            });
        } catch (error) {
            this.setState({ error: error.message });
        } finally {
            this.setState({ loading: false });
        }
    }

    async loadMoreVideos() {
        try {
            this.setState({ loading: true });
            const response = await this.feedManager.loadMoreVideos();
            
            if (response) {
                this.setState(prevState => ({
                    videos: [...prevState.videos, ...response.data],
                    hasMore: response.pagination.has_more,
                    nextCursor: response.pagination.next_cursor
                }));
            }
        } catch (error) {
            this.setState({ error: error.message });
        } finally {
            this.setState({ loading: false });
        }
    }

    async handleLike(videoId) {
        try {
            const response = await this.api.toggleLike(videoId);
            
            this.setState(prevState => ({
                videos: prevState.videos.map(video => 
                    video.id === videoId 
                        ? {
                            ...video,
                            interactions: {
                                ...video.interactions,
                                is_liked: response.is_liked
                            },
                            stats: {
                                ...video.stats,
                                likes: response.likes_count
                            }
                        }
                        : video
                )
            }));
        } catch (error) {
            console.error('Error liking video:', error);
        }
    }

    render() {
        const { videos, loading, error, hasMore } = this.state;

        return (
            <div className="video-feed">
                {error && <div className="error">{error}</div>}
                
                {videos.map(video => (
                    <VideoCard 
                        key={video.id} 
                        video={video} 
                        onLike={() => this.handleLike(video.id)}
                    />
                ))}
                
                {loading && <div className="loading">Memuat video...</div>}
                
                {hasMore && !loading && (
                    <button onClick={() => this.loadMoreVideos()}>
                        Muat Lebih Banyak
                    </button>
                )}
            </div>
        );
    }
}

// Contoh penggunaan dengan vanilla JavaScript
async function contohPenggunaanAPI() {
    const api = new VideoAPI();
    
    try {
        // 1. Memuat video feed pertama
        console.log('Memuat video feed...');
        const feedResponse = await api.getVideosFeedCursor();
        console.log('Video feed:', feedResponse);
        
        // 2. Memuat video berikutnya
        if (feedResponse.pagination.has_more) {
            console.log('Memuat video berikutnya...');
            const nextResponse = await api.getVideosFeedCursor(feedResponse.pagination.next_cursor);
            console.log('Video berikutnya:', nextResponse);
        }
        
        // 3. Mengambil detail video pertama
        if (feedResponse.data.length > 0) {
            const firstVideo = feedResponse.data[0];
            console.log('Mengambil detail video:', firstVideo.id);
            const detailResponse = await api.getVideoDetail(firstVideo.id);
            console.log('Detail video:', detailResponse);
            
            // 4. Like video
            console.log('Liking video...');
            const likeResponse = await api.toggleLike(firstVideo.id);
            console.log('Like response:', likeResponse);
            
            // 5. Menambahkan komentar
            console.log('Menambahkan komentar...');
            const commentResponse = await api.addComment(firstVideo.id, 'Video yang bagus! 👍');
            console.log('Comment response:', commentResponse);
            
            // 6. Mengambil komentar
            console.log('Mengambil komentar...');
            const commentsResponse = await api.getVideoComments(firstVideo.id);
            console.log('Comments:', commentsResponse);
        }
        
    } catch (error) {
        console.error('Error dalam contoh penggunaan:', error);
    }
}

// Export untuk penggunaan di modul lain
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { VideoAPI, VideoFeedManager };
}

// Jalankan contoh jika di browser
if (typeof window !== 'undefined') {
    // Uncomment untuk menjalankan contoh
    // contohPenggunaanAPI();
}
