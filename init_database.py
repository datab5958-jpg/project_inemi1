#!/usr/bin/env python3
"""
Database Initialization Script
Run this to initialize the database with sample data
"""

import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app_db import create_app
from models import db, SampleImage, SampleMusic
from api.sample_content_db import populate_sample_data

def init_database():
    """Initialize database with sample data"""
    app = create_app()
    
    with app.app_context():
        try:
            # Create tables
            db.create_all()
            print("Database tables created successfully!")
            
            # Check if data already exists
            image_count = SampleImage.query.count()
            music_count = SampleMusic.query.count()
            
            if image_count == 0 and music_count == 0:
                print("Populating database with sample data...")
                populate_sample_data()
                print("Sample data populated successfully!")
            else:
                print(f"Database already contains {image_count} images and {music_count} music tracks")
            
            # Show final status
            final_image_count = SampleImage.query.count()
            final_music_count = SampleMusic.query.count()
            
            print(f"Final Status:")
            print(f"   - Images: {final_image_count}")
            print(f"   - Music: {final_music_count}")
            print(f"   - Total: {final_image_count + final_music_count}")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            return False
    
    return True

if __name__ == '__main__':
    print("Starting INEMI Database Initialization...")
    print("Database: SQLite (inemi_sample_content.db)")
    print("-" * 50)
    
    success = init_database()
    
    if success:
        print("-" * 50)
        print("Database initialization completed!")
        print("You can now run: python run_app.py")
    else:
        print("-" * 50)
        print("Database initialization failed!")
        print("Please check the error messages above")
