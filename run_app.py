#!/usr/bin/env python3
"""
INEMI Application Runner
Run this file to start the Flask application with database integration
"""

import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app_db import create_app

if __name__ == '__main__':
    print("🚀 Starting INEMI Application...")
    print("📊 Database: SQLite (inemi_sample_content.db)")
    print("🎨 Features: 3D Animations, Dynamic Loading, Database Integration")
    print("🌐 URL: http://localhost:5000")
    print("📝 Admin: http://localhost:5000/admin/populate-sample-data")
    print("📊 Status: http://localhost:5000/admin/database-status")
    print("-" * 50)
    
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
