# Dokumentasi API Video Feed dengan Lazy Loading

## Overview
API ini menyediakan endpoint untuk mengambil video feed dengan lazy loading yang efisien, termasuk informasi user, caption, dan interaksi seperti like, comment, dan share.

## Base URL
```
http://localhost:5000
```

## Authentication
Beberapa endpoint memerlukan session user. Pastikan user sudah login sebelum mengakses endpoint yang memerlukan authentication.

## Endpoints

### 1. Video Feed dengan Pagination Tradisional
**GET** `/api/feed/videos`

Mengambil daftar video dengan pagination tradisional.

#### Parameters
- `page` (optional): Nomor halaman (default: 1)
- `per_page` (optional): Jumlah video per halaman (default: 10, max: 20)

#### Response
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "Video by username",
      "caption": "Caption video...",
      "video_url": "/static/videos/video1.mp4",
      "thumbnail_url": "/static/thumbnails/thumb1.jpg",
      "user": {
        "id": 1,
        "username": "username",
        "avatar_url": "/static/avatars/avatar1.jpg",
        "is_verified": false
      },
      "stats": {
        "likes": 150,
        "comments": 25,
        "views": 1000,
        "shares": 10
      },
      "interactions": {
        "is_liked": false,
        "is_bookmarked": false
      },
      "created_at": "2024-01-15T10:30:00",
      "duration": "00:02:30"
    }
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 10,
    "total_videos": 100,
    "total_pages": 10,
    "has_more": true,
    "has_previous": false,
    "next_cursor": "2024-01-15T10:30:00"
  },
  "meta": {
    "timestamp": "2024-01-15T12:00:00",
    "user_id": 1
  }
}
```

### 2. Video Feed dengan Cursor-based Pagination (Direkomendasikan)
**GET** `/api/feed/videos/cursor`

Mengambil daftar video dengan cursor-based pagination yang lebih efisien untuk lazy loading.

#### Parameters
- `cursor` (optional): ISO timestamp string untuk pagination
- `limit` (optional): Jumlah video yang diminta (default: 10, max: 20)

#### Response
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "Video by username",
      "caption": "Caption video...",
      "video_url": "/static/videos/video1.mp4",
      "thumbnail_url": "/static/thumbnails/thumb1.jpg",
      "user": {
        "id": 1,
        "username": "username",
        "avatar_url": "/static/avatars/avatar1.jpg",
        "is_verified": false
      },
      "stats": {
        "likes": 150,
        "comments": 25,
        "views": 1000,
        "shares": 10
      },
      "interactions": {
        "is_liked": false,
        "is_bookmarked": false
      },
      "created_at": "2024-01-15T10:30:00",
      "duration": "00:02:30"
    }
  ],
  "pagination": {
    "has_more": true,
    "next_cursor": "2024-01-15T10:30:00",
    "limit": 10
  },
  "meta": {
    "timestamp": "2024-01-15T12:00:00",
    "user_id": 1,
    "count": 10
  }
}
```

### 3. Detail Video Individual
**GET** `/api/feed/video/{video_id}`

Mengambil detail lengkap video individual termasuk komentar terbaru.

#### Parameters
- `video_id`: ID video (path parameter)

#### Response
```json
{
  "success": true,
  "data": {
    "id": 1,
    "title": "Video by username",
    "caption": "Caption video...",
    "video_url": "/static/videos/video1.mp4",
    "thumbnail_url": "/static/thumbnails/thumb1.jpg",
    "user": {
      "id": 1,
      "username": "username",
      "avatar_url": "/static/avatars/avatar1.jpg",
      "is_verified": false,
      "followers_count": 500,
      "is_following": false
    },
    "stats": {
      "likes": 150,
      "comments": 25,
      "views": 1000,
      "shares": 10
    },
    "interactions": {
      "is_liked": false,
      "is_bookmarked": false
    },
    "created_at": "2024-01-15T10:30:00",
    "duration": "00:02:30",
    "recent_comments": [
      {
        "id": 1,
        "comment": "Video yang bagus!",
        "user": {
          "id": 2,
          "username": "commenter",
          "avatar_url": "/static/avatars/avatar2.jpg"
        },
        "created_at": "2024-01-15T11:00:00"
      }
    ]
  }
}
```

### 4. Like/Unlike Video
**POST** `/api/feed/video/{video_id}/like`

Mengubah status like video. Memerlukan authentication.

#### Parameters
- `video_id`: ID video (path parameter)

#### Response
```json
{
  "success": true,
  "is_liked": true,
  "likes_count": 151
}
```

### 5. Menambahkan Komentar
**POST** `/api/feed/video/{video_id}/comment`

Menambahkan komentar ke video. Memerlukan authentication.

#### Request Body
```json
{
  "comment": "Komentar yang ingin ditambahkan"
}
```

#### Response
```json
{
  "success": true,
  "comments_count": 26,
  "comment": {
    "id": 2,
    "comment": "Komentar yang ingin ditambahkan",
    "user_id": 1,
    "created_at": "2024-01-15T12:00:00"
  }
}
```

### 6. Mengambil Komentar Video
**GET** `/api/feed/video/{video_id}/comments`

Mengambil daftar komentar video dengan pagination.

#### Parameters
- `page` (optional): Nomor halaman (default: 1)
- `per_page` (optional): Jumlah komentar per halaman (default: 10)

#### Response
```json
{
  "success": true,
  "comments": [
    {
      "id": 1,
      "comment": "Video yang bagus!",
      "user": {
        "id": 2,
        "username": "commenter",
        "avatar_url": "/static/avatars/avatar2.jpg"
      },
      "created_at": "2024-01-15T11:00:00"
    }
  ],
  "has_more": false,
  "page": 1,
  "per_page": 10,
  "total": 1
}
```

### 7. Share Video
**POST** `/api/feed/video/{video_id}/share`

Mencatat share video.

#### Parameters
- `video_id`: ID video (path parameter)

#### Response
```json
{
  "success": true,
  "message": "Video shared successfully",
  "shares_count": 11
}
```

## Error Responses

Semua endpoint mengembalikan error dalam format yang konsisten:

```json
{
  "success": false,
  "error": "Error message",
  "data": [],
  "pagination": {
    "has_more": false,
    "next_cursor": null
  }
}
```

### Status Codes
- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `500`: Internal Server Error

## Contoh Penggunaan

### JavaScript (Vanilla)
```javascript
// Menggunakan cursor-based pagination
async function loadVideos() {
    const response = await fetch('/api/feed/videos/cursor?limit=10');
    const data = await response.json();
    
    if (data.success) {
        console.log('Videos:', data.data);
        console.log('Next cursor:', data.pagination.next_cursor);
        console.log('Has more:', data.pagination.has_more);
    }
}

// Memuat video berikutnya
async function loadMoreVideos(cursor) {
    const response = await fetch(`/api/feed/videos/cursor?cursor=${cursor}&limit=10`);
    const data = await response.json();
    
    return data;
}

// Like video
async function likeVideo(videoId) {
    const response = await fetch(`/api/feed/video/${videoId}/like`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    });
    
    const data = await response.json();
    return data;
}
```

### React Hook
```javascript
import { useState, useEffect, useCallback } from 'react';

function useVideoFeed() {
    const [videos, setVideos] = useState([]);
    const [loading, setLoading] = useState(false);
    const [hasMore, setHasMore] = useState(true);
    const [nextCursor, setNextCursor] = useState(null);

    const loadVideos = useCallback(async (cursor = null) => {
        if (loading) return;
        
        setLoading(true);
        try {
            const url = cursor 
                ? `/api/feed/videos/cursor?cursor=${cursor}&limit=10`
                : '/api/feed/videos/cursor?limit=10';
                
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success) {
                setVideos(prev => cursor ? [...prev, ...data.data] : data.data);
                setNextCursor(data.pagination.next_cursor);
                setHasMore(data.pagination.has_more);
            }
        } catch (error) {
            console.error('Error loading videos:', error);
        } finally {
            setLoading(false);
        }
    }, [loading]);

    const loadMore = useCallback(() => {
        if (hasMore && nextCursor) {
            loadVideos(nextCursor);
        }
    }, [hasMore, nextCursor, loadVideos]);

    useEffect(() => {
        loadVideos();
    }, []);

    return { videos, loading, hasMore, loadMore };
}
```

## Best Practices

### 1. Lazy Loading
- Gunakan cursor-based pagination (`/api/feed/videos/cursor`) untuk performa yang lebih baik
- Implementasikan Intersection Observer untuk auto-loading
- Batasi jumlah video yang dimuat sekaligus (max 20)

### 2. Error Handling
- Selalu cek `success` field dalam response
- Implementasikan retry mechanism untuk network errors
- Tampilkan pesan error yang user-friendly

### 3. Performance
- Cache video data di client-side
- Preload thumbnail untuk video berikutnya
- Gunakan debouncing untuk search functionality

### 4. User Experience
- Tampilkan loading state saat memuat video
- Implementasikan pull-to-refresh
- Berikan feedback visual untuk interaksi (like, comment)

## Rate Limiting
API ini memiliki rate limiting untuk mencegah abuse:
- 100 requests per menit per IP
- 1000 requests per jam per user (jika authenticated)

## Caching
Response API di-cache selama 5 menit untuk meningkatkan performa. Data real-time seperti like count mungkin tidak selalu up-to-date.
