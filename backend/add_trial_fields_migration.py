"""
Migration script untuk menambahkan field trial ke tabel users
Menambahkan:
- video_trial_used (BOOLEAN, default False)
- image_to_video_trial_used (BOOLEAN, default False)
- face_swap_trial_used (BOOLEAN, default False)

Jalankan script ini sekali untuk update database.
"""

import sqlite3
import os
import sys
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def migrate_sqlite():
    """Migrate SQLite database"""
    db_path = Path('instance/inemi.db')
    if not db_path.exists():
        print(f"Database tidak ditemukan di {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'video_trial_used' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN video_trial_used BOOLEAN DEFAULT 0 NOT NULL")
            print("[OK] Added video_trial_used column")
        else:
            print("[OK] video_trial_used column already exists")
        
        if 'image_to_video_trial_used' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN image_to_video_trial_used BOOLEAN DEFAULT 0 NOT NULL")
            print("[OK] Added image_to_video_trial_used column")
        else:
            print("[OK] image_to_video_trial_used column already exists")
        
        if 'face_swap_trial_used' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN face_swap_trial_used BOOLEAN DEFAULT 0 NOT NULL")
            print("[OK] Added face_swap_trial_used column")
        else:
            print("[OK] face_swap_trial_used column already exists")
        
        conn.commit()
        conn.close()
        print("\n[SUCCESS] Migration SQLite berhasil!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error migrating SQLite: {e}")
        return False

def migrate_mysql():
    """Generate MySQL migration SQL"""
    sql = """-- Migration untuk menambahkan field trial ke tabel users
-- Jalankan SQL ini di MySQL database

-- Check and add video_trial_used
SET @dbname = DATABASE();
SET @tablename = "users";
SET @columnname = "video_trial_used";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  "SELECT 'Column already exists.'",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " BOOLEAN DEFAULT FALSE NOT NULL")
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Check and add image_to_video_trial_used
SET @columnname = "image_to_video_trial_used";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  "SELECT 'Column already exists.'",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " BOOLEAN DEFAULT FALSE NOT NULL")
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Check and add face_swap_trial_used
SET @columnname = "face_swap_trial_used";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  "SELECT 'Column already exists.'",
  CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " BOOLEAN DEFAULT FALSE NOT NULL")
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;
"""
    
    # Save to file
    os.makedirs('database', exist_ok=True)
    with open('database/migration_add_trial_fields.sql', 'w') as f:
        f.write(sql)
    
    print("[OK] SQL migration file created: database/migration_add_trial_fields.sql")
    print("\nUntuk MySQL, jalankan file SQL tersebut di database Anda.")
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("Migration: Add Trial Fields to Users Table")
    print("=" * 60)
    print()
    
    # Try SQLite first
    if migrate_sqlite():
        print()
    
    # Generate MySQL migration
    migrate_mysql()
    
    print("\n" + "=" * 60)
    print("Migration selesai!")
    print("=" * 60)

