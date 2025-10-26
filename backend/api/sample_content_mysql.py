from flask import Blueprint, jsonify, request
from datetime import datetime
import os
import json

# Import models
from models_mysql import db, SampleImage, SampleMusic, GalleryImage, MusicTrack, GenericImage, GenericMusic

# Blueprint untuk sample content API
sample_content_bp = Blueprint('sample_content', __name__)

# Configuration untuk memilih model yang sesuai
USE_GENERIC_MODELS = True  # Set to True jika menggunakan tabel yang sudah ada
USE_ALTERNATIVE_MODELS = False  # Set to True jika menggunakan GalleryImage/MusicTrack

def get_image_model():
    """Mengembalikan model yang sesuai untuk images"""
    if USE_GENERIC_MODELS:
        return GenericImage
    elif USE_ALTERNATIVE_MODELS:
        return GalleryImage
    else:
        return SampleImage

def get_music_model():
    """Mengembalikan model yang sesuai untuk music"""
    if USE_GENERIC_MODELS:
        return GenericMusic
    elif USE_ALTERNATIVE_MODELS:
        return MusicTrack
    else:
        return SampleMusic

# API Endpoints
@sample_content_bp.route('/api/sample-images', methods=['GET'])
def get_sample_images():
    """Mengambil sample gambar dari database MySQL"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 8, type=int)
        category = request.args.get('category', None)
        featured_only = request.args.get('featured', False, type=bool)
        
        ImageModel = get_image_model()
        query = ImageModel.query
        
        if category and category != 'all':
            query = query.filter(ImageModel.category == category)
        
        if featured_only:
            query = query.filter(ImageModel.is_featured == True)
        
        query = query.order_by(ImageModel.created_at.desc())
        
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
    """Mengambil sample musik dari database MySQL"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 6, type=int)
        genre = request.args.get('genre', None)
        featured_only = request.args.get('featured', False, type=bool)
        
        MusicModel = get_music_model()
        query = MusicModel.query
        
        if genre and genre != 'all':
            query = query.filter(MusicModel.genre == genre)
        
        if featured_only:
            query = query.filter(MusicModel.is_featured == True)
        
        query = query.order_by(MusicModel.created_at.desc())
        
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
    """Mengambil daftar kategori gambar dari MySQL"""
    try:
        ImageModel = get_image_model()
        categories = db.session.query(ImageModel.category).distinct().all()
        category_list = [cat[0] for cat in categories if cat[0]]
        
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
    """Mengambil daftar genre musik dari MySQL"""
    try:
        MusicModel = get_music_model()
        genres = db.session.query(MusicModel.genre).distinct().all()
        genre_list = [genre[0] for genre in genres if genre[0]]
        
        return jsonify({
            'success': True,
            'data': genre_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sample_content_bp.route('/api/database-info', methods=['GET'])
def get_database_info():
    """Mengambil informasi tentang database dan tabel"""
    try:
        ImageModel = get_image_model()
        MusicModel = get_music_model()
        
        image_count = ImageModel.query.count()
        music_count = MusicModel.query.count()
        
        # Get table names
        image_table = ImageModel.__tablename__
        music_table = MusicModel.__tablename__
        
        return jsonify({
            'success': True,
            'data': {
                'image_table': image_table,
                'music_table': music_table,
                'image_count': image_count,
                'music_count': music_count,
                'total_count': image_count + music_count,
                'using_generic_models': USE_GENERIC_MODELS,
                'using_alternative_models': USE_ALTERNATIVE_MODELS
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Fungsi untuk mengisi data sample (jika diperlukan)
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
        }
    ]
    
    ImageModel = get_image_model()
    MusicModel = get_music_model()
    
    # Insert sample images
    for img_data in sample_images:
        existing = ImageModel.query.filter_by(title=img_data['title']).first()
        if not existing:
            image = ImageModel(**img_data)
            db.session.add(image)
    
    # Insert sample music
    for music_data in sample_music:
        existing = MusicModel.query.filter_by(title=music_data['title']).first()
        if not existing:
            music = MusicModel(**music_data)
            db.session.add(music)
    
    db.session.commit()
    print("Sample data populated successfully!")

# Register blueprint
def register_sample_content_api(app, database):
    global db
    db = database
    app.register_blueprint(sample_content_bp)
