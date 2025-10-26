#!/usr/bin/env python3
"""
MySQL Database Initialization Script
Run this to initialize the MySQL database with sample data
"""

import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app_mysql import create_app
from models_mysql import db, SampleImage, SampleMusic, GalleryImage, MusicTrack, GenericImage, GenericMusic
from api.sample_content_mysql import populate_sample_data

def init_mysql_database():
    """Initialize MySQL database with sample data"""
    app = create_app()
    
    with app.app_context():
        try:
            # Test koneksi database
            print("Testing MySQL connection...")
            db.session.execute('SELECT 1')
            print("MySQL connection successful!")
            
            # Create tables (jika belum ada)
            print("Creating database tables...")
            db.create_all()
            print("Database tables created successfully!")
            
            # Check existing data
            print("Checking existing data...")
            sample_image_count = SampleImage.query.count()
            sample_music_count = SampleMusic.query.count()
            gallery_image_count = GalleryImage.query.count()
            music_track_count = MusicTrack.query.count()
            generic_image_count = GenericImage.query.count()
            generic_music_count = GenericMusic.query.count()
            
            total_existing = sample_image_count + sample_music_count + gallery_image_count + music_track_count + generic_image_count + generic_music_count
            
            print(f"Existing data found:")
            print(f"   - Sample Images: {sample_image_count}")
            print(f"   - Sample Music: {sample_music_count}")
            print(f"   - Gallery Images: {gallery_image_count}")
            print(f"   - Music Tracks: {music_track_count}")
            print(f"   - Generic Images: {generic_image_count}")
            print(f"   - Generic Music: {generic_music_count}")
            print(f"   - Total: {total_existing}")
            
            if total_existing == 0:
                print("No existing data found. Populating with sample data...")
                populate_sample_data()
                print("Sample data populated successfully!")
            else:
                print("Database already contains data. Skipping population.")
            
            # Show final status
            print("\nFinal Status:")
            final_sample_image_count = SampleImage.query.count()
            final_sample_music_count = SampleMusic.query.count()
            final_gallery_image_count = GalleryImage.query.count()
            final_music_track_count = MusicTrack.query.count()
            final_generic_image_count = GenericImage.query.count()
            final_generic_music_count = GenericMusic.query.count()
            
            print(f"   - Sample Images: {final_sample_image_count}")
            print(f"   - Sample Music: {final_sample_music_count}")
            print(f"   - Gallery Images: {final_gallery_image_count}")
            print(f"   - Music Tracks: {final_music_track_count}")
            print(f"   - Generic Images: {final_generic_image_count}")
            print(f"   - Generic Music: {final_generic_music_count}")
            print(f"   - Total: {final_sample_image_count + final_sample_music_count + final_gallery_image_count + final_music_track_count + final_generic_image_count + final_generic_music_count}")
            
        except Exception as e:
            print(f"Error initializing MySQL database: {e}")
            print("\nTroubleshooting:")
            print("1. Check if MySQL server is running")
            print("2. Verify database credentials in backend/config.py")
            print("3. Ensure database exists")
            print("4. Check if PyMySQL is installed: pip install PyMySQL")
            return False
    
    return True

if __name__ == '__main__':
    print("Starting INEMI MySQL Database Initialization...")
    print("Database: MySQL")
    print("-" * 50)
    
    success = init_mysql_database()
    
    if success:
        print("-" * 50)
        print("MySQL database initialization completed!")
        print("You can now run: python run_mysql_app.py")
    else:
        print("-" * 50)
        print("MySQL database initialization failed!")
        print("Please check the error messages above")
