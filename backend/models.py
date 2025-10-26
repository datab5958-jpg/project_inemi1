from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Image(db.Model):
    """Model untuk tabel images yang sudah ada di database"""
    __tablename__ = 'images'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_url = db.Column(db.Text, nullable=False)  # Changed to Text to match database
    caption = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_favorite = db.Column(db.Boolean, default=False)
    whitelist_reason = db.Column(db.Text)  # Added missing column
    view_count = db.Column(db.Integer, default=0)
    
    # Relationship
    user = db.relationship('User', backref='images')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'caption': self.caption,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_favorite': self.is_favorite,
            'whitelist_reason': self.whitelist_reason,
            'view_count': self.view_count,
            'user': {
                'id': self.user.id if self.user else None,
                'username': self.user.username if self.user else 'Anonymous',
                'avatar_url': self.user.avatar_url if self.user else '/static/assets/image/default.jpg'
            } if self.user else None
        }

class Video(db.Model):
    """Model untuk tabel videos yang sudah ada di database"""
    __tablename__ = 'videos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    video_url = db.Column(db.Text, nullable=False)
    caption = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_favorite = db.Column(db.Boolean, default=False)
    whitelist_reason = db.Column(db.Text)
    view_count = db.Column(db.Integer, default=0)
    
    # Relationship
    user = db.relationship('User', backref='videos')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'caption': self.caption,
            'video_url': self.video_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_favorite': self.is_favorite,
            'whitelist_reason': self.whitelist_reason,
            'view_count': self.view_count,
            'user': {
                'id': self.user.id if self.user else None,
                'username': self.user.username if self.user else 'Anonymous',
                'avatar_url': self.user.avatar_url if self.user else '/static/assets/image/default.jpg'
            } if self.user else None
        }

class Song(db.Model):
    """Model untuk tabel songs yang sudah ada di database"""
    __tablename__ = 'songs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200))
    prompt = db.Column(db.Text)
    model_name = db.Column(db.String(100))
    duration = db.Column(db.Float)  # Duration in seconds
    image_url = db.Column(db.String(500))
    audio_url = db.Column(db.String(500))
    stream_audio_url = db.Column(db.String(500))
    source_audio_url = db.Column(db.String(500))
    source_image_url = db.Column(db.String(500))
    source_stream_audio_url = db.Column(db.String(500))
    lyrics = db.Column(db.Text)
    artist = db.Column(db.String(200))
    is_favorite = db.Column(db.Boolean, default=False)
    whitelist_reason = db.Column(db.Text)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    genre = db.Column(db.String(50))
    mode = db.Column(db.String(50))
    
    # Relationship
    user = db.relationship('User', backref='songs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'prompt': self.prompt,
            'model_name': self.model_name,
            'duration': self.duration,
            'image_url': self.image_url,
            'audio_url': self.audio_url,
            'stream_audio_url': self.stream_audio_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'artist': self.artist,
            'is_favorite': self.is_favorite,
            'view_count': self.view_count,
            'genre': self.genre,
            'mode': self.mode,
            'user': {
                'id': self.user.id if self.user else None,
                'username': self.user.username if self.user else 'Anonymous',
                'avatar_url': self.user.avatar_url if self.user else '/static/assets/image/default.jpg'
            } if self.user else None
        }

class User(db.Model):
    """Model untuk tabel users yang sudah ada di database"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)  # Changed from 80 to 50
    email = db.Column(db.String(100))  # Changed from 120 to 100, removed unique constraint
    password = db.Column(db.String(255))  # Changed from password_hash to password
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.Text)  # Changed from String(500) to Text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.Enum('free', 'premium', 'premier', 'admin'), default='free')  # Changed to Enum
    kredit = db.Column(db.Integer, nullable=False)  # Removed default, made nullable=False
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'avatar_url': self.avatar_url,
            'role': self.role,
            'kredit': self.kredit,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'bio': self.bio
        }
    
    def set_password(self, password):
        """Set password hash"""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password, password)

class Message(db.Model):
    """Model untuk tabel messages"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

class Like(db.Model):
    """Model untuk tabel likes"""
    __tablename__ = 'likes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_type = db.Column(db.String(20), nullable=False)  # 'image', 'video', 'song'
    content_id = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='likes')

class Comment(db.Model):
    """Model untuk tabel comments"""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_type = db.Column(db.String(20), nullable=False)  # 'image', 'video', 'song'
    content_id = db.Column(db.String(50), nullable=False)
    text = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='comments')
    parent = db.relationship('Comment', remote_side=[id], backref='replies')

class Follow(db.Model):
    """Model untuk tabel follows"""
    __tablename__ = 'follows'
    
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    following_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    follower = db.relationship('User', foreign_keys=[follower_id], backref='following')
    following = db.relationship('User', foreign_keys=[following_id], backref='followers')

class VideoIklan(db.Model):
    """Model untuk tabel videos_iklan"""
    __tablename__ = 'videos_iklan'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    video_url = db.Column(db.LargeBinary)  # longblob in MySQL
    caption = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    video_data = db.Column(db.LargeBinary)  # Additional video_data column
    
    # Relationship
    user = db.relationship('User', backref='videos_iklan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'caption': self.caption,
            'video_url': self.video_url.decode('utf-8') if self.video_url else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user': {
                'id': self.user.id if self.user else None,
                'username': self.user.username if self.user else 'Anonymous',
                'avatar_url': self.user.avatar_url if self.user else '/static/assets/image/default.jpg'
            } if self.user else None
        }

class ModerationAction(db.Model):
    """Model untuk tabel moderation_actions"""
    __tablename__ = 'moderation_actions'
    
    id = db.Column(db.Integer, primary_key=True)
    content_type = db.Column(db.Enum('video', 'image', 'song', 'video_iklan'), nullable=False)
    content_id = db.Column(db.String(50), nullable=False)
    action = db.Column(db.Enum('deactivate', 'report'), nullable=False)
    reason = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Product(db.Model):
    """Model untuk tabel products"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    kredit = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    """Model untuk tabel orders"""
    __tablename__ = 'orders'
    
    order_id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='orders')
    product = db.relationship('Product', backref='orders')

class Payment(db.Model):
    """Model untuk tabel payments"""
    __tablename__ = 'payments'
    
    payment_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.order_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50))
    proof_image = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')
    verified_by = db.Column(db.String(50))
    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    order = db.relationship('Order', backref='payments')

class Notification(db.Model):
    """Model untuk tabel notifications"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # 'like', 'comment', 'follow', etc.
    content_type = db.Column(db.String(20))  # 'image', 'video', 'song'
    content_id = db.Column(db.String(50))
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    text = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_notifications')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_notifications')
    comment = db.relationship('Comment', backref='notifications')

class ViewCount(db.Model):
    """Model untuk tracking view counts"""
    __tablename__ = 'view_counts'
    
    id = db.Column(db.Integer, primary_key=True)
    content_type = db.Column(db.String(20), nullable=False)  # 'image', 'video', 'song'
    content_id = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip_address = db.Column(db.String(45))  # IPv6 support
    user_agent = db.Column(db.Text)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='view_counts')

class Prompt(db.Model):
    """Model untuk menyimpan AI prompts"""
    __tablename__ = 'prompts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(200))
    action = db.Column(db.String(200))
    expression = db.Column(db.String(200))
    style = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='prompts')

# Legacy models for backward compatibility
class SampleImage(db.Model):
    __tablename__ = 'sample_images'
    
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
            'created_at': self.created_at.isoformat(),
            'is_featured': self.is_featured,
            'tags': self.tags or []
        }

class SampleMusic(db.Model):
    __tablename__ = 'sample_music'
    
    id = db.Column(db.Integer, primary_key=True)
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
            'created_at': self.created_at.isoformat(),
            'is_featured': self.is_featured,
            'tags': self.tags or []
        }