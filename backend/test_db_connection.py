#!/usr/bin/env python3
"""
Test database connection script
"""

from app import app
from models import db

def test_database_connection():
    """Test database connection"""
    try:
        with app.app_context():
            # Test database connection using SQLAlchemy 2.0+ syntax
            with db.engine.connect() as connection:
                result = connection.execute(db.text('SELECT 1'))
                print("Database connection successful")
            return True
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return False

def test_user_table():
    """Test if User table exists and can be queried"""
    try:
        with app.app_context():
            from models import User
            user_count = User.query.count()
            print(f"User table accessible, found {user_count} users")
            return True
    except Exception as e:
        print(f"User table test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Testing Database Connection ===")
    print(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    
    # Test connection
    connection_ok = test_database_connection()
    
    if connection_ok:
        # Test User table
        test_user_table()
    
    print("=== Test Complete ===")
