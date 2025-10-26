#!/usr/bin/env python3
"""
Script untuk debug data video
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Image, Video

def debug_video_data():
    """Debug data video di database"""
    with app.app_context():
        try:
            print("🔍 Debugging video data...")
            
            # Cek semua user
            users = User.query.all()
            print(f"👥 Total users: {len(users)}")
            
            for user in users:
                print(f"\n👤 User: {user.username} (ID: {user.id})")
                
                # Cek images dengan caption "Image to Video"
                image_videos = Image.query.filter(
                    Image.user_id == user.id,
                    Image.caption.like('Image to Video%')
                ).all()
                print(f"   📸 Images with 'Image to Video' caption: {len(image_videos)}")
                
                # Cek videos di tabel videos
                videos = Video.query.filter(Video.user_id == user.id).all()
                print(f"   🎥 Videos in videos table: {len(videos)}")
                
                if image_videos:
                    print("   📋 Image videos details:")
                    for img in image_videos:
                        print(f"      - ID: {img.id}, Caption: {img.caption}, URL: {img.image_url}")
                
                if videos:
                    print("   📋 Video details:")
                    for vid in videos:
                        print(f"      - ID: {vid.id}, Caption: {vid.caption}, URL: {vid.video_url}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error debugging data: {e}")
            return False

if __name__ == "__main__":
    print("🚀 Debugging video data...")
    debug_video_data()





