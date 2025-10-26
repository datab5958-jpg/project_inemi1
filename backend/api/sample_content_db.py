from flask import Blueprint, jsonify, request
from datetime import datetime
import os
import json

# Import models
from models import db, SampleImage, SampleMusic

# Blueprint untuk sample content API
sample_content_bp = Blueprint('sample_content', __name__)

# API Endpoints
@sample_content_bp.route('/api/sample-images', methods=['GET'])
def get_sample_images():
    """Mengambil sample gambar dari database"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 8, type=int)
        category = request.args.get('category', None)
        featured_only = request.args.get('featured', False, type=bool)
        
        query = SampleImage.query
        
        if category and category != 'all':
            query = query.filter(SampleImage.category == category)
        
        if featured_only:
            query = query.filter(SampleImage.is_featured == True)
        
        query = query.order_by(SampleImage.created_at.desc())
        
        # Pagination
        total = query.count()
        start = (page - 1) * per_page
        images = query.offset(start).limit(per_page).all()
        
        # Convert to dict
        images_data = [image.to_dict() for image in images]
        
        return jsonify({
            'success': True,
            'data': images_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'has_next': start + per_page < total,
                'has_prev': page > 1
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sample_content_bp.route('/api/sample-music', methods=['GET'])
def get_sample_music():
    """Mengambil sample musik dari database"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 6, type=int)
        genre = request.args.get('genre', None)
        featured_only = request.args.get('featured', False, type=bool)
        
        query = SampleMusic.query
        
        if genre and genre != 'all':
            query = query.filter(SampleMusic.genre == genre)
        
        if featured_only:
            query = query.filter(SampleMusic.is_featured == True)
        
        query = query.order_by(SampleMusic.created_at.desc())
        
        # Pagination
        total = query.count()
        start = (page - 1) * per_page
        music = query.offset(start).limit(per_page).all()
        
        # Convert to dict
        music_data = [track.to_dict() for track in music]
        
        return jsonify({
            'success': True,
            'data': music_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'has_next': start + per_page < total,
                'has_prev': page > 1
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sample_content_bp.route('/api/sample-images/categories', methods=['GET'])
def get_image_categories():
    """Mengambil daftar kategori gambar"""
    try:
        categories = db.session.query(SampleImage.category).distinct().all()
        category_list = [cat[0] for cat in categories]
        
        return jsonify({
            'success': True,
            'data': category_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sample_content_bp.route('/api/sample-music/genres', methods=['GET'])
def get_music_genres():
    """Mengambil daftar genre musik"""
    try:
        genres = db.session.query(SampleMusic.genre).distinct().all()
        genre_list = [genre[0] for genre in genres]
        
        return jsonify({
            'success': True,
            'data': genre_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Fungsi untuk mengisi data sample
def populate_sample_data():
    """Mengisi database dengan data sample"""
    
    # Sample images data
    sample_images = [
        {
            'title': 'Cyberpunk Portrait',
            'description': 'Futuristic portrait with neon lighting',
            'image_url': 'https://images.unsplash.com/photo-1541961017774-22349e4a1262?w=400&h=300&fit=crop&crop=center',
            'category': 'Portrait',
            'created_by': '@creative_ai',
            'is_featured': True,
            'tags': ['cyberpunk', 'portrait', 'neon', 'futuristic']
        },
        {
            'title': 'Mountain Landscape',
            'description': 'Breathtaking mountain vista at sunset',
            'image_url': 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=300&fit=crop&crop=center',
            'category': 'Landscape',
            'created_by': '@nature_ai',
            'is_featured': True,
            'tags': ['landscape', 'mountains', 'sunset', 'nature']
        },
        {
            'title': 'Abstract Art',
            'description': 'Colorful abstract composition',
            'image_url': 'https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=400&h=300&fit=crop&crop=center',
            'category': 'Abstract',
            'created_by': '@abstract_ai',
            'is_featured': True,
            'tags': ['abstract', 'colorful', 'art', 'modern']
        },
        {
            'title': 'Futuristic City',
            'description': 'Sci-fi cityscape with flying vehicles',
            'image_url': 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=400&h=300&fit=crop&crop=center',
            'category': 'Sci-Fi',
            'created_by': '@future_ai',
            'is_featured': True,
            'tags': ['sci-fi', 'city', 'futuristic', 'technology']
        },
        {
            'title': 'Ocean Waves',
            'description': 'Peaceful ocean waves at dawn',
            'image_url': 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=300&fit=crop&crop=center',
            'category': 'Nature',
            'created_by': '@ocean_ai',
            'is_featured': False,
            'tags': ['ocean', 'waves', 'dawn', 'peaceful']
        },
        {
            'title': 'Digital Art',
            'description': 'Modern digital illustration',
            'image_url': 'https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=400&h=300&fit=crop&crop=center',
            'category': 'Digital',
            'created_by': '@digital_ai',
            'is_featured': False,
            'tags': ['digital', 'illustration', 'modern', 'art']
        },
        {
            'title': 'Neon Dreams',
            'description': 'Vibrant neon cityscape',
            'image_url': 'https://images.unsplash.com/photo-1541961017774-22349e4a1262?w=400&h=300&fit=crop&crop=center',
            'category': 'Neon',
            'created_by': '@neon_ai',
            'is_featured': False,
            'tags': ['neon', 'cityscape', 'vibrant', 'night']
        },
        {
            'title': 'Space Galaxy',
            'description': 'Cosmic galaxy with stars',
            'image_url': 'https://images.unsplash.com/photo-1446776877081-d282a0f896e2?w=400&h=300&fit=crop&crop=center',
            'category': 'Space',
            'created_by': '@space_ai',
            'is_featured': True,
            'tags': ['space', 'galaxy', 'stars', 'cosmic']
        }
    ]
    
    # Sample music data
    sample_music = [
        {
            'title': 'Cyber Symphony',
            'description': 'Electronic symphony with cyberpunk vibes',
            'music_url': '/static/audio/cyber_symphony.mp3',
            'cover_image_url': 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop&crop=center',
            'genre': 'Electronic',
            'duration': '3:24',
            'created_by': '@cyber_ai',
            'is_featured': True,
            'tags': ['electronic', 'cyberpunk', 'symphony', 'futuristic']
        },
        {
            'title': 'Neon Dreams',
            'description': 'Ambient soundscape for relaxation',
            'music_url': '/static/audio/neon_dreams.mp3',
            'cover_image_url': 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=300&h=300&fit=crop&crop=center',
            'genre': 'Ambient',
            'duration': '4:12',
            'created_by': '@ambient_ai',
            'is_featured': True,
            'tags': ['ambient', 'relaxing', 'neon', 'dreamy']
        },
        {
            'title': 'Digital Horizon',
            'description': 'Synthwave journey through digital landscapes',
            'music_url': '/static/audio/digital_horizon.mp3',
            'cover_image_url': 'https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=300&h=300&fit=crop&crop=center',
            'genre': 'Synthwave',
            'duration': '3:45',
            'created_by': '@synth_ai',
            'is_featured': True,
            'tags': ['synthwave', 'retro', 'digital', 'nostalgic']
        },
        {
            'title': 'Future Bass',
            'description': 'Heavy bass drops with futuristic sounds',
            'music_url': '/static/audio/future_bass.mp3',
            'cover_image_url': 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop&crop=center',
            'genre': 'Bass',
            'duration': '3:18',
            'created_by': '@bass_ai',
            'is_featured': False,
            'tags': ['bass', 'heavy', 'futuristic', 'drops']
        },
        {
            'title': 'Electric Pulse',
            'description': 'Rock anthem with electronic elements',
            'music_url': '/static/audio/electric_pulse.mp3',
            'cover_image_url': 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=300&h=300&fit=crop&crop=center',
            'genre': 'Rock',
            'duration': '4:02',
            'created_by': '@rock_ai',
            'is_featured': False,
            'tags': ['rock', 'electric', 'anthem', 'energy']
        },
        {
            'title': 'Jazz Fusion',
            'description': 'Modern jazz with AI-generated improvisation',
            'music_url': '/static/audio/jazz_fusion.mp3',
            'cover_image_url': 'https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=300&h=300&fit=crop&crop=center',
            'genre': 'Jazz',
            'duration': '5:15',
            'created_by': '@jazz_ai',
            'is_featured': False,
            'tags': ['jazz', 'fusion', 'improvisation', 'smooth']
        }
    ]
    
    # Insert sample images
    for img_data in sample_images:
        existing = SampleImage.query.filter_by(title=img_data['title']).first()
        if not existing:
            image = SampleImage(**img_data)
            db.session.add(image)
    
    # Insert sample music
    for music_data in sample_music:
        existing = SampleMusic.query.filter_by(title=music_data['title']).first()
        if not existing:
            music = SampleMusic(**music_data)
            db.session.add(music)
    
    db.session.commit()
    print("Sample data populated successfully!")

# Register blueprint
def register_sample_content_api(app, database):
    global db
    db = database
    app.register_blueprint(sample_content_bp)
