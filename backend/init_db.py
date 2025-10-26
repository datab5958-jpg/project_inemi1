#!/usr/bin/env python3
"""
Database initialization script for video_gabung
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User, VideoIklan, Product

def init_database():
    """Initialize the database with required tables and default data"""
    
    with app.app_context():
        print("=== Initializing Database ===")
        
        # Create all tables
        try:
            db.create_all()
            print("✓ Database tables created successfully")
        except Exception as e:
            print(f"✗ Error creating tables: {e}")
            return False
        
        # Check if default user exists
        default_user = User.query.filter_by(username='default_user').first()
        if not default_user:
            try:
                default_user = User(
                    username='default_user',
                    email='default@example.com',
                    kredit=1000
                )
                default_user.set_password('default_password')  # Use set_password method
                db.session.add(default_user)
                db.session.commit()
                print(f"✓ Created default user with ID: {default_user.id}")
            except Exception as e:
                print(f"✗ Error creating default user: {e}")
                return False
        else:
            print(f"✓ Default user already exists with ID: {default_user.id}")
        
        # Check if there are any existing videos
        video_count = VideoIklan.query.count()
        print(f"✓ Found {video_count} existing videos in database")
        
        print("=== Database initialization completed ===")
        return True

if __name__ == "__main__":
    success = init_database()
    if success:
        print("Database initialization successful!")
    else:
        print("Database initialization failed!")
        sys.exit(1) 