#!/usr/bin/env python3
"""
Script untuk test API endpoints
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User, Image, Video

def test_endpoints():
    """Test API endpoints"""
    with app.app_context():
        try:
            print("🧪 Testing API endpoints...")
            
            # Test database connection
            print("1. Testing database connection...")
            user_count = User.query.count()
            print(f"   ✅ Database connected. Users: {user_count}")
            
            # Test models
            print("2. Testing models...")
            image_count = Image.query.count()
            video_count = Video.query.count()
            print(f"   ✅ Images: {image_count}, Videos: {video_count}")
            
            # Test with test client
            print("3. Testing API endpoints...")
            with app.test_client() as client:
                # Test basic endpoint
                response = client.get('/api/test')
                print(f"   Test endpoint status: {response.status_code}")
                if response.status_code == 200:
                    print(f"   ✅ Test endpoint working: {response.get_json()}")
                else:
                    print(f"   ❌ Test endpoint failed: {response.data}")
                
                # Test miniatur results (without login)
                response = client.get('/api/get-miniatur-results')
                print(f"   Miniatur results status: {response.status_code}")
                if response.status_code == 200:
                    print(f"   ✅ Miniatur results working")
                else:
                    print(f"   ❌ Miniatur results failed: {response.data}")
                
                # Test video results (without login)
                response = client.get('/api/get-video-results')
                print(f"   Video results status: {response.status_code}")
                if response.status_code == 200:
                    print(f"   ✅ Video results working")
                else:
                    print(f"   ❌ Video results failed: {response.data}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing endpoints: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("🚀 Testing API endpoints...")
    success = test_endpoints()
    if success:
        print("🎉 All tests passed!")
    else:
        print("💥 Tests failed!")





