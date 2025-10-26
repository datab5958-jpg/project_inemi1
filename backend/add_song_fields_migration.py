#!/usr/bin/env python3
"""
Migration script untuk menambahkan field genre dan mode ke tabel songs
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def add_song_fields():
    """Menambahkan field genre dan mode ke tabel songs"""
    with app.app_context():
        try:
            # Cek apakah kolom genre sudah ada
            result = db.session.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'songs' 
                AND COLUMN_NAME = 'genre'
                AND TABLE_SCHEMA = DATABASE()
            """)).fetchone()
            
            if result[0] == 0:
                # Tambahkan kolom genre
                db.session.execute(text("""
                    ALTER TABLE songs 
                    ADD COLUMN genre VARCHAR(100) DEFAULT NULL
                """))
                print("✅ Field 'genre' berhasil ditambahkan")
            else:
                print("ℹ️ Field 'genre' sudah ada")
            
            # Cek apakah kolom mode sudah ada
            result = db.session.execute(text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'songs' 
                AND COLUMN_NAME = 'mode'
                AND TABLE_SCHEMA = DATABASE()
            """)).fetchone()
            
            if result[0] == 0:
                # Tambahkan kolom mode
                db.session.execute(text("""
                    ALTER TABLE songs 
                    ADD COLUMN mode VARCHAR(50) DEFAULT NULL
                """))
                print("✅ Field 'mode' berhasil ditambahkan")
            else:
                print("ℹ️ Field 'mode' sudah ada")
            
            # Commit perubahan
            db.session.commit()
            print("🎉 Migration berhasil diselesaikan!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error saat migration: {e}")
            return False
    
    return True

if __name__ == "__main__":
    add_song_fields()
