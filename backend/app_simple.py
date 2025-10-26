from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os

def create_app():
    """Factory function untuk membuat aplikasi Flask"""
    app = Flask(__name__)
    
    # Konfigurasi
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    
    # Enable CORS untuk API
    CORS(app)
    
    # Import dan register API
    from api.sample_content_simple import register_sample_content_api
    register_sample_content_api(app)
    
    # Routes
    @app.route('/')
    def index():
        """Route utama untuk landing page"""
        return render_template('landing/index.html')
    
    @app.route('/admin/populate-sample-data')
    def admin_populate_data():
        """Route admin untuk mengisi data sample"""
        try:
            return jsonify({
                'success': True,
                'message': 'Sample data is already available! Using static data for demo.'
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
            return jsonify({
                'success': True,
                'message': 'Sample data cleared successfully! (Static data will reload on next request)'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    print("🚀 Starting INEMI Application...")
    print("📊 Database: Static Data (No SQLite required)")
    print("🎨 Features: 3D Animations, Dynamic Loading, API Integration")
    print("🌐 URL: http://localhost:5000")
    print("📝 Admin: http://localhost:5000/admin/populate-sample-data")
    print("-" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
