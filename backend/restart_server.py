#!/usr/bin/env python3
"""
Script untuk restart server dan test endpoints
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test semua import"""
    try:
        print("🧪 Testing imports...")
        
        # Test basic imports
        from flask import Flask
        print("   ✅ Flask imported")
        
        from models import db, User, Image, Video, Notification
        print("   ✅ Models imported")
        
        from web.animasi import animasi_bp
        print("   ✅ Animasi blueprint imported")
        
        from app import app
        print("   ✅ App imported")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_app_creation():
    """Test app creation"""
    try:
        print("🧪 Testing app creation...")
        
        from app import app
        print(f"   ✅ App created: {app}")
        print(f"   ✅ App name: {app.name}")
        print(f"   ✅ App config: {app.config.get('SECRET_KEY', 'No secret key')}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ App creation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database connection"""
    try:
        print("🧪 Testing database...")
        
        from app import app
        from models import db, User
        
        with app.app_context():
            user_count = User.query.count()
            print(f"   ✅ Database connected. Users: {user_count}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Testing server components...")
    
    success = True
    success &= test_imports()
    success &= test_app_creation()
    success &= test_database()
    
    if success:
        print("🎉 All tests passed! Server should work now.")
        print("\n📝 To start server:")
        print("   cd backend && python app.py")
    else:
        print("💥 Tests failed! Check errors above.")





