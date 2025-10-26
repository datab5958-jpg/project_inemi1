#!/usr/bin/env python3
"""
Script untuk mengupdate data yang sudah ada di database
- Menambahkan kolom view_count jika belum ada
- Mengupdate view_count dengan nilai random
- Menambahkan likes untuk konten
- Mengatur beberapa konten sebagai favorite
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import mysql.connector
from config import Config
from app import app, db
from models import User, Image, Video, Song, Like
from datetime import datetime, timedelta
import random

def add_view_count_columns():
    """Tambah kolom view_count ke database"""
    try:
        # Parse database URL
        db_url = Config.SQLALCHEMY_DATABASE_URI
        if db_url.startswith('mysql://'):
            db_url = db_url.replace('mysql://', '')
        
        # Extract connection details
        if '@' in db_url:
            auth_part, rest = db_url.split('@')
            user, password = auth_part.split(':')
            host_part, database = rest.split('/')
            host = host_part.split(':')[0] if ':' in host_part else host_part
        else:
            print("❌ Invalid database URL format")
            return False
        
        # Connect to database
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        
        cursor = connection.cursor()
        print("✅ Connected to database successfully!")
        
        # Check if view_count column exists in images table
        cursor.execute("SHOW COLUMNS FROM images LIKE 'view_count'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE images ADD COLUMN view_count INT DEFAULT 0")
            print("✅ Added view_count to images table")
        else:
            print("✅ view_count already exists in images table")
        
        # Check if view_count column exists in videos table
        cursor.execute("SHOW COLUMNS FROM videos LIKE 'view_count'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE videos ADD COLUMN view_count INT DEFAULT 0")
            print("✅ Added view_count to videos table")
        else:
            print("✅ view_count already exists in videos table")
        
        # Check if view_count column exists in songs table
        cursor.execute("SHOW COLUMNS FROM songs LIKE 'view_count'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE songs ADD COLUMN view_count INT DEFAULT 0")
            print("✅ Added view_count to songs table")
        else:
            print("✅ view_count already exists in songs table")
        
        # Commit changes
        connection.commit()
        print("✅ All database changes committed successfully!")
        
        # Close connection
        cursor.close()
        connection.close()
        print("✅ Database connection closed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def update_existing_data():
    """Update data yang sudah ada di database"""
    with app.app_context():
        try:
            print("🔄 Mengupdate data yang sudah ada...")
            
            # Get users
            users = User.query.all()
            if not users:
                print("❌ Tidak ada user di database.")
                return False
            
            creator = users[0]
            print(f"✅ Menggunakan user: {creator.username}")
            
            # Update existing images
            images = Image.query.all()
            print(f"📸 Found {len(images)} images")
            
            for i, img in enumerate(images):
                # Update view_count
                img.view_count = random.randint(10, 200)
                
                # Set some as favorite (30% chance)
                if random.random() < 0.3:
                    img.is_favorite = True
                    reasons = [
                        "High quality content",
                        "Popular among users",
                        "Excellent composition",
                        "Viral potential",
                        "Featured content"
                    ]
                    img.whitelist_reason = random.choice(reasons)
                else:
                    img.is_favorite = False
                    img.whitelist_reason = None
                
                # Add some likes
                like_count = random.randint(0, 15)
                for _ in range(like_count):
                    like = Like(
                        user_id=creator.id,
                        content_type='image',
                        content_id=str(img.id)
                    )
                    db.session.add(like)
                
                print(f"   Image {i+1}: {img.view_count} views, {like_count} likes, favorite: {img.is_favorite}")
            
            # Update existing videos
            videos = Video.query.all()
            print(f"🎥 Found {len(videos)} videos")
            
            for i, vid in enumerate(videos):
                # Update view_count
                vid.view_count = random.randint(15, 150)
                
                # Set some as favorite (25% chance)
                if random.random() < 0.25:
                    vid.is_favorite = True
                    reasons = [
                        "Engaging video content",
                        "High watch time",
                        "Quality production",
                        "Trending topic",
                        "User favorite"
                    ]
                    vid.whitelist_reason = random.choice(reasons)
                else:
                    vid.is_favorite = False
                    vid.whitelist_reason = None
                
                # Add some likes
                like_count = random.randint(0, 12)
                for _ in range(like_count):
                    like = Like(
                        user_id=creator.id,
                        content_type='video',
                        content_id=str(vid.id)
                    )
                    db.session.add(like)
                
                print(f"   Video {i+1}: {vid.view_count} views, {like_count} likes, favorite: {vid.is_favorite}")
            
            # Update existing songs
            songs = Song.query.all()
            print(f"🎵 Found {len(songs)} songs")
            
            for i, song in enumerate(songs):
                # Update view_count
                song.view_count = random.randint(5, 100)
                
                # Set some as favorite (20% chance)
                if random.random() < 0.2:
                    song.is_favorite = True
                    reasons = [
                        "Beautiful melody",
                        "Catchy tune",
                        "High quality audio",
                        "Popular genre",
                        "User recommendation"
                    ]
                    song.whitelist_reason = random.choice(reasons)
                else:
                    song.is_favorite = False
                    song.whitelist_reason = None
                
                # Add some likes
                like_count = random.randint(0, 10)
                for _ in range(like_count):
                    like = Like(
                        user_id=creator.id,
                        content_type='song',
                        content_id=str(song.id)
                    )
                    db.session.add(like)
                
                print(f"   Song {i+1}: {song.view_count} views, {like_count} likes, favorite: {song.is_favorite}")
            
            # Commit all changes
            db.session.commit()
            
            print("✅ Data berhasil diupdate!")
            print(f"📊 Statistik setelah update:")
            print(f"   - Images: {Image.query.count()}")
            print(f"   - Videos: {Video.query.count()}")
            print(f"   - Songs: {Song.query.count()}")
            print(f"   - Likes: {Like.query.count()}")
            print(f"   - Favorites: {Image.query.filter_by(is_favorite=True).count() + Video.query.filter_by(is_favorite=True).count() + Song.query.filter_by(is_favorite=True).count()}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()
            return False

def main():
    """Main function"""
    print("🚀 Mengupdate data yang sudah ada di database...")
    print("=" * 50)
    
    # Step 1: Add view_count columns
    print("📋 Step 1: Menambahkan kolom view_count...")
    if add_view_count_columns():
        print("✅ Kolom view_count berhasil ditambahkan!")
    else:
        print("❌ Gagal menambahkan kolom view_count")
        return
    
    print()
    
    # Step 2: Update existing data
    print("📋 Step 2: Mengupdate data yang sudah ada...")
    if update_existing_data():
        print("✅ Data berhasil diupdate!")
    else:
        print("❌ Gagal mengupdate data")
        return
    
    print()
    print("🎉 Database berhasil diupdate!")
    print("🌐 Silakan refresh halaman: http://localhost:5000/admin/favorite-management")

if __name__ == "__main__":
    main()
