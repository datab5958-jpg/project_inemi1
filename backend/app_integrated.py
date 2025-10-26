#!/usr/bin/env python3
"""
Integrated Flask Application
Mengintegrasikan landing page dengan database MySQL yang sudah ada
"""

import os
import sys
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import existing models and database
from models_database import db, Image, Video, Song, User
from api.landing_content import register_landing_content_api

def create_app():
    """Factory function untuk membuat aplikasi Flask terintegrasi"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:@localhost/inemi'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # API Keys
    app.config['WAVESPEED_API_KEY'] = os.environ.get('WAVESPEED_API_KEY')
    app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY')
    app.config['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
    app.config['SUNO_API_KEY'] = os.environ.get('SUNO_API_KEY')
    app.config['ELEVENLABS_API_KEY'] = os.environ.get('ELEVENLABS_API_KEY')
    
    # Enable CORS
    CORS(app)
    
    # Initialize database
    db.init_app(app)
    
    # Register API blueprints
    register_landing_content_api(app)
    
    # Routes
    @app.route('/')
    def index():
        """Route utama untuk landing page"""
        return render_template('landing/index.html')
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            # Test database connection
            image_count = Image.query.count()
            video_count = Video.query.count()
            song_count = Song.query.count()
            user_count = User.query.count()
            
            return jsonify({
                'status': 'healthy',
                'database': {
                    'images': image_count,
                    'videos': video_count,
                    'songs': song_count,
                    'users': user_count
                },
                'message': 'Landing page integrated with MySQL database'
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    @app.route('/api/database-info')
    def database_info():
        """Informasi tentang database"""
        try:
            image_count = Image.query.count()
            video_count = Video.query.count()
            song_count = Song.query.count()
            user_count = User.query.count()
            
            return jsonify({
                'success': True,
                'data': {
                    'total_images': image_count,
                    'total_videos': video_count,
                    'total_songs': song_count,
                    'total_users': user_count,
                    'total_content': image_count + video_count + song_count,
                    'database_type': 'MySQL',
                    'status': 'Connected'
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    print("=" * 60)
    print("🚀 INEMI Landing Page - MySQL Integration")
    print("=" * 60)
    print("📊 Features:")
    print("   • Dynamic content loading from MySQL database")
    print("   • Modern futuristic UI with 3D animations")
    print("   • Real-time statistics and counters")
    print("   • Responsive design for all devices")
    print("   • GPU-optimized animations (60 FPS)")
    print("=" * 60)
    print("🌐 URLs:")
    print("   • Landing Page: http://localhost:5000")
    print("   • Health Check: http://localhost:5000/health")
    print("   • Database Info: http://localhost:5000/api/database-info")
    print("   • API Images: http://localhost:5000/api/landing/images")
    print("   • API Music: http://localhost:5000/api/landing/music")
    print("   • API Stats: http://localhost:5000/api/landing/stats")
    print("=" * 60)
    
    # Test database connection
    with app.app_context():
        try:
            db.session.execute('SELECT 1')
            print("✅ Database connection: SUCCESS")
        except Exception as e:
            print(f"❌ Database connection: FAILED - {e}")
            print("   Please check your MySQL configuration")
    
    print("=" * 60)
    print("🎯 Starting server...")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
