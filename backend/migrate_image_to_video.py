#!/usr/bin/env python3
"""
Script untuk memindahkan data Image to Video yang salah disimpan di tabel images ke tabel videos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Image, Video
from datetime import datetime

def migrate_image_to_video_data():
    """Memindahkan data Image to Video dari tabel images ke tabel videos"""
    with app.app_context():
        try:
            print("🔄 Memulai migrasi data Image to Video...")
            
            # Cari semua image yang memiliki caption "Image to Video"
            image_to_video_images = Image.query.filter(
                Image.caption.like('Image to Video%')
            ).all()
            
            print(f"📸 Ditemukan {len(image_to_video_images)} data Image to Video di tabel images")
            
            migrated_count = 0
            for img in image_to_video_images:
                try:
                    # Buat record video baru
                    video = Video(
                        user_id=img.user_id,
                        video_url=img.image_url,  # URL video disimpan di image_url
                        caption=img.caption,
                        is_favorite=img.is_favorite,
                        whitelist_reason=img.whitelist_reason,
                        view_count=img.view_count,
                        created_at=img.created_at,
                        updated_at=img.updated_at
                    )
                    
                    # Simpan video
                    db.session.add(video)
                    db.session.flush()  # Flush untuk mendapatkan ID
                    
                    # Hapus image yang salah
                    db.session.delete(img)
                    
                    migrated_count += 1
                    print(f"   ✅ Migrated: {img.caption} (ID: {img.id} -> Video ID: {video.id})")
                    
                except Exception as e:
                    print(f"   ❌ Error migrating image ID {img.id}: {e}")
                    db.session.rollback()
                    continue
            
            # Commit semua perubahan
            db.session.commit()
            print(f"✅ Berhasil memigrasi {migrated_count} data Image to Video ke tabel videos")
            
            # Verifikasi hasil
            video_count = Video.query.filter(
                Video.caption.like('Image to Video%')
            ).count()
            print(f"📊 Total video Image to Video di tabel videos: {video_count}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("🚀 Starting Image to Video data migration...")
    success = migrate_image_to_video_data()
    if success:
        print("🎉 Migration completed successfully!")
    else:
        print("💥 Migration failed!")





