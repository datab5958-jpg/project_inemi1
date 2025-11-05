"""
INEMI Application - Main Entry Point
Mengintegrasikan semua blueprint dan route yang sudah ada
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import models - using the main models file
from models import db, Image, Video, User, Message, Song, Like, Comment, VideoIklan, Follow, ModerationAction, Product, Order, Payment, ViewCount, Notification, Prompt

# Import all blueprints
# Web Blueprints (UI Routes)
from web.routes import web_pages          # Main web routes (/, /home, /login, /register, etc.)
from web.admin import admin_bp            # Admin dashboard (/admin/*)
from web.animasi import animasi_bp        # Animation features
from web.explore_api import explore_api   # Explore page API
from web.face_swap import face_swap_bp    # Face swap functionality
from web.favorite import favorite_bp      # Favorite content management
from web.foto import foto_bp              # Photo generation and management
from web.fusigaya import fusigaya_bp      # Fusigaya AI features
from web.image_video import image_video_bp # Image to video conversion
from web.musik import musik_bp            # Music generation and management
from web.profil import profil_bp          # User profile management
from web.video import video_bp            # Video generation and management
from web.ai_generate import ai_generate_bp  # Unified AI Generate page and API
from generate_banner import generate_banner_bp  # Banner generation functionality
from Generate_video_avatar import generate_video_avatar_bp  # Video avatar generation functionality

# API Blueprints (Backend Routes)
from api.landing_content import landing_content_bp  # Landing page content API
from api.routes import api_routes                   # Main API routes (/api/*)

# Import custom filters
from web.utils import utc_to_wib, format_tanggal_indonesia

def create_app():
    """Factory function untuk membuat aplikasi Flask dengan semua blueprint"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:@localhost/inemi'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Session Configuration
    from datetime import timedelta
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # API Keys
    app.config['WAVESPEED_API_KEY'] = os.environ.get('WAVESPEED_API_KEY')
    app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY')
    app.config['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
    app.config['SUNO_API_KEY'] = os.environ.get('SUNO_API_KEY')
    app.config['ELEVENLABS_API_KEY'] = os.environ.get('ELEVENLABS_API_KEY')
    
    # File Upload Configuration
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    app.config['DOMAIN_PUBLIC'] = os.environ.get('DOMAIN_PUBLIC', 'http://127.0.0.1:5000')
    
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Enable CORS with credentials support
    CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
    
    # Initialize database
    db.init_app(app)
    
    # Register custom Jinja2 filters
    app.jinja_env.filters['utc_to_wib'] = utc_to_wib
    app.jinja_env.filters['format_tanggal_id'] = format_tanggal_indonesia
    
    # Register all blueprints
    print("Registering blueprints...")
    
    # Web blueprints
    try:
        app.register_blueprint(web_pages)
        print("SUCCESS: web_pages blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register web_pages: {e}")
    
    try:
        app.register_blueprint(admin_bp)
        print("SUCCESS: admin_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register admin_bp: {e}")
    
    try:
        app.register_blueprint(animasi_bp)
        print("SUCCESS: animasi_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register animasi_bp: {e}")
    
    try:
        app.register_blueprint(explore_api)
        print("SUCCESS: explore_api blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register explore_api: {e}")
    
    try:
        app.register_blueprint(face_swap_bp)
        print("SUCCESS: face_swap_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register face_swap_bp: {e}")
    
    try:
        app.register_blueprint(favorite_bp)
        print("SUCCESS: favorite_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register favorite_bp: {e}")
    
    try:
        app.register_blueprint(foto_bp)
        print("SUCCESS: foto_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register foto_bp: {e}")
    
    try:
        app.register_blueprint(fusigaya_bp)
        print("SUCCESS: fusigaya_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register fusigaya_bp: {e}")
    
    try:
        app.register_blueprint(image_video_bp)
        print("SUCCESS: image_video_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register image_video_bp: {e}")
    
    try:
        app.register_blueprint(musik_bp, url_prefix='/musik')
        print("SUCCESS: musik_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register musik_bp: {e}")
    
    try:
        app.register_blueprint(profil_bp)
        print("SUCCESS: profil_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register profil_bp: {e}")
    
    try:
        app.register_blueprint(video_bp)
        print("SUCCESS: video_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register video_bp: {e}")

    try:
        app.register_blueprint(ai_generate_bp)
        print("SUCCESS: ai_generate_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register ai_generate_bp: {e}")
    
    try:
        app.register_blueprint(generate_banner_bp)
        print("SUCCESS: generate_banner_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register generate_banner_bp: {e}")
    
    try:
        app.register_blueprint(generate_video_avatar_bp)
        print("SUCCESS: generate_video_avatar_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register generate_video_avatar_bp: {e}")
    
    # API blueprints
    try:
        app.register_blueprint(landing_content_bp)
        print("SUCCESS: landing_content_bp blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register landing_content_bp: {e}")
    
    try:
        app.register_blueprint(api_routes)
        print("SUCCESS: api_routes blueprint registered")
    except Exception as e:
        print(f"ERROR: Failed to register api_routes: {e}")
    
    print("SUCCESS: Blueprint registration completed")
    
    # Additional routes (only if not already defined in blueprints)
    # Note: The main routes are handled by web_pages blueprint
    
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
                'message': 'All blueprints and routes are active',
                'blueprints': [
                    'web_pages', 'admin', 'animasi', 'explore_api', 'face_swap',
                    'favorite', 'foto', 'fusigaya', 'image_video', 'musik',
                    'profil', 'video', 'generate_banner', 'generate_video_avatar', 
                    'landing_content', 'api_routes'
                ]
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    @app.route('/static/uploads/<filename>')
    def uploaded_file(filename):
        """Serve uploaded files"""
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
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
    
    @app.route('/api/routes-list')
    def routes_list():
        """Daftar semua route yang tersedia dalam aplikasi"""
        try:
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append({
                    'endpoint': rule.endpoint,
                    'methods': list(rule.methods),
                    'rule': str(rule),
                    'blueprint': rule.endpoint.split('.')[0] if '.' in rule.endpoint else 'main'
                })
            
            # Group routes by blueprint
            routes_by_blueprint = {}
            for route in routes:
                blueprint = route['blueprint']
                if blueprint not in routes_by_blueprint:
                    routes_by_blueprint[blueprint] = []
                routes_by_blueprint[blueprint].append(route)
            
            return jsonify({
                'success': True,
                'total_routes': len(routes),
                'routes_by_blueprint': routes_by_blueprint,
                'blueprints': list(routes_by_blueprint.keys())
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    return app

def main():
    """Main function to run the INEMI application with all blueprints"""
    try:
        # Create the application
        app = create_app()
        
        print("=" * 80)
        print("INEMI Application - All Blueprints Active")
        print("=" * 80)
        print("Database: MySQL (inemi)")
        print("Features:")
        print("   • Landing Page with 3D Gallery & Music Player")
        print("   • User Authentication & Profiles")
        print("   • Content Generation (Images, Videos, Music)")
        print("   • Social Features (Likes, Comments, Follows)")
        print("   • Admin Dashboard")
        print("   • Payment & Subscription System")
        print("   • Real-time Notifications")
        print("=" * 80)
        print("Main URLs:")
        print("   • Landing Page: http://localhost:5000")
        print("   • Login: http://localhost:5000/login")
        print("   • Register: http://localhost:5000/register")
        print("   • Home: http://localhost:5000/home")
        print("   • Admin: http://localhost:5000/admin")
        print("   • Health Check: http://localhost:5000/health")
        print("=" * 80)
        print("Content URLs:")
        print("   • Music Gallery: http://localhost:5000#music")
        print("   • 3D Gallery: http://localhost:5000#gallery-3d")
        print("   • Generate Image: http://localhost:5000/generate_image")
        print("   • Generate Video: http://localhost:5000/generate_video")
        print("   • Generate Music: http://localhost:5000/generate_music")
        print("=" * 80)
        print("API Endpoints:")
        print("   • Landing Content: http://localhost:5000/api/landing/*")
        print("   • User API: http://localhost:5000/api/*")
        print("   • Database Info: http://localhost:5000/api/database-info")
        print("   • Routes List: http://localhost:5000/api/routes-list")
        print("=" * 80)
        
        # Test database connection
        with app.app_context():
            try:
                db.session.execute('SELECT 1')
                print("SUCCESS: Database connection successful")
            except Exception as e:
                print(f"ERROR: Database connection failed - {e}")
                print("   Please check your MySQL configuration")
        
        print("=" * 80)
        print("Starting server...")
        print("=" * 80)
        
        # Run the application
        app.run(debug=False, host='0.0.0.0', port=5000)
        
    except Exception as e:
        print(f"ERROR: Error starting application: {e}")
        print("Make sure MySQL database 'inemi' is running and accessible")
        print("Check database connection settings")
        sys.exit(1)

if __name__ == '__main__':
    main()