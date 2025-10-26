from flask import Blueprint, jsonify, request
from models import db, Image, Video, Song
from sqlalchemy import desc
import os

favorite_bp = Blueprint('favorite', __name__)

@favorite_bp.route('/api/images/favorite', methods=['GET'])
def get_favorite_images():
    """Get whitelisted high-quality generated images"""
    try:
        # Get images that are marked as favorites or have high quality scores
        # For now, we'll get the most recent high-quality images
        # In the future, this can be enhanced with a favorite/whitelist system
        
        # Get images with high engagement (likes, views) or marked as favorites
        favorite_images = Image.query.filter(
            Image.is_favorite == True
        ).order_by(desc(Image.created_at)).limit(20).all()
        
        # If no favorites found, get high-quality recent images as fallback
        if not favorite_images:
            favorite_images = Image.query.order_by(desc(Image.created_at)).limit(12).all()
        
        items = []
        for img in favorite_images:
            items.append({
                'id': img.id,
                'url': img.image_url,
                'title': img.caption or f'AI Generated Image {img.id}',
                'type': 'image',
                'user': img.user.username if img.user else 'Anonymous',
                'caption': img.caption or 'High-quality AI generated image',
                'created_at': img.created_at.isoformat() if img.created_at else None,
                'isFavorite': True
            })
        
        return jsonify({
            'success': True,
            'items': items,
            'total': len(items),
            'message': 'Favorite images loaded successfully'
        })
        
    except Exception as e:
        print(f"Error getting favorite images: {e}")
        return jsonify({
            'success': False,
            'items': [],
            'error': 'Failed to load favorite images'
        }), 500

@favorite_bp.route('/api/videos/favorite', methods=['GET'])
def get_favorite_videos():
    """Get whitelisted high-quality generated videos"""
    try:
        # Get videos that are marked as favorites or have high quality scores
        favorite_videos = Video.query.filter(
            Video.is_favorite == True
        ).order_by(desc(Video.created_at)).limit(20).all()
        
        # If no favorites found, get high-quality recent videos as fallback
        if not favorite_videos:
            favorite_videos = Video.query.order_by(desc(Video.created_at)).limit(12).all()
        
        items = []
        for vid in favorite_videos:
            items.append({
                'id': vid.id,
                'url': vid.video_url,
                'title': vid.caption or f'AI Generated Video {vid.id}',
                'type': 'video',
                'user': vid.user.username if vid.user else 'Anonymous',
                'caption': vid.caption or 'High-quality AI generated video',
                'created_at': vid.created_at.isoformat() if vid.created_at else None,
                'isFavorite': True
            })
        
        return jsonify({
            'success': True,
            'items': items,
            'total': len(items),
            'message': 'Favorite videos loaded successfully'
        })
        
    except Exception as e:
        print(f"Error getting favorite videos: {e}")
        return jsonify({
            'success': False,
            'items': [],
            'error': 'Failed to load favorite videos'
        }), 500

@favorite_bp.route('/api/songs/favorite', methods=['GET'])
def get_favorite_songs():
    """Get whitelisted high-quality generated music"""
    try:
        # Get songs that are marked as favorites or have high quality scores
        favorite_songs = Song.query.filter(
            Song.is_favorite == True
        ).order_by(desc(Song.created_at)).limit(20).all()
        
        # If no favorites found, get high-quality recent songs as fallback
        if not favorite_songs:
            favorite_songs = Song.query.order_by(desc(Song.created_at)).limit(12).all()
        
        items = []
        for song in favorite_songs:
            items.append({
                'id': song.id,
                'url': song.audio_url,
                'title': song.title or f'AI Generated Song {song.id}',
                'type': 'music',
                'user': song.user.username if song.user else 'Anonymous',
                'artist': song.artist or 'AI Generated',
                'caption': song.lyrics[:100] + '...' if song.lyrics and len(song.lyrics) > 100 else song.lyrics or 'High-quality AI generated music',
                'created_at': song.created_at.isoformat() if song.created_at else None,
                'isFavorite': True
            })
        
        return jsonify({
            'success': True,
            'items': items,
            'total': len(items),
            'message': 'Favorite songs loaded successfully'
        })
        
    except Exception as e:
        print(f"Error getting favorite songs: {e}")
        return jsonify({
            'success': False,
            'items': [],
            'error': 'Failed to load favorite songs'
        }), 500

@favorite_bp.route('/api/favorite/toggle', methods=['POST'])
def toggle_favorite():
    """Toggle favorite status for an item"""
    try:
        data = request.get_json()
        content_type = data.get('type')  # 'image', 'video', or 'music'
        content_id = data.get('id')
        
        if not content_type or not content_id:
            return jsonify({
                'success': False,
                'error': 'Missing content type or ID'
            }), 400
        
        # Get the appropriate model based on content type
        if content_type == 'image':
            item = Image.query.get(content_id)
        elif content_type == 'video':
            item = Video.query.get(content_id)
        elif content_type == 'music':
            item = Song.query.get(content_id)
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid content type'
            }), 400
        
        if not item:
            return jsonify({
                'success': False,
                'error': 'Content not found'
            }), 404
        
        # Toggle favorite status
        if hasattr(item, 'is_favorite'):
            item.is_favorite = not item.is_favorite
        else:
            # If the field doesn't exist, create it (for backward compatibility)
            item.is_favorite = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'isFavorite': item.is_favorite,
            'message': f'Content {"added to" if item.is_favorite else "removed from"} favorites'
        })
        
    except Exception as e:
        print(f"Error toggling favorite: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to toggle favorite status'
        }), 500

@favorite_bp.route('/api/favorite/whitelist', methods=['POST'])
def add_to_whitelist():
    """Add content to whitelist (admin function)"""
    try:
        data = request.get_json()
        content_type = data.get('type')
        content_id = data.get('id')
        reason = data.get('reason', 'High quality content')
        
        if not content_type or not content_id:
            return jsonify({
                'success': False,
                'error': 'Missing content type or ID'
            }), 400
        
        # Get the appropriate model based on content type
        if content_type == 'image':
            item = Image.query.get(content_id)
        elif content_type == 'video':
            item = Video.query.get(content_id)
        elif content_type == 'music':
            item = Song.query.get(content_id)
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid content type'
            }), 400
        
        if not item:
            return jsonify({
                'success': False,
                'error': 'Content not found'
            }), 404
        
        # Mark as favorite and add whitelist reason
        if hasattr(item, 'is_favorite'):
            item.is_favorite = True
        if hasattr(item, 'whitelist_reason'):
            item.whitelist_reason = reason
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Content added to whitelist successfully'
        })
        
    except Exception as e:
        print(f"Error adding to whitelist: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to add content to whitelist'
        }), 500
