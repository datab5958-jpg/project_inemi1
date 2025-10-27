from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from models import db, SampleImage, SampleMusic
from api.sample_content_db import register_sample_content_api, populate_sample_data

# Load environment variables from .env file
load_dotenv()

def create_app():
    """Factory function untuk membuat aplikasi Flask"""
    app = Flask(__name__)
    
    # Konfigurasi
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inemi_sample_content.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
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
    
    # Enable CORS untuk API
    CORS(app)
    
    # Inisialisasi database
    db.init_app(app)
    
    # Register API blueprints
    register_sample_content_api(app, db)
    
    # Routes
    @app.route('/')
    def index():
        """Route utama untuk landing page"""
        return render_template('landing/index.html')
    
    @app.route('/admin/populate-sample-data')
    def admin_populate_data():
        """Route admin untuk mengisi data sample"""
        try:
            populate_sample_data()
            return jsonify({
                'success': True,
                'message': 'Sample data populated successfully!'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/admin/clear-sample-data')
    def admin_clear_data():
        """Route admin untuk menghapus data sample"""
        try:
            # Hapus semua data sample
            db.session.query(SampleImage).delete()
            db.session.query(SampleMusic).delete()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Sample data cleared successfully!'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/admin/database-status')
    def database_status():
        """Route untuk mengecek status database"""
        try:
            image_count = SampleImage.query.count()
            music_count = SampleMusic.query.count()
            
            return jsonify({
                'success': True,
                'data': {
                    'images': image_count,
                    'music': music_count,
                    'total': image_count + music_count
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
    
    # Buat tabel jika belum ada
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {e}")
    
    print("🚀 Starting INEMI Application...")
    print("📊 Database: SQLite (inemi_sample_content.db)")
    print("🎨 Features: 3D Animations, Dynamic Loading, Database Integration")
    print("🌐 URL: http://localhost:5000")
    print("📝 Admin: http://localhost:5000/admin/populate-sample-data")
    print("📊 Status: http://localhost:5000/admin/database-status")
    print("-" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
