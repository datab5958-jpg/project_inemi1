#!/usr/bin/env python3
"""
Script untuk membuat tabel orders dan payments
"""

from app import app
from models import db

def create_tables():
    """Membuat tabel orders dan payments"""
    with app.app_context():
        try:
            print("🔄 Membuat tabel orders dan payments...")
            
            # Create all tables
            db.create_all()
            print("✅ Tabel berhasil dibuat")
            
            # Verify tables exist
            result = db.engine.execute("SHOW TABLES LIKE 'orders'")
            if result.fetchone():
                print("✅ Tabel orders berhasil dibuat")
            else:
                print("❌ Tabel orders gagal dibuat")
                
            result = db.engine.execute("SHOW TABLES LIKE 'payments'")
            if result.fetchone():
                print("✅ Tabel payments berhasil dibuat")
            else:
                print("❌ Tabel payments gagal dibuat")
                
        except Exception as e:
            print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    create_tables()
