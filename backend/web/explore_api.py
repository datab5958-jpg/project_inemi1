from flask import Blueprint, request, jsonify, session
from models import db, Image, Video, Song, User, Like, Comment, Follow
import random
import os
from datetime import datetime

explore_api = Blueprint('explore_api', __name__)

@explore_api.route('/api/explore/load-more', methods=['POST'])
def api_explore_load_more():
    """API endpoint for infinite scroll in explore page"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        content_type = data.get('content_type', 'all')
        page = data.get('page', 1)
        per_page = 12
        
        offset = (page - 1) * per_page
        current_user_id = session.get('user_id')
        
        # Get content based on type, exclude current user's content
        if content_type == 'new_images':
            if current_user_id:
                content = db.session.query(Image).filter(Image.user_id != current_user_id).order_by(Image.created_at.desc()).offset(offset).limit(per_page).all()
            else:
                content = db.session.query(Image).order_by(Image.created_at.desc()).offset(offset).limit(per_page).all()
        elif content_type == 'new_videos':
            if current_user_id:
                content = db.session.query(Video).filter(Video.user_id != current_user_id).order_by(Video.created_at.desc()).offset(offset).limit(per_page).all()
            else:
                content = db.session.query(Video).order_by(Video.created_at.desc()).offset(offset).limit(per_page).all()
        elif content_type == 'new_songs':
            if current_user_id:
                content = db.session.query(Song).filter(Song.user_id != current_user_id).order_by(Song.created_at.desc()).offset(offset).limit(per_page).all()
            else:
                content = db.session.query(Song).order_by(Song.created_at.desc()).offset(offset).limit(per_page).all()
        elif content_type == 'images':
            if current_user_id:
                content = db.session.query(Image).filter(Image.user_id != current_user_id).order_by(Image.view_count.desc()).offset(offset).limit(per_page).all()
            else:
                content = db.session.query(Image).order_by(Image.view_count.desc()).offset(offset).limit(per_page).all()
        elif content_type == 'videos':
            if current_user_id:
                content = db.session.query(Video).filter(Video.user_id != current_user_id).order_by(Video.view_count.desc()).offset(offset).limit(per_page).all()
            else:
                content = db.session.query(Video).order_by(Video.view_count.desc()).offset(offset).limit(per_page).all()
        elif content_type == 'songs':
            if current_user_id:
                content = db.session.query(Song).filter(Song.user_id != current_user_id).order_by(Song.view_count.desc()).offset(offset).limit(per_page).all()
            else:
                content = db.session.query(Song).order_by(Song.view_count.desc()).offset(offset).limit(per_page).all()
        else:  # all
            # Combine all content types (new + trending)
            if current_user_id:
                new_images = db.session.query(Image).filter(Image.user_id != current_user_id).order_by(Image.created_at.desc()).offset(offset).limit(per_page//6).all()
                new_videos = db.session.query(Video).filter(Video.user_id != current_user_id).order_by(Video.created_at.desc()).offset(offset).limit(per_page//6).all()
                new_songs = db.session.query(Song).filter(Song.user_id != current_user_id).order_by(Song.created_at.desc()).offset(offset).limit(per_page//6).all()
                trending_images = db.session.query(Image).filter(Image.user_id != current_user_id).order_by(Image.view_count.desc()).offset(offset).limit(per_page//6).all()
                trending_videos = db.session.query(Video).filter(Video.user_id != current_user_id).order_by(Video.view_count.desc()).offset(offset).limit(per_page//6).all()
                trending_songs = db.session.query(Song).filter(Song.user_id != current_user_id).order_by(Song.view_count.desc()).offset(offset).limit(per_page//6).all()
            else:
                new_images = db.session.query(Image).order_by(Image.created_at.desc()).offset(offset).limit(per_page//6).all()
                new_videos = db.session.query(Video).order_by(Video.created_at.desc()).offset(offset).limit(per_page//6).all()
                new_songs = db.session.query(Song).order_by(Song.created_at.desc()).offset(offset).limit(per_page//6).all()
                trending_images = db.session.query(Image).order_by(Image.view_count.desc()).offset(offset).limit(per_page//6).all()
                trending_videos = db.session.query(Video).order_by(Video.view_count.desc()).offset(offset).limit(per_page//6).all()
                trending_songs = db.session.query(Song).order_by(Song.view_count.desc()).offset(offset).limit(per_page//6).all()
            content = list(new_images) + list(new_videos) + list(new_songs) + list(trending_images) + list(trending_videos) + list(trending_songs)
        
        # Add user info and counts for each content
        content_data = []
        for item in content:
            try:
                user = db.session.query(User).filter_by(id=item.user_id).first()
                likes_count = db.session.query(Like).filter_by(content_type=item.__class__.__name__.lower(), content_id=str(item.id)).count()
                comments_count = db.session.query(Comment).filter_by(content_type=item.__class__.__name__.lower(), content_id=str(item.id)).count()
                
                # Check if current user is following this content's user
                is_following = False
                if current_user_id and user:
                    existing_follow = db.session.query(Follow).filter_by(
                        follower_id=current_user_id,
                        following_id=user.id
                    ).first()
                    is_following = existing_follow is not None
                
                content_data.append({
                    'id': item.id,
                    'type': item.__class__.__name__.lower(),
                    'user': {
                        'id': user.id if user else None,
                        'username': user.username if user else 'Unknown',
                        'avatar_url': user.avatar_url if user else '/static/assets/image/default.jpg'
                    },
                    'likes_count': likes_count,
                    'comments_count': comments_count,
                    'view_count': item.view_count or 0,
                    'image_url': getattr(item, 'image_url', None),
                    'video_url': getattr(item, 'video_url', None),
                    'thumbnail_url': getattr(item, 'thumbnail_url', None),
                    'caption': getattr(item, 'caption', ''),
                    'title': getattr(item, 'title', ''),
                    'is_following': is_following
                })
            except Exception as e:
                print(f"Error processing content {item.id}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'content': content_data,
            'has_more': len(content_data) == per_page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@explore_api.route('/api/feed/videos', methods=['GET'])
def api_feed_videos():
    """API endpoint untuk mengambil video dengan caption dan user yang membuatnya dengan lazy loading"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 20)  # Max 20 per page
        cursor = request.args.get('cursor', None)  # For cursor-based pagination
        current_user_id = session.get('user_id')
        
        # Validate parameters
        if page < 1:
            page = 1
        
        # Calculate offset for traditional pagination
        offset = (page - 1) * per_page
        
        # Build base query
        base_query = db.session.query(Video, User).join(
            User, Video.user_id == User.id
        ).filter(
            Video.video_url.isnot(None),
            Video.video_url != ''
        )
        
        # Exclude current user's videos if logged in
        if current_user_id:
            base_query = base_query.filter(Video.user_id != current_user_id)
        
        # Apply cursor-based pagination if cursor is provided
        if cursor:
            try:
                cursor_timestamp = cursor
                base_query = base_query.filter(Video.created_at < cursor_timestamp)
            except:
                pass  # If cursor is invalid, ignore it
        
        # Order by creation date (newest first)
        base_query = base_query.order_by(Video.created_at.desc())
        
        # Get total count for pagination info
        total_videos = base_query.count()
        
        # Get paginated results
        results = base_query.offset(offset).limit(per_page).all()
        
        # Process videos
        videos_data = []
        next_cursor = None
        
        for video, user in results:
            try:
                # Get interaction counts
                likes_count = db.session.query(Like).filter_by(
                    content_type='video',
                    content_id=str(video.id)
                ).count()
                
                comments_count = db.session.query(Comment).filter_by(
                    content_type='video',
                    content_id=str(video.id)
                ).count()
                
                # Check if current user liked this video
                is_liked = False
                if current_user_id:
                    existing_like = db.session.query(Like).filter_by(
                        user_id=current_user_id,
                        content_type='video',
                        content_id=str(video.id)
                    ).first()
                    is_liked = existing_like is not None
                
                # Process URLs
                video_url = video.video_url
                if video_url and not video_url.startswith('http'):
                    video_url = f"/static/{video_url}"
                
                # Generate thumbnail URL from video URL or use default
                thumbnail_url = getattr(video, 'thumbnail_url', None)
                if not thumbnail_url:
                    # Generate thumbnail from video URL or use default
                    if video_url and 'sample-videos.com' in video_url:
                        thumbnail_url = '/static/assets/image/default.jpg'
                    else:
                        thumbnail_url = '/static/assets/image/default.jpg'
                
                if thumbnail_url and not thumbnail_url.startswith('http'):
                    thumbnail_url = f"/static/{thumbnail_url}"
                
                user_avatar = user.avatar_url
                if user_avatar and not user_avatar.startswith('http'):
                    user_avatar = f"/static/{user_avatar}"
                
                video_data = {
                    'id': video.id,
                    'title': getattr(video, 'title', None) or f"Video by {user.username}",
                    'caption': video.caption or "",
                    'video_url': video_url,
                    'thumbnail_url': thumbnail_url or '/static/assets/image/default.jpg',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'avatar_url': user_avatar or '/static/assets/image/default.jpg',
                        'is_verified': getattr(user, 'is_verified', False)
                    },
                    'stats': {
                        'likes': likes_count,
                        'comments': comments_count,
                        'views': video.view_count or 0,
                        'shares': random.randint(5, 50)  # Mock share count
                    },
                    'interactions': {
                        'is_liked': is_liked,
                        'is_bookmarked': False  # You can implement bookmark functionality later
                    },
                    'created_at': video.created_at.isoformat() if video.created_at else None,
                    'duration': getattr(video, 'duration', None)  # If you have duration field
                }
                
                videos_data.append(video_data)
                
                # Set next cursor to the last video's timestamp
                if video.created_at:
                    next_cursor = video.created_at.isoformat()
                    
            except Exception as e:
                print(f"Error processing video {video.id}: {e}")
                continue
        
        # Calculate pagination info
        has_more = len(results) == per_page
        total_pages = (total_videos + per_page - 1) // per_page
        
        return jsonify({
            'success': True,
            'data': videos_data,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_videos': total_videos,
                'total_pages': total_pages,
                'has_more': has_more,
                'has_previous': page > 1,
                'next_cursor': next_cursor
            },
            'meta': {
                'timestamp': datetime.now().isoformat(),
                'user_id': current_user_id
            }
        })
        
    except Exception as e:
        print(f"Error in api_feed_videos: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load videos',
            'data': [],
            'pagination': {
                'current_page': 1,
                'per_page': 10,
                'total_videos': 0,
                'total_pages': 0,
                'has_more': False,
                'has_previous': False,
                'next_cursor': None
            }
        }), 500

@explore_api.route('/api/feed/videos/cursor', methods=['GET'])
def api_feed_videos_cursor():
    """API endpoint untuk mengambil video dengan cursor-based pagination (lebih efisien untuk lazy loading)"""
    try:
        # Get query parameters
        cursor = request.args.get('cursor', None)  # ISO timestamp string
        limit = min(request.args.get('limit', 10, type=int), 20)  # Max 20 per request
        current_user_id = session.get('user_id')
        
        # Build base query with join for better performance
        base_query = db.session.query(Video, User).join(
            User, Video.user_id == User.id
        ).filter(
            Video.video_url.isnot(None),
            Video.video_url != ''
        )
        
        # Exclude current user's videos if logged in
        if current_user_id:
            base_query = base_query.filter(Video.user_id != current_user_id)
        
        # Apply cursor-based pagination
        if cursor:
            try:
                cursor_datetime = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
                base_query = base_query.filter(Video.created_at < cursor_datetime)
            except ValueError:
                # If cursor is invalid, ignore it and start from beginning
                pass
        
        # Order by creation date (newest first)
        base_query = base_query.order_by(Video.created_at.desc())
        
        # Get results
        results = base_query.limit(limit + 1).all()  # Get one extra to check if there are more
        
        # Check if there are more results
        has_more = len(results) > limit
        if has_more:
            results = results[:limit]  # Remove the extra result
        
        # Process videos
        videos_data = []
        next_cursor = None
        
        for video, user in results:
            try:
                # Get interaction counts in batch (more efficient)
                likes_count = db.session.query(Like).filter_by(
                    content_type='video',
                    content_id=str(video.id)
                ).count()
                
                comments_count = db.session.query(Comment).filter_by(
                    content_type='video',
                    content_id=str(video.id)
                ).count()
                
                # Check if current user liked this video
                is_liked = False
                if current_user_id:
                    existing_like = db.session.query(Like).filter_by(
                        user_id=current_user_id,
                        content_type='video',
                        content_id=str(video.id)
                    ).first()
                    is_liked = existing_like is not None
                
                # Process URLs
                video_url = video.video_url
                if video_url and not video_url.startswith('http'):
                    video_url = f"/static/{video_url}"
                
                # Generate thumbnail URL from video URL or use default
                thumbnail_url = getattr(video, 'thumbnail_url', None)
                if not thumbnail_url:
                    # Generate thumbnail from video URL or use default
                    if video_url and 'sample-videos.com' in video_url:
                        thumbnail_url = '/static/assets/image/default.jpg'
                    else:
                        thumbnail_url = '/static/assets/image/default.jpg'
                
                if thumbnail_url and not thumbnail_url.startswith('http'):
                    thumbnail_url = f"/static/{thumbnail_url}"
                
                user_avatar = user.avatar_url
                if user_avatar and not user_avatar.startswith('http'):
                    user_avatar = f"/static/{user_avatar}"
                
                video_data = {
                    'id': video.id,
                    'title': getattr(video, 'title', None) or f"Video by {user.username}",
                    'caption': video.caption or "",
                    'video_url': video_url,
                    'thumbnail_url': thumbnail_url or '/static/assets/image/default.jpg',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'avatar_url': user_avatar or '/static/assets/image/default.jpg',
                        'is_verified': getattr(user, 'is_verified', False)
                    },
                    'stats': {
                        'likes': likes_count,
                        'comments': comments_count,
                        'views': video.view_count or 0,
                        'shares': random.randint(5, 50)
                    },
                    'interactions': {
                        'is_liked': is_liked,
                        'is_bookmarked': False
                    },
                    'created_at': video.created_at.isoformat() if video.created_at else None,
                    'duration': getattr(video, 'duration', None)
                }
                
                videos_data.append(video_data)
                
                # Set next cursor to the last video's timestamp
                if video.created_at:
                    next_cursor = video.created_at.isoformat()
                    
            except Exception as e:
                print(f"Error processing video {video.id}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'data': videos_data,
            'pagination': {
                'has_more': has_more,
                'next_cursor': next_cursor,
                'limit': limit
            },
            'meta': {
                'timestamp': datetime.now().isoformat(),
                'user_id': current_user_id,
                'count': len(videos_data)
            }
        })
        
    except Exception as e:
        print(f"Error in api_feed_videos_cursor: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load videos',
            'data': [],
            'pagination': {
                'has_more': False,
                'next_cursor': None,
                'limit': 10
            }
        }), 500

@explore_api.route('/api/videos', methods=['GET'])
def api_get_videos():
    """API endpoint untuk mengambil video dengan caption dan user yang membuatnya"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)
        
        # Validate parameters
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 20:
            per_page = 5
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get videos from database with user information
        videos_query = db.session.query(Video, User).join(
            User, Video.user_id == User.id
        ).filter(
            Video.video_url.isnot(None),
            Video.video_url != ''
        ).order_by(Video.created_at.desc())
        
        # Get total count first
        total_videos = videos_query.count()
        
        # Get paginated results
        results = videos_query.offset(offset).limit(per_page).all()
        
        # Process videos
        videos_data = []
        for video, user in results:
            try:
                # Process video URL
                video_url = video.video_url
                if video_url and not video_url.startswith('http'):
                    video_url = f"/static/{video_url}"
                
                # Process thumbnail URL
                thumbnail_url = video.thumbnail_url
                if thumbnail_url and not thumbnail_url.startswith('http'):
                    thumbnail_url = f"/static/{thumbnail_url}"
                
                # Process user avatar
                user_avatar = user.avatar_url
                if user_avatar and not user_avatar.startswith('http'):
                    user_avatar = f"/static/{user_avatar}"
                
                videos_data.append({
                    'id': video.id,
                    'title': getattr(video, 'title', None) or "Untitled Video",
                    'caption': video.caption or "",
                    'video_url': video_url,
                    'thumbnail_url': thumbnail_url or '/static/assets/image/default.jpg',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'avatar_url': user_avatar or '/static/assets/image/default.jpg'
                    },
                    'created_at': video.created_at.isoformat() if video.created_at else None,
                    'view_count': video.view_count or 0
                })
            except Exception as e:
                print(f"Error processing video {video.id}: {e}")
                continue
        
        # Calculate pagination info
        has_more = (offset + per_page) < total_videos
        total_pages = (total_videos + per_page - 1) // per_page
        
        return jsonify({
            'success': True,
            'data': videos_data,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_videos': total_videos,
                'total_pages': total_pages,
                'has_more': has_more,
                'has_previous': page > 1
            }
        })
        
    except Exception as e:
        print(f"Error in api_get_videos: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load videos',
            'data': [],
            'pagination': {
                'current_page': 1,
                'per_page': 5,
                'total_videos': 0,
                'total_pages': 0,
                'has_more': False,
                'has_previous': False
            }
        }), 500

@explore_api.route('/api/feed/video/<int:video_id>', methods=['GET'])
def api_feed_video_detail(video_id):
    """API endpoint untuk mendapatkan detail video individual dengan semua informasi"""
    try:
        current_user_id = session.get('user_id')
        
        # Get video with user information
        result = db.session.query(Video, User).join(
            User, Video.user_id == User.id
        ).filter(Video.id == video_id).first()
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Video not found'
            }), 404
        
        video, user = result
        
        # Get interaction counts
        likes_count = db.session.query(Like).filter_by(
            content_type='video',
            content_id=str(video_id)
        ).count()
        
        comments_count = db.session.query(Comment).filter_by(
            content_type='video',
            content_id=str(video_id)
        ).count()
        
        # Check if current user liked this video
        is_liked = False
        if current_user_id:
            existing_like = db.session.query(Like).filter_by(
                user_id=current_user_id,
                content_type='video',
                content_id=str(video_id)
            ).first()
            is_liked = existing_like is not None
        
        # Check if current user is following the video author
        is_following = False
        if current_user_id and current_user_id != user.id:
            existing_follow = db.session.query(Follow).filter_by(
                follower_id=current_user_id,
                following_id=user.id
            ).first()
            is_following = existing_follow is not None
        
        # Process URLs
        video_url = video.video_url
        if video_url and not video_url.startswith('http'):
            video_url = f"/static/{video_url}"
        
        thumbnail_url = video.thumbnail_url
        if thumbnail_url and not thumbnail_url.startswith('http'):
            thumbnail_url = f"/static/{thumbnail_url}"
        
        user_avatar = user.avatar_url
        if user_avatar and not user_avatar.startswith('http'):
            user_avatar = f"/static/{user_avatar}"
        
        # Get recent comments (limit 5)
        recent_comments = db.session.query(Comment, User).join(
            User, Comment.user_id == User.id
        ).filter(
            Comment.content_type == 'video',
            Comment.content_id == str(video_id)
        ).order_by(Comment.created_at.desc()).limit(5).all()
        
        comments_data = []
        for comment, comment_user in recent_comments:
            comment_user_avatar = comment_user.avatar_url
            if comment_user_avatar and not comment_user_avatar.startswith('http'):
                comment_user_avatar = f"/static/{comment_user_avatar}"
            
            comments_data.append({
                'id': comment.id,
                'comment': comment.comment,
                'user': {
                    'id': comment_user.id,
                    'username': comment_user.username,
                    'avatar_url': comment_user_avatar or '/static/assets/image/default.jpg'
                },
                'created_at': comment.created_at.isoformat() if comment.created_at else None
            })
        
        video_data = {
            'id': video.id,
            'title': video.title or f"Video by {user.username}",
            'caption': video.caption or "",
            'video_url': video_url,
            'thumbnail_url': thumbnail_url or '/static/assets/image/default.jpg',
            'user': {
                'id': user.id,
                'username': user.username,
                'avatar_url': user_avatar or '/static/assets/image/default.jpg',
                'is_verified': getattr(user, 'is_verified', False),
                'followers_count': db.session.query(Follow).filter_by(following_id=user.id).count(),
                'is_following': is_following
            },
            'stats': {
                'likes': likes_count,
                'comments': comments_count,
                'views': video.view_count or 0,
                'shares': random.randint(5, 50)
            },
            'interactions': {
                'is_liked': is_liked,
                'is_bookmarked': False
            },
            'created_at': video.created_at.isoformat() if video.created_at else None,
            'duration': getattr(video, 'duration', None),
            'recent_comments': comments_data
        }
        
        return jsonify({
            'success': True,
            'data': video_data
        })
        
    except Exception as e:
        print(f"Error in api_feed_video_detail: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load video details'
        }), 500

@explore_api.route('/api/videos/<int:video_id>', methods=['GET'])
def api_get_video_by_id(video_id):
    """API endpoint untuk mengambil video berdasarkan ID"""
    try:
        # Get video with user information
        result = db.session.query(Video, User).join(
            User, Video.user_id == User.id
        ).filter(Video.id == video_id).first()
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Video not found'
            }), 404
        
        video, user = result
        
        # Process video URL
        video_url = video.video_url
        if video_url and not video_url.startswith('http'):
            video_url = f"/static/{video_url}"
        
        # Process thumbnail URL
        thumbnail_url = video.thumbnail_url
        if thumbnail_url and not thumbnail_url.startswith('http'):
            thumbnail_url = f"/static/{thumbnail_url}"
        
        # Process user avatar
        user_avatar = user.avatar_url
        if user_avatar and not user_avatar.startswith('http'):
            user_avatar = f"/static/{user_avatar}"
        
        video_data = {
            'id': video.id,
            'title': video.title or "Untitled Video",
            'caption': video.caption or "",
            'video_url': video_url,
            'thumbnail_url': thumbnail_url or '/static/assets/image/default.jpg',
            'user': {
                'id': user.id,
                'username': user.username,
                'avatar_url': user_avatar or '/static/assets/image/default.jpg'
            },
            'created_at': video.created_at.isoformat() if video.created_at else None,
            'view_count': video.view_count or 0
        }
        
        return jsonify({
            'success': True,
            'data': video_data
        })
        
    except Exception as e:
        print(f"Error in api_get_video_by_id: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load video'
        }), 500

@explore_api.route('/api/videos/search', methods=['GET'])
def api_search_videos():
    """API endpoint untuk mencari video berdasarkan title atau caption"""
    try:
        # Get query parameters
        query = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        # Validate parameters
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 20:
            per_page = 5
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Search videos by title or caption
        videos_query = db.session.query(Video, User).join(
            User, Video.user_id == User.id
        ).filter(
            Video.video_url.isnot(None),
            Video.video_url != '',
            (Video.title.contains(query) | Video.caption.contains(query))
        ).order_by(Video.created_at.desc())
        
        # Get total count
        total_videos = videos_query.count()
        
        # Get paginated results
        results = videos_query.offset(offset).limit(per_page).all()
        
        # Process videos
        videos_data = []
        for video, user in results:
            try:
                # Process video URL
                video_url = video.video_url
                if video_url and not video_url.startswith('http'):
                    video_url = f"/static/{video_url}"
                
                # Process thumbnail URL
                thumbnail_url = video.thumbnail_url
                if thumbnail_url and not thumbnail_url.startswith('http'):
                    thumbnail_url = f"/static/{thumbnail_url}"
                
                # Process user avatar
                user_avatar = user.avatar_url
                if user_avatar and not user_avatar.startswith('http'):
                    user_avatar = f"/static/{user_avatar}"
                
                videos_data.append({
                    'id': video.id,
                    'title': getattr(video, 'title', None) or "Untitled Video",
                    'caption': video.caption or "",
                    'video_url': video_url,
                    'thumbnail_url': thumbnail_url or '/static/assets/image/default.jpg',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'avatar_url': user_avatar or '/static/assets/image/default.jpg'
                    },
                    'created_at': video.created_at.isoformat() if video.created_at else None,
                    'view_count': video.view_count or 0
                })
            except Exception as e:
                print(f"Error processing video {video.id}: {e}")
                continue
        
        # Calculate pagination info
        has_more = (offset + per_page) < total_videos
        total_pages = (total_videos + per_page - 1) // per_page
        
        return jsonify({
            'success': True,
            'data': videos_data,
            'query': query,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_videos': total_videos,
                'total_pages': total_pages,
                'has_more': has_more,
                'has_previous': page > 1
            }
        })
        
    except Exception as e:
        print(f"Error in api_search_videos: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to search videos'
        }), 500

def create_dummy_videos(page, per_page):
    """Create dummy video data for testing"""
    dummy_videos = [
        {
            'id': 1,
            'title': "Amazing AI Generated Music",
            'description': "Check out this incredible music created with AI technology! 🎵",
            'videoUrl': "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            'thumbnail': "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/BigBuckBunny.jpg",
            'likes': 1250,
            'comments': 89,
            'shares': 45,
            'bookmarks': 23,
            'author': "AI Music Creator",
            'authorAvatar': "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop&crop=face",
            'isLiked': False,
            'isBookmarked': False
        },
        {
            'id': 2,
            'title': "Stunning AI Art Generation",
            'description': "Watch as AI creates beautiful digital art in real-time! 🎨",
            'videoUrl': "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
            'thumbnail': "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ElephantsDream.jpg",
            'likes': 2100,
            'comments': 156,
            'shares': 78,
            'bookmarks': 45,
            'author': "Digital Artist",
            'authorAvatar': "https://images.unsplash.com/photo-1494790108755-2616b612b786?w=100&h=100&fit=crop&crop=face",
            'isLiked': True,
            'isBookmarked': False
        },
        {
            'id': 3,
            'title': "AI Video Creation Magic",
            'description': "See how AI transforms text into amazing videos! ✨",
            'videoUrl': "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            'thumbnail': "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerBlazes.jpg",
            'likes': 890,
            'comments': 67,
            'shares': 34,
            'bookmarks': 18,
            'author': "Video Creator",
            'authorAvatar': "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face",
            'isLiked': False,
            'isBookmarked': True
        },
        {
            'id': 4,
            'title': "AI Text to Speech Demo",
            'description': "Listen to this natural-sounding AI voice! 🎤",
            'videoUrl': "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
            'thumbnail': "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerEscapes.jpg",
            'likes': 1560,
            'comments': 123,
            'shares': 56,
            'bookmarks': 32,
            'author': "Voice AI",
            'authorAvatar': "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop&crop=face",
            'isLiked': False,
            'isBookmarked': False
        },
        {
            'id': 5,
            'title': "AI Chat Assistant in Action",
            'description': "Watch our AI assistant help with creative tasks! 🤖",
            'videoUrl': "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
            'thumbnail': "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerFun.jpg",
            'likes': 3200,
            'comments': 234,
            'shares': 98,
            'bookmarks': 67,
            'author': "AI Assistant",
            'authorAvatar': "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop&crop=face",
            'isLiked': True,
            'isBookmarked': True
        }
    ]
    
    # Add more dummy videos for pagination
    for i in range(6, 50):
        dummy_videos.append({
            'id': i,
            'title': f"AI Generated Content #{i}",
            'description': f"This is amazing AI-generated content! Check it out! 🚀 #{i}",
            'videoUrl': f"https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            'thumbnail': f"https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/BigBuckBunny.jpg",
            'likes': random.randint(100, 5000),
            'comments': random.randint(10, 500),
            'shares': random.randint(5, 200),
            'bookmarks': random.randint(3, 100),
            'author': f"Creator {i}",
            'authorAvatar': f"https://images.unsplash.com/photo-{random.randint(1000000000000, 9999999999999)}?w=100&h=100&fit=crop&crop=face",
            'isLiked': random.choice([True, False]),
            'isBookmarked': random.choice([True, False])
        })
    
    # Calculate start and end indices for pagination
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    return dummy_videos[start_idx:end_idx]

@explore_api.route('/api/feed/video/<int:video_id>/like', methods=['POST'])
def api_video_like(video_id):
    """API endpoint to like/unlike a video"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        current_user_id = session.get('user_id')
        
        # Check if user already liked this video
        existing_like = db.session.query(Like).filter_by(
            user_id=current_user_id,
            content_type='video',
            content_id=str(video_id)
        ).first()
        
        if existing_like:
            # Unlike - remove the like
            db.session.delete(existing_like)
            is_liked = False
        else:
            # Like - add new like
            new_like = Like(
                user_id=current_user_id,
                content_type='video',
                content_id=str(video_id)
            )
            db.session.add(new_like)
            is_liked = True
        
        db.session.commit()
        
        # Get updated likes count
        likes_count = db.session.query(Like).filter_by(
            content_type='video',
            content_id=str(video_id)
        ).count()
        
        return jsonify({
            'success': True,
            'is_liked': is_liked,
            'likes_count': likes_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@explore_api.route('/api/feed/video/<int:video_id>/comment', methods=['POST'])
def api_video_comment(video_id):
    """API endpoint to add a comment to a video"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        comment_text = data.get('comment', '').strip()
        
        if not comment_text:
            return jsonify({'error': 'Comment cannot be empty'}), 400
        
        current_user_id = session.get('user_id')
        
        # Add new comment
        new_comment = Comment(
            user_id=current_user_id,
            content_type='video',
            content_id=str(video_id),
            comment=comment_text
        )
        db.session.add(new_comment)
        db.session.commit()
        
        # Get updated comments count
        comments_count = db.session.query(Comment).filter_by(
            content_type='video',
            content_id=str(video_id)
        ).count()
        
        return jsonify({
            'success': True,
            'comments_count': comments_count,
            'comment': {
                'id': new_comment.id,
                'comment': comment_text,
                'user_id': current_user_id,
                'created_at': new_comment.created_at.isoformat() if new_comment.created_at else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@explore_api.route('/api/feed/video/<int:video_id>/share', methods=['POST'])
def api_video_share(video_id):
    """API endpoint to share a video"""
    try:
        # For now, just increment share count (you can implement actual sharing logic later)
        # This is a simple implementation - you might want to track actual shares
        
        return jsonify({
            'success': True,
            'message': 'Video shared successfully',
            'shares_count': random.randint(1, 100)  # Mock share count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@explore_api.route('/api/feed/video/<int:video_id>/comments', methods=['GET'])
def api_video_comments(video_id):
    """API endpoint to get comments for a video"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        offset = (page - 1) * per_page
        
        # Get comments for the video
        comments = db.session.query(Comment).filter_by(
            content_type='video',
            content_id=str(video_id)
        ).order_by(Comment.created_at.desc()).offset(offset).limit(per_page).all()
        
        comments_data = []
        for comment in comments:
            user = db.session.query(User).filter_by(id=comment.user_id).first()
            comments_data.append({
                'id': comment.id,
                'comment': comment.comment,
                'user': {
                    'id': user.id if user else None,
                    'username': user.username if user else 'Unknown',
                    'avatar_url': user.avatar_url if user else '/static/assets/image/default.jpg'
                },
                'created_at': comment.created_at.isoformat() if comment.created_at else None
            })
        
        # Get total comments count
        total_comments = db.session.query(Comment).filter_by(
            content_type='video',
            content_id=str(video_id)
        ).count()
        
        has_more = (offset + per_page) < total_comments
        
        return jsonify({
            'success': True,
            'comments': comments_data,
            'has_more': has_more,
            'page': page,
            'per_page': per_page,
            'total': total_comments
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@explore_api.route('/api/analytics/track', methods=['POST'])
def api_analytics_track():
    """API endpoint to track video interactions"""
    try:
        data = request.get_json()
        action = data.get('action')
        video_id = data.get('video_id')
        timestamp = data.get('timestamp')
        metadata = data.get('metadata', {})
        
        # Log analytics data (you can store this in database later)
        print(f"Analytics: {action} for video {video_id} at {timestamp}")
        print(f"Metadata: {metadata}")
        
        # Here you can store the analytics data in your database
        # For now, we'll just log it
        
        return jsonify({
            'success': True,
            'message': 'Analytics tracked successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@explore_api.route('/api/feed/video/<int:video_id>/stats', methods=['GET'])
def api_video_stats(video_id):
    """API endpoint to get video statistics"""
    try:
        # Get video from database
        video = db.session.query(Video).filter_by(id=video_id).first()
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Get statistics
        likes_count = db.session.query(Like).filter_by(
            content_type='video',
            content_id=str(video_id)
        ).count()
        
        comments_count = db.session.query(Comment).filter_by(
            content_type='video',
            content_id=str(video_id)
        ).count()
        
        # Get user info
        user = db.session.query(User).filter_by(id=video.user_id).first()
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'likes': likes_count,
            'comments': comments_count,
            'shares': random.randint(10, 100),  # Mock share count
            'views': video.view_count or 0,
            'author': {
                'id': user.id if user else None,
                'username': user.username if user else 'Unknown',
                'avatar_url': user.avatar_url if user else '/static/assets/image/default.jpg'
            },
            'created_at': video.created_at.isoformat() if video.created_at else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

