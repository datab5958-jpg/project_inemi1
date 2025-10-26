from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from config import config
from models_mysql import db, SampleImage, SampleMusic, GalleryImage, MusicTrack, GenericImage, GenericMusic
from api.sample_content_mysql import register_sample_content_api, populate_sample_data

# Load environment variables from .env file
load_dotenv()

def create_app(config_name='default'):
    """Factory function untuk membuat aplikasi Flask dengan MySQL"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Add API Keys to Flask config
    app.config['WAVESPEED_API_KEY'] = os.environ.get('WAVESPEED_API_KEY')
    app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY')
    app.config['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
    app.config['SUNO_API_KEY'] = os.environ.get('SUNO_API_KEY')
    app.config['ELEVENLABS_API_KEY'] = os.environ.get('ELEVENLABS_API_KEY')
    
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
            SampleImage.query.delete()
            SampleMusic.query.delete()
            GalleryImage.query.delete()
            MusicTrack.query.delete()
            GenericImage.query.delete()
            GenericMusic.query.delete()
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
            # Cek semua model
            sample_image_count = SampleImage.query.count()
            sample_music_count = SampleMusic.query.count()
            gallery_image_count = GalleryImage.query.count()
            music_track_count = MusicTrack.query.count()
            generic_image_count = GenericImage.query.count()
            generic_music_count = GenericMusic.query.count()
            
            return jsonify({
                'success': True,
                'data': {
                    'sample_images': sample_image_count,
                    'sample_music': sample_music_count,
                    'gallery_images': gallery_image_count,
                    'music_tracks': music_track_count,
                    'generic_images': generic_image_count,
                    'generic_music': generic_music_count,
                    'total': sample_image_count + sample_music_count + gallery_image_count + music_track_count + generic_image_count + generic_music_count
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/admin/test-connection')
    def test_connection():
        """Route untuk test koneksi database"""
        try:
            # Test koneksi dengan query sederhana
            result = db.session.execute('SELECT 1 as test').fetchone()
            
            return jsonify({
                'success': True,
                'message': 'Database connection successful!',
                'test_result': result[0] if result else None
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    return app

if __name__ == '__main__':
    # Pilih konfigurasi berdasarkan environment
    config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = create_app(config_name)
    
    # Test koneksi database
    with app.app_context():
        try:
            # Test koneksi
            db.session.execute('SELECT 1')
            print("Database connection test successful!")
        except Exception as e:
            print(f"Database connection test failed: {e}")
            print("Please check your MySQL configuration in config.py")
    
    print("Starting INEMI Application with MySQL...")
    print("Database: MySQL")
    print("Features: 3D Animations, Dynamic Loading, MySQL Integration")
    print("URL: http://localhost:5000")
    print("Admin: http://localhost:5000/admin/populate-sample-data")
    print("Status: http://localhost:5000/admin/database-status")
    print("Test: http://localhost:5000/admin/test-connection")
    print("-" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
