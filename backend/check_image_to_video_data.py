#!/usr/bin/env python3
"""
Script untuk mengecek data Image to Video yang salah disimpan di tabel images
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Image, Video

def check_image_to_video_data():
    """Cek data Image to Video yang salah disimpan"""
    with app.app_context():
        try:
            print("🔍 Mengecek data Image to Video...")
            
            # Cari semua image yang memiliki caption "Image to Video"
            image_to_video_images = Image.query.filter(
                Image.caption.like('Image to Video%')
            ).all()
            
            print(f"📸 Ditemukan {len(image_to_video_images)} data Image to Video di tabel images")
            
            if image_to_video_images:
                print("\n📋 Detail data yang ditemukan:")
                for i, img in enumerate(image_to_video_images, 1):
                    print(f"   {i}. ID: {img.id}")
                    print(f"      User ID: {img.user_id}")
                    print(f"      Caption: {img.caption}")
                    print(f"      URL: {img.image_url}")
                    print(f"      Created: {img.created_at}")
                    print()
            
            # Cek juga di tabel videos
            video_to_video_videos = Video.query.filter(
                Video.caption.like('Image to Video%')
            ).all()
            
            print(f"🎥 Ditemukan {len(video_to_video_videos)} data Image to Video di tabel videos")
            
            if video_to_video_videos:
                print("\n📋 Detail video yang ditemukan:")
                for i, vid in enumerate(video_to_video_videos, 1):
                    print(f"   {i}. ID: {vid.id}")
                    print(f"      User ID: {vid.user_id}")
                    print(f"      Caption: {vid.caption}")
                    print(f"      URL: {vid.video_url}")
                    print(f"      Created: {vid.created_at}")
                    print()
            
            return len(image_to_video_images), len(video_to_video_videos)
            
        except Exception as e:
            print(f"❌ Error checking data: {e}")
            return 0, 0

if __name__ == "__main__":
    print("🚀 Checking Image to Video data...")
    image_count, video_count = check_image_to_video_data()
    print(f"\n📊 Summary:")
    print(f"   Images with 'Image to Video' caption: {image_count}")
    print(f"   Videos with 'Image to Video' caption: {video_count}")
    
    if image_count > 0:
        print(f"\n⚠️  Found {image_count} Image to Video data in wrong table (images)")
        print("   These need to be migrated to videos table")
    else:
        print("\n✅ No Image to Video data found in images table")





