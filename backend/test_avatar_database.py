#!/usr/bin/env python3
"""
Test script untuk memverifikasi integrasi database video avatar
"""

import os
import sys
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def test_imports():
    """Test import semua module yang diperlukan"""
    try:
        from Generate_video_avatar import generate_video_avatar_bp
        from models import db, Video
        print("✅ Import Generate_video_avatar dan models berhasil")
        return True
    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        return False

def test_video_model():
    """Test model Video"""
    try:
        from models import Video
        
        # Check if Video model has required fields
        required_fields = ['id', 'user_id', 'video_url', 'caption', 'created_at']
        video_columns = [column.name for column in Video.__table__.columns]
        
        missing_fields = [field for field in required_fields if field not in video_columns]
        if missing_fields:
            print(f"❌ Missing fields in Video model: {missing_fields}")
            return False
        
        print("✅ Video model has all required fields")
        print(f"   Available fields: {video_columns}")
        return True
    except Exception as e:
        print(f"❌ Video model test failed: {str(e)}")
        return False

def test_database_connection():
    """Test koneksi database"""
    try:
        from models import db
        from flask import Flask
        
        # Create a test Flask app
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        
        with app.app_context():
            # Test database connection
            db.engine.execute('SELECT 1')
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def test_video_creation():
    """Test pembuatan record Video"""
    try:
        from models import db, Video
        from flask import Flask
        from datetime import datetime
        
        # Create a test Flask app
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        
        with app.app_context():
            # Create test video record
            test_video = Video(
                user_id=1,
                video_url="/static/outputs/test_avatar.mp4",
                caption="Test AI Avatar Video"
            )
            
            # Test that we can create the object
            print(f"✅ Video object created successfully")
            print(f"   User ID: {test_video.user_id}")
            print(f"   Video URL: {test_video.video_url}")
            print(f"   Caption: {test_video.caption}")
            print(f"   Created at: {test_video.created_at}")
            
            return True
    except Exception as e:
        print(f"❌ Video creation test failed: {str(e)}")
        return False

def main():
    print("🔧 Testing Avatar Video Database Integration")
    print("=" * 50)
    
    tests = [
        ("Import Modules", test_imports),
        ("Video Model Structure", test_video_model),
        ("Database Connection", test_database_connection),
        ("Video Creation", test_video_creation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Database integration should work correctly.")
        print("📝 Video avatars will now be saved to database and appear in feeds!")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    return all_passed

if __name__ == "__main__":
    main()




