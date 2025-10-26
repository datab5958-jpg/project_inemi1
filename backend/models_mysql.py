from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class SampleImage(db.Model):
    """Model untuk sample images - menggunakan tabel yang sudah ada di MySQL"""
    __tablename__ = 'sample_images'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    created_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_featured = db.Column(db.Boolean, default=False)
    tags = db.Column(db.JSON)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url,
            'category': self.category,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_featured': self.is_featured,
            'tags': self.tags if self.tags else []
        }

class SampleMusic(db.Model):
    """Model untuk sample music - menggunakan tabel yang sudah ada di MySQL"""
    __tablename__ = 'sample_music'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    music_url = db.Column(db.String(500), nullable=False)
    cover_image_url = db.Column(db.String(500))
    genre = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.String(10), nullable=False)  # Format: "3:24"
    created_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_featured = db.Column(db.Boolean, default=False)
    tags = db.Column(db.JSON)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'music_url': self.music_url,
            'cover_image_url': self.cover_image_url,
            'genre': self.genre,
            'duration': self.duration,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_featured': self.is_featured,
            'tags': self.tags if self.tags else []
        }

# Alternative models jika menggunakan tabel yang sudah ada dengan nama berbeda
class GalleryImage(db.Model):
    """Model alternatif untuk gallery images"""
    __tablename__ = 'gallery_images'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    created_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_featured = db.Column(db.Boolean, default=False)
    tags = db.Column(db.JSON)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url,
            'category': self.category,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_featured': self.is_featured,
            'tags': self.tags if self.tags else []
        }

class MusicTrack(db.Model):
    """Model alternatif untuk music tracks"""
    __tablename__ = 'music_tracks'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    music_url = db.Column(db.String(500), nullable=False)
    cover_image_url = db.Column(db.String(500))
    genre = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.String(10), nullable=False)
    created_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_featured = db.Column(db.Boolean, default=False)
    tags = db.Column(db.JSON)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'music_url': self.music_url,
            'cover_image_url': self.cover_image_url,
            'genre': self.genre,
            'duration': self.duration,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_featured': self.is_featured,
            'tags': self.tags if self.tags else []
        }

# Generic model untuk tabel yang sudah ada
class GenericImage(db.Model):
    """Model generik untuk tabel images yang sudah ada"""
    __tablename__ = 'images'  # Ganti dengan nama tabel yang sesuai
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    created_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_featured = db.Column(db.Boolean, default=False)
    tags = db.Column(db.JSON)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url,
            'category': self.category,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_featured': self.is_featured,
            'tags': self.tags if self.tags else []
        }

class GenericMusic(db.Model):
    """Model generik untuk tabel music yang sudah ada"""
    __tablename__ = 'music'  # Ganti dengan nama tabel yang sesuai
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    music_url = db.Column(db.String(500), nullable=False)
    cover_image_url = db.Column(db.String(500))
    genre = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.String(10), nullable=False)
    created_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_featured = db.Column(db.Boolean, default=False)
    tags = db.Column(db.JSON)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'music_url': self.music_url,
            'cover_image_url': self.cover_image_url,
            'genre': self.genre,
            'duration': self.duration,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_featured': self.is_featured,
            'tags': self.tags if self.tags else []
        }
