#!/usr/bin/env python3
"""
Script to create an admin user or modify existing user to admin role
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def create_admin_user(username, email, password):
    """Create a new admin user"""
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"User '{username}' already exists. Updating role to admin...")
            existing_user.role = 'admin'
            db.session.commit()
            print(f"User '{username}' role updated to admin successfully!")
            return existing_user
        
        # Create new admin user
        admin_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role='admin',
            kredit=1000,
            avatar_url='/static/assets/image/default.jpg'
        )
        
        db.session.add(admin_user)
        db.session.commit()
        print(f"Admin user '{username}' created successfully!")
        return admin_user

def list_users():
    """List all users with their roles"""
    with app.app_context():
        users = User.query.all()
        print("\nCurrent users in database:")
        print("-" * 60)
        print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Role':<10}")
        print("-" * 60)
        for user in users:
            print(f"{user.id:<5} {user.username:<20} {user.email:<30} {user.role:<10}")
        print("-" * 60)

def make_user_admin(username):
    """Make an existing user an admin"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"User '{username}' not found!")
            return False
        
        user.role = 'admin'
        db.session.commit()
        print(f"User '{username}' role updated to admin successfully!")
        return True

if __name__ == "__main__":
    print("INEMI Admin User Management")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Create new admin user")
        print("2. Make existing user admin")
        print("3. List all users")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            username = input("Enter username: ").strip()
            email = input("Enter email: ").strip()
            password = input("Enter password: ").strip()
            
            if username and email and password:
                create_admin_user(username, email, password)
            else:
                print("All fields are required!")
        
        elif choice == "2":
            username = input("Enter username to make admin: ").strip()
            if username:
                make_user_admin(username)
            else:
                print("Username is required!")
        
        elif choice == "3":
            list_users()
        
        elif choice == "4":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice! Please enter 1-4.")








