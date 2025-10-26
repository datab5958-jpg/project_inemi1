import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # MySQL Configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or 3306)
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or ''
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE') or 'inemi'
    
    # SQLAlchemy URI for MySQL
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}'
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # CORS configuration
    CORS_ORIGINS = ['*']
    
    # Pagination
    POSTS_PER_PAGE = 10
    IMAGES_PER_PAGE = 8
    MUSIC_PER_PAGE = 6
    
    # API Keys
    SUNO_API_KEY = os.environ.get('SUNO_API_KEY') or 'your-suno-api-key'
    SUNO_BASE_URL = os.environ.get('SUNO_BASE_URL') or 'https://api.suno.ai'
    CALLBACK_DOMAIN = os.environ.get('CALLBACK_DOMAIN') or 'http://localhost:5000'
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or 'your-gemini-api-key'
    GEMINI_API_URL = os.environ.get('GEMINI_API_URL') or 'https://generativelanguage.googleapis.com'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or 'your-openai-api-key'
    WAVESPEED_API_KEY = os.environ.get('WAVESPEED_API_KEY') or 'your-wavespeed-api-key'
    ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY') or 'your-elevenlabs-api-key'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}