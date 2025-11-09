from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from models import db, Image, Video, User, Message, Song, Like, Comment, VideoIklan, Follow, ModerationAction, Product, Order, Payment
from sqlalchemy import or_
from .utils import get_width_height
import os
import uuid
import requests
from sqlalchemy.sql.expression import func
from datetime import datetime
import re
import time
from urllib.parse import urlparse

web_pages = Blueprint('web_pages', __name__)

os.environ["REPLICATE_API_TOKEN"] = "r8_cw6SUS8zayL2jZIUvNLKCrvYZGY4XA32PSSDx"

# Configuration for file uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_text(text):
    import re
    return re.sub(r'<[^>]+>', '', text) if text else text

@web_pages.route('/')
def index():
    # Tampilkan halaman landing INEMI AI yang baru
    return render_template('landing/index.html')

@web_pages.route('/health')
def health_check():
    """Simple health check endpoint"""
    try:
        from models import Image, Video, Song, User
        # Test database connection
        image_count = Image.query.count()
        video_count = Video.query.count()
        song_count = Song.query.count()
        user_count = User.query.count()
        
        return jsonify({
            'status': 'healthy',
            'database': {
                'images': image_count,
                'videos': video_count,
                'songs': song_count,
                'users': user_count
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@web_pages.route('/api/images/latest')
def api_images_latest():
    try:
        images = Image.query.order_by(Image.created_at.desc()).limit(6).all()
        items = []
        for image in images:
            user = User.query.get(image.user_id) if image.user_id else None
            # Validate image URL
            image_url = image.image_url if image.image_url and image.image_url.startswith('http') else None
            items.append({
                'id': image.id,
                'type': 'image',
                'url': image_url or 'https://via.placeholder.com/400x300/6366f1/ffffff?text=Sample+Image',
                'title': image.caption or 'Untitled Image',
                'user': user.username if user else 'Anonymous',
                'created_at': image.created_at.isoformat() if image.created_at else None
            })
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        # Return empty array if database error
        return jsonify({'success': True, 'items': []})

@web_pages.route('/api/example_images')
def api_example_images():
    """API endpoint untuk mengambil contoh gambar dari database untuk halaman generate_image"""
    try:
        # Ambil 10 gambar terbaru dari database yang valid
        images = Image.query.filter(
            Image.image_url.isnot(None),
            Image.image_url != '',
            Image.image_url.like('http%')  # Hanya URL yang valid
        ).order_by(Image.created_at.desc()).limit(10).all()
        
        images_data = []
        for image in images:
            # Validasi URL gambar
            if image.image_url and image.image_url.startswith('http'):
                images_data.append({
                    'id': image.id,
                    'url': image.image_url,
                    'caption': image.caption or 'Generated Image',
                    'created_at': image.created_at.isoformat() if image.created_at else None
                })
        
        return jsonify({
            'success': True,
            'images': images_data,
            'source': 'database',
            'count': len(images_data)
        })
        
    except Exception as e:
        print(f"Error in api_example_images: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'images': [],
            'source': 'error'
        }), 500

@web_pages.route('/api/search/infinite')
def api_search_infinite():
    """API endpoint untuk infinite scroll di halaman search"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        offset = (page - 1) * per_page
        
        # Query semua gambar dengan pagination
        images = Image.query.order_by(Image.created_at.desc()).offset(offset).limit(per_page).all()
        
        items = []
        for image in images:
            user = User.query.get(image.user_id) if image.user_id else None
            items.append({
                'id': image.id,
                'type': 'image',
                'url': image.image_url,
                'title': image.caption or 'Untitled Image',
                'user': {
                    'username': user.username if user else 'Anonymous',
                    'avatar_url': user.avatar_url if user else '/static/assets/image/default.jpg'
                },
                'created_at': image.created_at.isoformat() if image.created_at else None
            })
        
        # Check if there are more items
        total_count = Image.query.count()
        has_more = (offset + per_page) < total_count
        
        return jsonify({
            'success': True, 
            'items': items,
            'has_more': has_more,
            'page': page,
            'total': total_count
        })
        
    except Exception as e:
        print(f"Error in api_search_infinite: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@web_pages.route('/api/videos/latest')
def api_videos_latest():
    try:
        videos = Video.query.order_by(Video.created_at.desc()).limit(6).all()
        items = []
        for video in videos:
            user = User.query.get(video.user_id) if video.user_id else None
            # Validate video URL
            video_url = video.video_url if video.video_url and video.video_url.startswith('https') else None
            items.append({
                'id': video.id,
                'type': 'video',
                'url': video_url or 'https://via.placeholder.com/400x300/06b6d4/ffffff?text=Sample+Video',
                'title': video.caption or 'Untitled Video',
                'user': user.username if user else 'Anonymous',
                'created_at': video.created_at.isoformat() if video.created_at else None
            })
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        # Return empty array if database error
        return jsonify({'success': True, 'items': []})

@web_pages.route('/api/songs/latest')
def api_songs_latest():
    try:
        songs = Song.query.order_by(Song.created_at.desc()).limit(6).all()
        items = []
        for song in songs:
            user = User.query.get(song.user_id) if song.user_id else None
            # Validate URLs
            audio_url = song.audio_url if song.audio_url and song.audio_url.startswith('http') else None
            image_url = song.image_url if song.image_url and song.image_url.startswith('http') else None
            items.append({
                'id': song.id,
                'type': 'music',
                'audio_url': audio_url or '#',
                'image_url': image_url or 'https://via.placeholder.com/400x300/10b981/ffffff?text=Music+Cover',
                'title': song.title or 'Untitled Song',
                'user': user.username if user else 'Anonymous',
                'duration': song.duration or '0:00',
                'created_at': song.created_at.isoformat() if song.created_at else None
            })
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        # Return empty array if database error
        return jsonify({'success': True, 'items': []})

@web_pages.route('/chat', methods=['GET', 'POST'])
def chat_page():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    user_id = session['user_id']
    search_query = request.args.get('q', '').strip()

    # Cari user yang pernah chat (baik sebagai pengirim atau penerima)
    chat_user_ids = db.session.query(Message.sender_id).filter(Message.receiver_id == user_id).union(
        db.session.query(Message.receiver_id).filter(Message.sender_id == user_id)
    ).distinct().all()
    chat_user_ids = set([uid for (uid,) in chat_user_ids if uid != user_id])

    chat_users = User.query.filter(User.id.in_(chat_user_ids)).all() if chat_user_ids else []

    # Fitur pencarian user
    found_users = []
    if search_query:
        found_users = User.query.filter(User.username.ilike(f"%{search_query}%"), User.id != user_id).all()

    return render_template('chat.html', chat_users=chat_users, found_users=found_users, search_query=search_query)

@web_pages.route('/ai_data')
def ai_data():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    return render_template('ai_data.html')

@web_pages.route('/ai_photo')
def ai_photo():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    return render_template('ai_photo.html')

@web_pages.route('/search')
def search():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    query = request.args.get('q', '').strip()
    
    found_users = []
    if query:
        found_users = User.query.filter(User.username.ilike(f"%{query}%")).all()

    # Load initial 20 images untuk infinite scroll
    images = Image.query.order_by(Image.created_at.desc()).limit(20).all()
    
    return render_template('cari.html', 
                         found_users=found_users, 
                         search_query=query, 
                         images=images)

@web_pages.route('/landing')
def landing():
    # Tampilkan halaman landing Inemi yang baru
    return render_template('landing/index.html')

@web_pages.route('/test')
def test():
    # Route untuk halaman test - menampilkan halaman landing yang sama
    return render_template('landing/index.html')

@web_pages.route('/api/static/images/ai_gen')
def get_static_ai_images():
    """API endpoint untuk mengambil daftar gambar AI dari direktori static"""
    import os
    import glob
    
    try:
        # Path ke direktori static ai_gen
        static_path = os.path.join(current_app.static_folder, 'assets', 'image', 'ai_gen')
        
        # Cek apakah direktori ada
        if not os.path.exists(static_path):
            return jsonify({
                'success': False,
                'message': 'Directory not found',
                'files': []
            })
        
        # Ambil semua file gambar
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']
        files = []
        
        for extension in image_extensions:
            pattern = os.path.join(static_path, extension)
            files.extend(glob.glob(pattern))
            # Juga cari dengan huruf besar
            pattern_upper = os.path.join(static_path, extension.upper())
            files.extend(glob.glob(pattern_upper))
        
        # Konversi ke URL relatif
        static_urls = []
        for file_path in files:
            # Dapatkan nama file saja
            filename = os.path.basename(file_path)
            # Buat URL relatif
            relative_url = f'/static/assets/image/ai_gen/{filename}'
            static_urls.append(relative_url)
        
        # Urutkan berdasarkan nama file
        static_urls.sort()
        
        return jsonify({
            'success': True,
            'message': f'Found {len(static_urls)} images',
            'files': static_urls
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}',
            'files': []
        })

@web_pages.route('/home')
def home():
    # Jika user sudah login, redirect ke halaman home yang lama
    if 'user_id' in session:
        return redirect(url_for('web_pages.old_home'))
    # Jika belum login, redirect ke halaman utama
    return redirect(url_for('web_pages.index'))

@web_pages.route('/old-home')
def old_home():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    
    # Get initial media items for the home page (20 items like Instagram)
    # Distribution: ~7 images, ~7 videos, ~6-7 music (total ~20 items)
    # Take more items initially to compensate for filtering
    images = Image.query.order_by(Image.created_at.desc()).limit(15).all()
    videos = Video.query.order_by(Video.created_at.desc()).limit(15).all()
    
    # Temporary fix for missing genre/mode columns
    try:
        songs = Song.query.order_by(Song.created_at.desc()).limit(15).all()
    except Exception as e:
        # If genre/mode columns don't exist, use raw SQL to get only existing columns
        from sqlalchemy import text
        result = db.session.execute(text("""
            SELECT id, user_id, title, prompt, model_name, duration, 
                   image_url, audio_url, stream_audio_url, source_audio_url,
                   source_image_url, source_stream_audio_url, lyrics, artist,
                   is_favorite, whitelist_reason, view_count, created_at, updated_at
            FROM songs 
            ORDER BY created_at DESC 
            LIMIT 50
        """))
        songs = []
        for row in result:
            song = Song()
            song.id = row[0]
            song.user_id = row[1]
            song.title = row[2]
            song.prompt = row[3]
            song.model_name = row[4]
            song.duration = row[5]
            song.image_url = row[6]
            song.audio_url = row[7]
            song.stream_audio_url = row[8]
            song.source_audio_url = row[9]
            song.source_image_url = row[10]
            song.source_stream_audio_url = row[11]
            song.lyrics = row[12]
            song.artist = row[13]
            song.is_favorite = row[14]
            song.whitelist_reason = row[15]
            song.view_count = row[16]
            song.created_at = row[17]
            song.updated_at = row[18]
            song.genre = None  # Default value
            song.mode = None   # Default value
            songs.append(song)
    
    # Combine all media with type indicators
    all_media = []
    
    # Statistics for debugging
    stats = {
        'images_queried': len(images),
        'videos_queried': len(videos),
        'songs_queried': len(songs),
        'images_deactivated': 0,
        'videos_deactivated': 0,
        'songs_deactivated': 0,
        'images_no_url': 0,
        'videos_no_url': 0,
        'songs_no_url': 0,
        'images_added': 0,
        'videos_added': 0,
        'songs_added': 0
    }
    
    def is_deactivated(content_type: str, content_id: str, obj=None) -> bool:
        if obj is not None and hasattr(obj, 'is_active') and obj.is_active is not None:
            return not bool(obj.is_active)
        action = ModerationAction.query.filter_by(content_type=content_type, content_id=content_id, action='deactivate').first()
        return bool(action and action.active)

    for image in images:
        if is_deactivated('image', str(image.id), image):
            stats['images_deactivated'] += 1
            continue
        # Skip if image_url is empty or None
        if not image.image_url or (isinstance(image.image_url, str) and image.image_url.strip() == ''):
            stats['images_no_url'] += 1
            continue
        likes_count = Like.query.filter_by(content_type='image', content_id=str(image.id)).count()
        comments_count = Comment.query.filter_by(content_type='image', content_id=str(image.id)).count()
        all_media.append({
            'id': image.id,
            'type': 'image',
            'url': image.image_url,
            'caption': image.caption,
            'created_at': image.created_at,
            'user': image.user,
            'likes_count': likes_count,
            'comments_count': comments_count
        })
        stats['images_added'] += 1
    
    for video in videos:
        if is_deactivated('video', str(video.id), video):
            stats['videos_deactivated'] += 1
            continue
        # Skip if video_url is empty or None
        if not video.video_url or (isinstance(video.video_url, str) and video.video_url.strip() == ''):
            stats['videos_no_url'] += 1
            continue
        likes_count = Like.query.filter_by(content_type='video', content_id=str(video.id)).count()
        comments_count = Comment.query.filter_by(content_type='video', content_id=str(video.id)).count()
        all_media.append({
            'id': video.id,
            'type': 'video',
            'url': video.video_url,
            'caption': video.caption,
            'created_at': video.created_at,
            'user': video.user,
            'likes_count': likes_count,
            'comments_count': comments_count
        })
        stats['videos_added'] += 1
    
    for song in songs:
        if is_deactivated('song', str(song.id), song):
            stats['songs_deactivated'] += 1
            continue
        # Skip if audio_url is empty or None
        if not song.audio_url or (isinstance(song.audio_url, str) and song.audio_url.strip() == ''):
            stats['songs_no_url'] += 1
            continue
        likes_count = Like.query.filter_by(content_type='song', content_id=song.id).count()
        comments_count = Comment.query.filter_by(content_type='song', content_id=song.id).count()
        all_media.append({
            'id': song.id,
            'type': 'music',
            'url': song.audio_url,
            'image_url': song.image_url,
            'title': song.title,
            'caption': song.prompt,
            'created_at': song.created_at,
            'user': User.query.get(song.user_id),
            'likes_count': likes_count,
            'comments_count': comments_count
        })
        stats['songs_added'] += 1
    
    # Separate by type for balanced distribution
    images_list = [item for item in all_media if item['type'] == 'image']
    videos_list = [item for item in all_media if item['type'] == 'video']
    music_list = [item for item in all_media if item['type'] == 'music']
    
    # Calculate balanced distribution: ~7 images, ~7 videos, ~6 music (total ~20)
    items_per_type = 7
    total_target = 20
    
    # Take items from each type (already sorted by created_at desc)
    selected_images = images_list[:items_per_type]
    selected_videos = videos_list[:items_per_type]
    selected_music = music_list[:min(items_per_type, len(music_list))]
    
    # Combine and sort by created_at to maintain chronological order
    initial_items = selected_images + selected_videos + selected_music
    initial_items.sort(key=lambda x: x['created_at'], reverse=True)
    
    # If we have less than 20 items, fill with remaining items from all types
    if len(initial_items) < total_target:
        remaining = []
        remaining.extend(images_list[items_per_type:])
        remaining.extend(videos_list[items_per_type:])
        remaining.extend(music_list[items_per_type:])
        remaining.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Add remaining items up to 20 total
        needed = total_target - len(initial_items)
        initial_items.extend(remaining[:needed])
        initial_items.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Limit to exactly 20 items
    initial_items = initial_items[:total_target]
    
    # Count types in initial display
    initial_types = {'image': 0, 'video': 0, 'music': 0}
    for item in initial_items:
        item_type = item.get('type', 'unknown')
        if item_type in initial_types:
            initial_types[item_type] += 1
    
    # Count types in all valid items
    all_types = {'image': len(images_list), 'video': len(videos_list), 'music': len(music_list)}
    
    print(f"""
    📊 Home Page Statistics:
    - Queried: {stats['images_queried']} images, {stats['videos_queried']} videos, {stats['songs_queried']} songs
    - Deactivated: {stats['images_deactivated']} images, {stats['videos_deactivated']} videos, {stats['songs_deactivated']} songs
    - No URL: {stats['images_no_url']} images, {stats['videos_no_url']} videos, {stats['songs_no_url']} songs
    - Added: {stats['images_added']} images, {stats['videos_added']} videos, {stats['songs_added']} songs
    - Total valid items: {len(all_media)} (Images: {all_types['image']}, Videos: {all_types['video']}, Music: {all_types['music']})
    - Initial display: {len(initial_items)} items (Images: {initial_types['image']}, Videos: {initial_types['video']}, Music: {initial_types['music']})
    """)
    
    return render_template('home.html', media_items=initial_items)

@web_pages.route('/home/musik')
def home_musik():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    songs = Song.query.order_by(Song.created_at.desc()).limit(50).all()
    
    media_items = []
    for song in songs:
        likes_count = Like.query.filter_by(content_type='song', content_id=song.id).count()
        comments_count = Comment.query.filter_by(content_type='song', content_id=song.id).count()
        media_items.append({
            'id': song.id,
            'type': 'music',
            'url': song.audio_url,
            'image_url': song.image_url,
            'title': song.title,
            'caption': song.prompt,
            'created_at': song.created_at,
            'user': User.query.get(song.user_id),
            'likes_count': likes_count,
            'comments_count': comments_count
        })
    
    return render_template('home.html', media_items=media_items, active_filter='music')

@web_pages.route('/home/videos')
def home_videos():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    videos = Video.query.order_by(Video.created_at.desc()).limit(50).all()
    
    media_items = []
    for video in videos:
        likes_count = Like.query.filter_by(content_type='video', content_id=str(video.id)).count()
        comments_count = Comment.query.filter_by(content_type='video', content_id=str(video.id)).count()
        media_items.append({
            'id': video.id,
            'type': 'video',
            'url': video.video_url,
            'caption': video.caption,
            'created_at': video.created_at,
            'user': video.user,
            'likes_count': likes_count,
            'comments_count': comments_count
        })
    
    return render_template('home.html', media_items=media_items, active_filter='video')

@web_pages.route('/home/foto')
def home_foto():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    images = Image.query.order_by(Image.created_at.desc()).limit(50).all()
    
    media_items = []
    for image in images:
        likes_count = Like.query.filter_by(content_type='image', content_id=str(image.id)).count()
        comments_count = Comment.query.filter_by(content_type='image', content_id=str(image.id)).count()
        media_items.append({
            'id': image.id,
            'type': 'image',
            'url': image.image_url,
            'caption': image.caption,
            'created_at': image.created_at,
            'user': image.user,
            'likes_count': likes_count,
            'comments_count': comments_count
        })
    
    return render_template('home.html', media_items=media_items, active_filter='photo')

@web_pages.route('/generate_video')

def generate_video():
    if session.get('role') == 'free':
        return redirect(url_for('web_pages.home'))
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    return render_template('generate_video.html')

@web_pages.route('/generate_image')
def generate_image():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    return render_template('generate_image.html')

@web_pages.route('/generate_music')
def generate_music():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    return render_template('generate_music.html')

@web_pages.route('/isi_chat', methods=['GET', 'POST'])
def isi_chat():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    user_id = session['user_id']
    username = request.args.get('user_name')
    target_user = User.query.filter_by(username=username).first()
    if not username:
        return 'User not specified', 400
    # Kirim pesan jika POST
    if request.method == 'POST':
        content = request.form.get('message', '').strip()
        if content:
            msg = Message(sender_id=user_id, receiver_id=target_user.id, content=content)
            db.session.add(msg)
            db.session.commit()
        return redirect(url_for('web_pages.isi_chat', user_name=target_user.username))

    # Ambil semua pesan antara user login dan target user
    messages = Message.query.filter(
        ((Message.sender_id == user_id) & (Message.receiver_id == target_user.id)) |
        ((Message.sender_id == target_user.id) & (Message.receiver_id == user_id))
    ).order_by(Message.sent_at.asc()).all()
    return render_template('chat_isi_user.html', target_user=target_user, messages=messages)

@web_pages.route('/ai_chat')
def ai_chat():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    """Halaman chat dengan AI untuk generate prompt"""
    return render_template('chat_isi.html')
    target_user = User.query.filter_by(username=username).first()
    if not target_user:
        return 'User not found', 404

    # Kirim pesan jika POST
    if request.method == 'POST':
        content = request.form.get('message', '').strip()
        if content:
            msg = Message(sender_id=user_id, receiver_id=target_user.id, content=content)
            db.session.add(msg)
            db.session.commit()
        return redirect(url_for('web_pages.isi_chat', user_name=target_user.username))

    # Ambil semua pesan antara user login dan target user
    messages = Message.query.filter(
        ((Message.sender_id == user_id) & (Message.receiver_id == target_user.id)) |
        ((Message.sender_id == target_user.id) & (Message.receiver_id == user_id))
    ).order_by(Message.sent_at.asc()).all()
    return render_template('chat_isi.html', target_user=target_user, messages=messages)

@web_pages.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('web_pages.home'))
    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter(
            or_(User.username == username_or_email, User.email == username_or_email)
        ).first()
        
        if not user or not user.check_password(password):
            flash('Username/email atau password salah', 'danger')
            return render_template('login.html')
        
        session.permanent = True  # Set session sebagai permanent
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session['avatar_url'] = user.avatar_url or '/static/assets/image/default.jpg'
        session['kredit'] = user.kredit if user.kredit is not None else 0  # Simpan kredit di session juga
        flash('Login berhasil! Selamat datang kembali, ' + user.username + '!', 'success')
        return redirect(url_for('web_pages.profil'))
    
    return render_template('login.html')

@web_pages.route('/auth/google/debug')
def google_oauth_debug():
    """Debug page to show redirect URI that needs to be added to Google Cloud Console"""
    redirect_uri = url_for('web_pages.google_callback', _external=True)
    return f"""
    <html>
    <head><title>Google OAuth Debug</title></head>
    <body style="font-family: Arial; padding: 20px; background: #f5f5f5;">
        <div style="background: white; padding: 20px; border-radius: 8px; max-width: 800px; margin: 0 auto;">
            <h1>Google OAuth Configuration</h1>
            <p><strong>Redirect URI yang perlu ditambahkan di Google Cloud Console:</strong></p>
            <div style="background: #f0f0f0; padding: 15px; border-radius: 4px; margin: 10px 0;">
                <code style="font-size: 14px; word-break: break-all;">{redirect_uri}</code>
            </div>
            <h2>Instruksi:</h2>
            <ol>
                <li>Buka <a href="https://console.cloud.google.com/" target="_blank">Google Cloud Console</a></li>
                <li>Pilih project Anda</li>
                <li>Buka <strong>APIs & Services</strong> → <strong>Credentials</strong></li>
                <li>Klik OAuth 2.0 Client ID Anda</li>
                <li>Di bagian <strong>Authorized redirect URIs</strong>, klik <strong>ADD URI</strong></li>
                <li>Copy dan paste redirect URI di atas</li>
                <li>Klik <strong>SAVE</strong></li>
                <li>Tunggu beberapa detik, lalu coba login lagi</li>
            </ol>
            <p><strong>Catatan:</strong> Jika Anda mengakses dari IP/domain berbeda, tambahkan semua kemungkinan redirect URI:</p>
            <ul>
                <li><code>http://127.0.0.1:5000/auth/google/callback</code></li>
                <li><code>http://localhost:5000/auth/google/callback</code></li>
                <li><code>http://172.20.10.11:5000/auth/google/callback</code></li>
                <li>Dan redirect URI yang ditampilkan di atas</li>
            </ul>
            <p><a href="/login">← Kembali ke Login</a></p>
        </div>
    </body>
    </html>
    """

@web_pages.route('/auth/google')
def google_login():
    """Initiate Google OAuth login"""
    from config import Config
    from urllib.parse import quote, urlencode
    
    # Check if Google OAuth is configured
    if not Config.GOOGLE_CLIENT_ID or Config.GOOGLE_CLIENT_ID == '':
        flash('Google login belum dikonfigurasi. Silakan hubungi administrator.', 'danger')
        return redirect(url_for('web_pages.login'))
    
    # Build redirect URI based on current request
    # For production domain (inemi.id), force HTTPS
    host = request.host
    scheme = request.scheme
    
    # Force HTTPS for production domains
    if 'inemi.id' in host or 'inemi.com' in host:
        scheme = 'https'
    
    # Build redirect URI manually to ensure correct scheme
    redirect_uri = f"{scheme}://{host}/auth/google/callback"
    
    # Log for debugging
    print(f"[Google OAuth] Redirect URI: {redirect_uri}")
    print(f"[Google OAuth] Request URL: {request.url}")
    print(f"[Google OAuth] Request Host: {host}")
    print(f"[Google OAuth] Request Scheme: {request.scheme}")
    print(f"[Google OAuth] Using Scheme: {scheme}")
    
    # Build Google OAuth URL with proper encoding
    params = {
        'client_id': Config.GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'online'
    }
    
    google_auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(params)
    
    print(f"[Google OAuth] Google Auth URL: {google_auth_url}")
    
    return redirect(google_auth_url)

@web_pages.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    from config import Config
    import base64
    
    code = request.args.get('code')
    error = request.args.get('error')
    error_description = request.args.get('error_description', '')
    
    # Handle OAuth errors
    if error:
        # Build redirect URI for error message (must match the one used in google_login)
        host = request.host
        scheme = request.scheme
        if 'inemi.id' in host or 'inemi.com' in host:
            scheme = 'https'
        redirect_uri = f"{scheme}://{host}/auth/google/callback"
        
        if error == 'redirect_uri_mismatch':
            error_msg = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Google OAuth Error - Redirect URI Mismatch</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        padding: 20px;
                        margin: 0;
                    }}
                    .error-container {{
                        max-width: 700px;
                        background: white;
                        border-radius: 16px;
                        padding: 40px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    }}
                    h1 {{
                        color: #d32f2f;
                        margin-bottom: 20px;
                        font-size: 28px;
                    }}
                    .redirect-uri-box {{
                        background: #f5f5f5;
                        padding: 15px;
                        border-radius: 8px;
                        margin: 20px 0;
                        border-left: 4px solid #667eea;
                    }}
                    code {{
                        word-break: break-all;
                        font-family: 'Courier New', monospace;
                        font-size: 14px;
                        color: #333;
                    }}
                    ol, ul {{
                        text-align: left;
                        line-height: 1.8;
                    }}
                    .btn {{
                        display: inline-block;
                        padding: 12px 24px;
                        background: #667eea;
                        color: white;
                        text-decoration: none;
                        border-radius: 8px;
                        margin-top: 20px;
                        font-weight: 600;
                        transition: transform 0.2s;
                    }}
                    .btn:hover {{
                        transform: translateY(-2px);
                    }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <h1>❌ Redirect URI Mismatch</h1>
                    <p>Redirect URI yang digunakan tidak terdaftar di Google Cloud Console.</p>
                    <p><strong>Redirect URI yang digunakan:</strong></p>
                    <div class="redirect-uri-box">
                        <code>{redirect_uri}</code>
                    </div>
                    <h3>Langkah perbaikan:</h3>
                    <ol>
                        <li>Buka <a href="https://console.cloud.google.com/apis/credentials" target="_blank">Google Cloud Console - Credentials</a></li>
                        <li>Klik OAuth 2.0 Client ID Anda</li>
                        <li>Scroll ke bagian <strong>"Authorized redirect URIs"</strong></li>
                        <li>Klik <strong>"ADD URI"</strong></li>
                        <li>Copy dan paste redirect URI di atas: <code>{redirect_uri}</code></li>
                        <li>Klik <strong>"SAVE"</strong></li>
                        <li>Tunggu 1-2 menit, lalu coba login lagi</li>
                    </ol>
                    <p><strong>Atau tambahkan semua kemungkinan URI:</strong></p>
                    <ul>
                        <li><code>http://127.0.0.1:5000/auth/google/callback</code></li>
                        <li><code>http://localhost:5000/auth/google/callback</code></li>
                        <li><code>https://www.inemi.id/auth/google/callback</code></li>
                        <li><code>https://inemi.id/auth/google/callback</code></li>
                    </ul>
                    <a href="/login" class="btn">← Kembali ke Login</a>
                </div>
            </body>
            </html>
            '''
            return error_msg
        else:
            flash(f'Error dari Google: {error_description or error}', 'danger')
            return redirect(url_for('web_pages.login'))
    
    if not code:
        flash('Gagal login dengan Google. Silakan coba lagi.', 'danger')
        return redirect(url_for('web_pages.login'))
    
    try:
        # Build redirect URI based on current request (must match the one used in google_login)
        # For production domain (inemi.id), force HTTPS
        host = request.host
        scheme = request.scheme
        
        # Force HTTPS for production domains
        if 'inemi.id' in host or 'inemi.com' in host:
            scheme = 'https'
        
        # Build redirect URI manually to ensure correct scheme
        redirect_uri = f"{scheme}://{host}/auth/google/callback"
        
        # Log for debugging
        print(f"[Google OAuth Callback] Redirect URI: {redirect_uri}")
        print(f"[Google OAuth Callback] Request URL: {request.url}")
        print(f"[Google OAuth Callback] Request Host: {host}")
        print(f"[Google OAuth Callback] Request Scheme: {request.scheme}")
        print(f"[Google OAuth Callback] Using Scheme: {scheme}")
        print(f"[Google OAuth Callback] Code received: {code[:20]}...")
        
        # Exchange code for access token
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': Config.GOOGLE_CLIENT_ID,
            'client_secret': Config.GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        print(f"[Google OAuth Callback] Token request data: {token_data}")
        
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        print(f"[Google OAuth Callback] Token response: {token_json}")
        
        if 'access_token' not in token_json:
            flash('Gagal mendapatkan token dari Google. Silakan coba lagi.', 'danger')
            return redirect(url_for('web_pages.login'))
        
        access_token = token_json['access_token']
        
        # Get user info from Google
        user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        user_info_response = requests.get(user_info_url, headers=headers)
        user_info = user_info_response.json()
        
        if 'email' not in user_info:
            flash('Gagal mendapatkan informasi dari Google. Silakan coba lagi.', 'danger')
            return redirect(url_for('web_pages.login'))
        
        email = user_info.get('email')
        name = user_info.get('name', '')
        picture = user_info.get('picture', '')
        google_id = user_info.get('id', '')
        
        # Check if user exists by email
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create new user with Google account
            # Generate username from email or name
            username_base = name.lower().replace(' ', '_') if name else email.split('@')[0]
            username = username_base
            counter = 1
            
            # Ensure unique username
            while User.query.filter_by(username=username).first():
                username = f"{username_base}_{counter}"
                counter += 1
            
            # Create new user
            user = User(
                username=username,
                email=email,
                password='',  # No password for Google users
                avatar_url=picture or '/static/assets/image/default.jpg',
                role='free',
                kredit=100  # Give 100 credits for new Google users
            )
            db.session.add(user)
            db.session.commit()
            
            flash('Akun berhasil dibuat dengan Google!', 'success')
        else:
            # Update avatar if available
            if picture and (not user.avatar_url or user.avatar_url == '/static/assets/image/default.jpg'):
                user.avatar_url = picture
                db.session.commit()
        
        # Set session
        session.permanent = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session['avatar_url'] = user.avatar_url or '/static/assets/image/default.jpg'
        session['kredit'] = user.kredit if user.kredit is not None else 0
        
        return redirect(url_for('web_pages.profil'))
        
    except Exception as e:
        print(f"Google OAuth error: {e}")
        import traceback
        traceback.print_exc()
        flash('Terjadi kesalahan saat login dengan Google. Silakan coba lagi.', 'danger')
        return redirect(url_for('web_pages.login'))

@web_pages.route('/lokal')
def lokal():
    return render_template('lokal.html')

@web_pages.route('/profil')
def profil():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    
    user = db.session.get(User, session['user_id'])
    media_items = []

    # Get user's images (all images, ordered by latest first)
    user_images = Image.query.filter_by(user_id=user.id).order_by(Image.created_at.desc()).all() if user else []
    for image in user_images:
        media_items.append({
            'id': image.id,
            'type': 'image',
            'url': image.image_url,
            'caption': image.caption,
            'created_at': image.created_at
        })

    # Get user's videos (all videos, ordered by latest first)
    user_videos = Video.query.filter_by(user_id=user.id).order_by(Video.created_at.desc()).all() if user else []
    for video in user_videos:
        media_items.append({
            'id': video.id,
            'type': 'video',
            'url': video.video_url,
            'caption': video.caption,
            'created_at': video.created_at
        })

    # Get user's songs (all songs, ordered by latest first)
    user_songs = Song.query.filter_by(user_id=user.id).order_by(Song.created_at.desc()).all() if user else []
    for song in user_songs:
        media_items.append({
            'id': song.id,
            'type': 'music',
            'url': song.audio_url,
            'image_url': song.image_url,
            'title': song.title,
            'caption': song.prompt,
            'created_at': song.created_at
        })

    # Sort all media items by creation date (latest first)
    media_items.sort(key=lambda x: x['created_at'], reverse=True)

    follower_count = len(user.followers)
    following_count = len(user.following)
    return render_template('profil.html', user=user, media_items=media_items, follower_count=follower_count, following_count=following_count)

@web_pages.route('/profil_private')
def profil_private():
    return render_template('profil_private.html')

@web_pages.route('/profil_user_lain')
def profil_user_lain():
    return render_template('profil_user_lain.html')

@web_pages.route('/user/<username>')
def user_profile(username):
    if 'username' in session and session['username'] == username:
        return redirect(url_for('web_pages.profil'))
    # Check if username is actually an email
    user = User.query.filter_by(email=username).first()
    if not user:
        user = User.query.filter_by(username=username).first()
    if not user:
        return 'User not found', 404
    
    media_items = []

    # Get user's images (all images, ordered by latest first)
    user_images = Image.query.filter_by(user_id=user.id).order_by(Image.created_at.desc()).all()
    for image in user_images:
        media_items.append({
            'id': image.id,
            'type': 'image',
            'url': image.image_url,
            'caption': image.caption,
            'created_at': image.created_at
        })

    # Get user's videos (all videos, ordered by latest first)
    user_videos = Video.query.filter_by(user_id=user.id).order_by(Video.created_at.desc()).all()
    for video in user_videos:
        media_items.append({
            'id': video.id,
            'type': 'video',
            'url': video.video_url,
            'caption': video.caption,
            'created_at': video.created_at
        })

    # Get user's songs (all songs, ordered by latest first)
    user_songs = Song.query.filter_by(user_id=user.id).order_by(Song.created_at.desc()).all()
    for song in user_songs:
        media_items.append({
            'id': song.id,
            'type': 'music',
            'url': song.audio_url,
            'image_url': song.image_url,
            'title': song.title,
            'caption': song.prompt,
            'created_at': song.created_at
        })

    # Sort all media items by creation date (latest first)
    media_items.sort(key=lambda x: x['created_at'], reverse=True)

    follower_count = len(user.followers)
    following_count = len(user.following)
    is_following = False
    if 'user_id' in session:
        current_user = db.session.get(User, session['user_id'])
        is_following = current_user.is_following(user) if current_user.id != user.id else False
        print(f"DEBUG: Is following: {current_user.username} is following {user.username}? {is_following}")
    return render_template('profil_user_lain.html', user=user, media_items=media_items, follower_count=follower_count, following_count=following_count, is_following=is_following)

@web_pages.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('web_pages.home'))
    if request.method == 'POST':
        username = sanitize_text(request.form.get('username'))
        email = sanitize_text(request.form.get('email'))
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        agree_terms = request.form.get('agreeTerms')

        # Validation
        if not username or not email or not password or not confirm_password:
            flash('Mohon isi semua field yang diperlukan.', 'danger')
            return render_template('register.html')
        if len(username) < 3:
            flash('Username minimal 3 karakter.', 'danger')
            return render_template('register.html')
        if len(username) > 20:
            flash('Username maksimal 20 karakter.', 'danger')
            return render_template('register.html')
        if ' ' in username:
            flash('Username tidak boleh mengandung spasi.', 'danger')
            return render_template('register.html')
        username_pattern = re.compile(r'^[a-zA-Z0-9_]+$')
        if not username_pattern.match(username):
            flash('Username hanya boleh mengandung huruf, angka, dan underscore (_).', 'danger')
            return render_template('register.html')
        if username[0].isdigit():
            flash('Username tidak boleh dimulai dengan angka.', 'danger')
            return render_template('register.html')
        if '<' in username or '>' in username or '"' in username or "'" in username:
            flash('Username tidak boleh mengandung karakter khusus yang berbahaya.', 'danger')
            return render_template('register.html')
        if 'javascript:' in username.lower() or 'data:' in username.lower():
            flash('Username tidak boleh mengandung script atau data URL.', 'danger')
            return render_template('register.html')
        if 'http://' in username.lower() or 'https://' in username.lower():
            flash('Username tidak boleh mengandung URL.', 'danger')
            return render_template('register.html')
        if 'admin' in username.lower() or 'root' in username.lower() or 'system' in username.lower():
            flash('Username tidak boleh mengandung kata yang dilarang.', 'danger')
            return render_template('register.html')
        if len(password) < 8:
            flash('Password minimal 8 karakter.', 'danger')
            return render_template('register.html')
        if len(password) > 50:
            flash('Password maksimal 50 karakter.', 'danger')
            return render_template('register.html')
        if not re.search(r'[A-Z]', password):
            flash('Password harus mengandung minimal 1 huruf besar.', 'danger')
            return render_template('register.html')
        if not re.search(r'[a-z]', password):
            flash('Password harus mengandung minimal 1 huruf kecil.', 'danger')
            return render_template('register.html')
        if not re.search(r'\d', password):
            flash('Password harus mengandung minimal 1 angka.', 'danger')
            return render_template('register.html')
        if '<' in password or '>' in password or '"' in password or "'" in password:
            flash('Password tidak boleh mengandung karakter khusus yang berbahaya.', 'danger')
            return render_template('register.html')
        if 'javascript:' in password.lower() or 'data:' in password.lower():
            flash('Password tidak boleh mengandung script atau data URL.', 'danger')
            return render_template('register.html')
        if 'http://' in password.lower() or 'https://' in password.lower():
            flash('Password tidak boleh mengandung URL.', 'danger')
            return render_template('register.html')
        if len(email) > 100:
            flash('Email maksimal 100 karakter.', 'danger')
            return render_template('register.html')
        email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
        if not email_pattern.match(email):
            flash('Format email tidak valid.', 'danger')
            return render_template('register.html')
        if '<' in email or '>' in email or '"' in email or "'" in email:
            flash('Email tidak boleh mengandung karakter khusus yang berbahaya.', 'danger')
            return render_template('register.html')
        if 'javascript:' in email.lower() or 'data:' in email.lower():
            flash('Email tidak boleh mengandung script atau data URL.', 'danger')
            return render_template('register.html')
        if 'http://' in email.lower() or 'https://' in email.lower():
            flash('Email tidak boleh mengandung URL.', 'danger')
            return render_template('register.html')
        if 'admin' in username.lower() or 'root' in username.lower() or 'system' in username.lower():
            flash('Username tidak boleh mengandung kata yang dilarang.', 'danger')
            return render_template('register.html')
        if password != confirm_password:
            flash('Password dan konfirmasi password tidak cocok.', 'danger')
            return render_template('register.html')
        if not agree_terms:
            flash('Anda harus menyetujui Terms & Conditions.', 'danger')
            return render_template('register.html')

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan. Silakan pilih username lain.', 'danger')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email sudah terdaftar. Silakan gunakan email lain.', 'danger')
            return render_template('register.html')

        # Create user
        user = User(username=username, email=email, avatar_url='/static/assets/image/default.jpg', role='free', kredit=100)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registrasi berhasil! Akun Anda telah dibuat. Silakan login untuk melanjutkan.', 'success')
        return redirect(url_for('web_pages.login'))
    return render_template('register.html')

@web_pages.route('/saran')
def saran():
    images = Image.query.order_by(Image.created_at.desc()).all()
    videos = Video.query.order_by(Video.created_at.desc()).all()
    songs = Song.query.order_by(Song.created_at.desc()).all()
    return render_template('lokal.html', images=images, videos=videos, songs=songs)

@web_pages.route('/teman')
def teman():
    images = Image.query.order_by(Image.created_at.desc()).all()
    videos = Video.query.order_by(Video.created_at.desc()).all()
    songs = Song.query.order_by(Song.created_at.desc()).all()
    return render_template('lokal.html', images=images, videos=videos, songs=songs)

@web_pages.route('/untuk_kamu')
def untuk_kamu():
    return render_template('lokal.html')

@web_pages.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Berhasil logout', 'success')
    return redirect(url_for('web_pages.index'))

@web_pages.route('/follow/<username>', methods=['POST'])
def follow_user(username):
    print(f"DEBUG: Follow request for username: {username}")
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    # Check if username is actually an email
    user = User.query.filter_by(email=username).first()
    if not user:
        user = User.query.filter_by(username=username).first()
    if not user:
        print(f"DEBUG: User not found for username: {username}")
        abort(404)
    current_user = db.session.get(User, session['user_id'])
    print(f"DEBUG: Current user: {current_user.username}, Target user: {user.username}")
    if user.id == current_user.id:
        return redirect(url_for('web_pages.user_profile', username=user.username))
    current_user.follow(user)
    
    return redirect(url_for('web_pages.user_profile', username=user.username))

@web_pages.route('/unfollow/<username>', methods=['POST'])
def unfollow_user(username):
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    # Check if username is actually an email
    user = User.query.filter_by(email=username).first()
    if not user:
        user = User.query.filter_by(username=username).first()
    if not user:
        abort(404)
    current_user = db.session.get(User, session['user_id'])
    if user.id == current_user.id:
        return redirect(url_for('web_pages.user_profile', username=user.username))
    current_user.unfollow(user)
    return redirect(url_for('web_pages.user_profile', username=user.username))

@web_pages.route('/like', methods=['POST'])
def like_content():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    user_id = session['user_id']
    content_type = request.form.get('content_type')
    content_id = request.form.get('content_id')
    if not content_type or not content_id:
        return jsonify({'success': False, 'error': 'Missing content_type or content_id'}), 400
    content_id = str(content_id)  # Pastikan selalu string
    from models import Like
    existing = Like.query.filter_by(user_id=user_id, content_type=content_type, content_id=content_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        liked = False
    else:
        like = Like(user_id=user_id, content_type=content_type, content_id=content_id)
        db.session.add(like)
        db.session.commit()
        liked = True
        
        # Create notification for like
        try:
            # Get content owner
            if content_type == 'image':
                content = Image.query.get(content_id)
            elif content_type == 'video':
                content = Video.query.get(content_id)
            elif content_type == 'song':
                content = Song.query.get(content_id)
            elif content_type == 'video_iklan':
                content = VideoIklan.query.get(content_id)
            else:
                content = None
                
            if content and content.user_id != user_id:  # Don't notify if user likes their own content
                from utils.notification_utils import create_notification
                create_notification(
                    sender_id=user_id,
                    recipient_id=content.user_id,
                    notification_type='like',
                    content_type=content_type,
                    content_id=content_id
                )
        except Exception as e:
            print(f"Error creating like notification: {e}")
    
    like_count = Like.query.filter_by(content_type=content_type, content_id=content_id).count()
    return jsonify({'success': True, 'like_count': like_count, 'liked': liked})

@web_pages.route('/comment', methods=['POST'])
def add_comment():
    print("=== DEBUG: add_comment called ===")
    print(f"Session: {session}")
    print(f"Form data: {request.form}")
    
    if 'user_id' not in session:
        print("❌ User not logged in")
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    content_type = request.form.get('content_type')
    content_id = request.form.get('content_id')
    text = sanitize_text(request.form.get('text', '').strip())
    
    print(f"User ID: {user_id}")
    print(f"Content Type: {content_type}")
    print(f"Content ID: {content_id}")
    print(f"Text: {text}")
    
    if not content_type or not content_id or not text:
        print("❌ Missing required fields")
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    content_id = str(content_id)  # Pastikan selalu string
    print(f"Content ID (converted): {content_id}")
    
    try:
        from models import Comment
        comment = Comment(user_id=user_id, content_type=content_type, content_id=content_id, text=text)
        print(f"Comment object created: {comment}")
        
        db.session.add(comment)
        db.session.commit()
        print(f"✅ Comment saved to database with ID: {comment.id}")
    except Exception as e:
        print(f"❌ Error saving comment: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
    
    # Create notification for comment
    try:
        # Get content owner
        if content_type == 'image':
            content = Image.query.get(content_id)
        elif content_type == 'video':
            content = Video.query.get(content_id)
        elif content_type == 'song':
            content = Song.query.get(content_id)
        elif content_type == 'video_iklan':
            content = VideoIklan.query.get(content_id)
        else:
            content = None
            
        if content and content.user_id != user_id:  # Don't notify if user comments their own content
            from utils.notification_utils import create_notification
            create_notification(
                sender_id=user_id,
                recipient_id=content.user_id,
                notification_type='comment',
                content_type=content_type,
                content_id=content_id,
                text=text[:100]  # Limit text length for notification
            )
    except Exception as e:
        print(f"Error creating comment notification: {e}")
    
    return jsonify({'success': True, 'comment_id': comment.id})


@web_pages.route('/comment/reply', methods=['POST'])
def reply_comment():
    """Route untuk membalas komentar"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    parent_comment_id = request.form.get('parent_comment_id')
    text = sanitize_text(request.form.get('text', '').strip())
    
    if not parent_comment_id or not text:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    try:
        # Get parent comment
        from models import Comment
        parent_comment = Comment.query.get(parent_comment_id)
        if not parent_comment:
            return jsonify({'success': False, 'error': 'Parent comment not found'}), 404
        
        # Create reply comment
        reply_comment = Comment(
            user_id=user_id,
            content_type=parent_comment.content_type,
            content_id=parent_comment.content_id,
            text=text,
            parent_id=parent_comment_id
        )
        db.session.add(reply_comment)
        db.session.commit()
        
        # Create notification for comment reply
        try:
            if parent_comment.user_id != user_id:  # Don't notify if user replies to their own comment
                from utils.notification_utils import create_notification
                create_notification(
                    sender_id=user_id,
                    recipient_id=parent_comment.user_id,
                    notification_type='comment_reply',
                    content_type=parent_comment.content_type,
                    content_id=parent_comment.content_id,
                    comment_id=parent_comment_id,
                    text=text[:100]  # Limit text length for notification
                )
        except Exception as e:
            print(f"Error creating comment reply notification: {e}")
        
        return jsonify({
            'success': True, 
            'comment_id': reply_comment.id,
            'parent_comment_id': parent_comment_id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating comment reply: {e}")
        return jsonify({'success': False, 'error': 'Failed to create reply'}), 500


@web_pages.route('/api/notifications/unread-count')
def api_notifications_unread_count():
    """API endpoint untuk mendapatkan jumlah notifikasi yang belum dibaca"""
    try:
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'error': 'Not authenticated',
                'unread_count': 0
            }), 401
        
        user_id = session['user_id']
        from models import Notification
        
        # Count unread notifications
        unread_count = Notification.query.filter_by(
            recipient_id=user_id,
            is_read=False
        ).count()
        
        return jsonify({
            'success': True,
            'unread_count': unread_count
        })
    except Exception as e:
        print(f"Error fetching unread count: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'unread_count': 0
        }), 500

@web_pages.route('/notifications')
def notifications_page():
    """Halaman untuk melihat semua notifikasi"""
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    
    try:
        user_id = session['user_id']
        from models import Notification
        
        # Get all notifications for user
        notifications = Notification.query.filter_by(recipient_id=user_id).order_by(Notification.created_at.desc()).all()
        
        # Mark all as read
        for notification in notifications:
            if not notification.is_read:
                notification.is_read = True
        db.session.commit()
        
        return render_template('notifications.html', notifications=notifications)
    except Exception as e:
        print(f"Error loading notifications page: {e}")
        return redirect(url_for('web_pages.home'))

@web_pages.route('/profil_edit', methods=['GET', 'POST'])
def profil_edit():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    user = db.session.get(User, session['user_id'])
    if not user:
        return redirect(url_for('web_pages.login'))

    error = None
    if request.method == 'POST':
        username = sanitize_text(request.form.get('username', '').strip())
        email = sanitize_text(request.form.get('email', '').strip())
        bio = sanitize_text(request.form.get('bio', '').strip())
        file = request.files.get('profile_pic')

        # Validasi username tidak boleh ada spasi
        if username and ' ' in username:
            error = 'Username tidak boleh mengandung spasi.'
        # Cek username jika berubah
        elif username and username != user.username:
            if User.query.filter(User.username == username, User.id != user.id).first():
                error = 'Username sudah digunakan.'
        # Cek email jika berubah
        if not error and email and email != user.email:
            if User.query.filter(User.email == email, User.id != user.id).first():
                error = 'Email sudah digunakan.'

        if error:
            return error, 400

        if username:
            user.username = username
            session['username'] = username
        if email:
            user.email = email
        if hasattr(user, 'bio'):
            user.bio = bio
        if file and file.filename:
            from werkzeug.utils import secure_filename
            allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in allowed_extensions:
                return 'Tipe file tidak didukung. Gunakan PNG, JPG, JPEG, GIF, atau WEBP.', 400
            allowed_mimes = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
            mime_type = file.content_type or 'image/jpeg'
            if mime_type not in allowed_mimes:
                return 'Tipe MIME file tidak valid', 400
            file.seek(0, 2)
            file_length = file.tell()
            file.seek(0)
            if file_length > 5 * 1024 * 1024:
                return 'Ukuran file terlalu besar (maksimal 5MB)', 400
            filename = f'{uuid.uuid4().hex}{ext}'
            path = os.path.join('static/assets/image/profile', filename)
            file.save(path)
            user.avatar_url = f'/static/assets/image/profile/{filename}'
            session['avatar_url'] = user.avatar_url
        db.session.commit()
        return 'Profile updated!',200

    return render_template('profil_edit.html', user=user)

@web_pages.route('/upgrade_akun')
def upgrade_akun():
    # if 'user_id' not in session:
    #     return redirect(url_for('web_pages.login'))
    # user = db.session.get(User, session['user_id'])
    # Tambahkan info ke template jika ingin
    return render_template('upgrade_akun.html')

@web_pages.route('/payment/products')
def payment_products():
    """API endpoint untuk mendapatkan daftar products untuk upgrade"""
    try:
        products = Product.query.all()
        products_data = []
        
        for product in products:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'description': f"Product {product.name} with {product.kredit} credits",
                'price': float(product.price),
                'kredit': product.kredit,
                'duration_days': 30,  # Default duration
                'features': []  # Empty features array
            })
        
        return jsonify({
            'success': True,
            'products': products_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@web_pages.route('/api/check-login')
def check_login():
    """API endpoint untuk mengecek status login user"""
    return jsonify({
        'logged_in': 'user_id' in session,
        'user_id': session.get('user_id'),
        'username': session.get('username')
    })

@web_pages.route('/payment/form/<int:product_id>')
def payment_form(product_id):
    """Form pembayaran untuk upgrade akun"""
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu untuk melanjutkan pembayaran.', 'warning')
        return redirect(url_for('web_pages.login'))
    
    # Get product details
    product = Product.query.get_or_404(product_id)
    user = User.query.get(session['user_id'])
    
    return render_template('payment_form.html', product=product, user=user)

@web_pages.route('/payment/process', methods=['POST'])
def process_payment():
    """Proses pembayaran dan buat order"""
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    
    try:
        # Get form data
        product_id = request.form.get('product_id')
        payment_method = request.form.get('payment_method')
        notes = request.form.get('notes', '')
        
        # Handle file upload
        proof_image = None
        if 'proof_image' in request.files:
            file = request.files['proof_image']
            if file and file.filename != '' and allowed_file(file.filename):
                # Create upload directory if it doesn't exist
                upload_path = os.path.join(current_app.root_path, 'static/uploads/proof_images')
                os.makedirs(upload_path, exist_ok=True)
                
                # Generate secure filename
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{timestamp}{ext}"
                
                # Save file
                file_path = os.path.join(upload_path, filename)
                file.save(file_path)
                
                # Set proof image URL
                proof_image = f"/static/uploads/proof_images/{filename}"
        
        final_proof_image = proof_image
        
        # Validate required fields
        if not product_id:
            flash('Product ID tidak valid!', 'error')
            return redirect(url_for('web_pages.upgrade_akun'))
        
        if not final_proof_image:
            flash('Bukti pembayaran harus diupload!', 'error')
            return redirect(url_for('web_pages.payment_form', product_id=product_id))
        
        # Get product and user
        product = Product.query.get_or_404(product_id)
        user = User.query.get(session['user_id'])
        
        # Create order
        order = Order(
            user_id=user.id,
            product_id=product.id,
            total_amount=product.price,
            status='pending'
        )
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Create payment
        payment = Payment(
            order_id=order.order_id,
            amount=product.price,
            method=payment_method or 'bank_transfer',
            proof_image=final_proof_image,
            status='pending'
        )
        db.session.add(payment)
        db.session.commit()
        
        flash('Pembayaran berhasil diajukan! Silakan tunggu konfirmasi dari admin.', 'success')
        return redirect(url_for('web_pages.upgrade_akun'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('web_pages.upgrade_akun'))

@web_pages.route('/transaction-history')
def transaction_history():
    """Halaman riwayat transaksi user"""
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu untuk melihat riwayat transaksi.', 'warning')
        return redirect(url_for('web_pages.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get user's orders with payments
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    
    # Get payments for each order
    transactions = []
    for order in orders:
        payment = Payment.query.filter_by(order_id=order.order_id).first()
        
        transactions.append({
            'order': order,
            'payment': payment,
            'product': order.product  # Use relationship
        })
    
    return render_template('transaction_history.html', user=user, transactions=transactions)

@web_pages.route('/upgrade/pro', methods=['POST'])
def upgrade_pro():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    # Jangan langsung upgrade, tampilkan instruksi pembayaran
    flash('Silakan selesaikan pembayaran untuk upgrade ke Pro. Kredit dan fitur Pro akan aktif setelah pembayaran berhasil.', 'info')
    return redirect(url_for('web_pages.upgrade_akun'))

@web_pages.route('/upgrade/premier', methods=['POST'])
def upgrade_premier():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    # Jangan langsung upgrade, tampilkan instruksi pembayaran
    flash('Silakan selesaikan pembayaran untuk upgrade ke Premier. Kredit dan fitur Premier akan aktif setelah pembayaran berhasil.', 'info')
    return redirect(url_for('web_pages.upgrade_akun'))

@web_pages.route('/home/videos_iklan')
def home_videos_iklan():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    videos_iklan = VideoIklan.query.order_by(VideoIklan.created_at.desc()).limit(50).all()
    media_items = []
    for video in videos_iklan:
        # Ambil user data
        user = db.session.get(User, video.user_id)
        # Hitung likes dan comments
        likes_count = Like.query.filter_by(content_type='video_iklan', content_id=str(video.id)).count()
        comments_count = Comment.query.filter_by(content_type='video_iklan', content_id=str(video.id)).count()
        
        media_items.append({
            'id': video.id,
            'type': 'video_iklan',
            'video_url': video.video_url,
            'caption': video.caption or 'Video Iklan',
            'created_at': video.created_at,
            'user': user,
            'likes_count': likes_count,
            'comments_count': comments_count
        })
    return render_template('home.html', media_items=media_items, active_filter='video_iklan')

@web_pages.route('/home/favorite')
def home_favorite():
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    
    # Get favorite/whitelisted content
    favorite_images = Image.query.filter_by(is_favorite=True).order_by(Image.created_at.desc()).limit(20).all()
    favorite_videos = Video.query.filter_by(is_favorite=True).order_by(Video.created_at.desc()).limit(20).all()
    favorite_songs = Song.query.filter_by(is_favorite=True).order_by(Song.created_at.desc()).limit(20).all()
    
    # If no favorites found, get high-quality recent content as fallback
    if not favorite_images and not favorite_videos and not favorite_songs:
        favorite_images = Image.query.order_by(Image.created_at.desc()).limit(10).all()
        favorite_videos = Video.query.order_by(Video.created_at.desc()).limit(10).all()
        favorite_songs = Song.query.order_by(Song.created_at.desc()).limit(10).all()
    
    media_items = []
    
    # Add favorite images
    for image in favorite_images:
        likes_count = Like.query.filter_by(content_type='image', content_id=str(image.id)).count()
        comments_count = Comment.query.filter_by(content_type='image', content_id=str(image.id)).count()
        media_items.append({
            'id': image.id,
            'type': 'image',
            'url': image.image_url,
            'caption': image.caption or 'High-quality AI Generated Image',
            'created_at': image.created_at,
            'user': image.user,
            'likes_count': likes_count,
            'comments_count': comments_count,
            'is_favorite': True
        })
    
    # Add favorite videos
    for video in favorite_videos:
        likes_count = Like.query.filter_by(content_type='video', content_id=str(video.id)).count()
        comments_count = Comment.query.filter_by(content_type='video', content_id=str(video.id)).count()
        media_items.append({
            'id': video.id,
            'type': 'video',
            'url': video.video_url,
            'caption': video.caption or 'High-quality AI Generated Video',
            'created_at': video.created_at,
            'user': video.user,
            'likes_count': likes_count,
            'comments_count': comments_count,
            'is_favorite': True
        })
    
    # Add favorite songs
    for song in favorite_songs:
        likes_count = Like.query.filter_by(content_type='song', content_id=song.id).count()
        comments_count = Comment.query.filter_by(content_type='song', content_id=song.id).count()
        media_items.append({
            'id': song.id,
            'type': 'music',
            'url': song.audio_url,
            'image_url': song.image_url,
            'title': song.title,
            'caption': song.prompt or 'High-quality AI Generated Music',
            'created_at': song.created_at,
            'user': User.query.get(song.user_id),
            'likes_count': likes_count,
            'comments_count': comments_count,
            'is_favorite': True
        })
    
    # Sort by creation date to ensure newest first
    media_items.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('home.html', media_items=media_items, active_filter='favorite')

@web_pages.route('/post_musik/<string:song_id>')
def post_musik(song_id):
    """Post musik page - dapat menerima ID sebagai string atau integer"""
    # Try to convert to int if possible, otherwise use as string
    song_id_int = None
    try:
        song_id_int = int(song_id)
        song = Song.query.get_or_404(song_id_int)
    except (ValueError, TypeError):
        # If not a valid integer, try as string ID (for UUID or other string IDs)
        song = Song.query.filter_by(id=song_id).first_or_404()
        song_id_int = song.id  # Get the actual integer ID from the song object
    
    # Use integer ID for filtering (more reliable)
    if song_id_int is None:
        song_id_int = song.id
    
    playlist = Song.query.filter(Song.id != song_id_int).order_by(func.random()).limit(10).all()
    
    # Get database songs for browser (exclude current song)
    database_songs = Song.query.filter(Song.id != song_id_int).order_by(Song.created_at.desc()).limit(20).all()
    database_songs_with_user = []
    for s in database_songs:
        user = db.session.get(User, s.user_id)
        database_songs_with_user.append({
            'id': s.id,
            'title': s.title,
            'prompt': s.prompt,
            'model_name': s.model_name,
            'duration': s.duration,
            'image_url': s.image_url,
            'audio_url': s.audio_url,
            'username': user.username if user else 'Unknown'
        })
    
    # Get recommendations (similar songs or random)
    recommendations = Song.query.filter(Song.id != song_id_int).order_by(func.random()).limit(6).all()
    recommendations_with_user = []
    for s in recommendations:
        user = db.session.get(User, s.user_id)
        recommendations_with_user.append({
            'id': s.id,
            'title': s.title,
            'prompt': s.prompt,
            'model_name': s.model_name,
            'duration': s.duration,
            'image_url': s.image_url,
            'audio_url': s.audio_url,
            'username': user.username if user else 'Unknown'
        })
    
    # Buat playlist dengan username
    playlist_with_user = []
    for s in playlist:
        user = db.session.get(User, s.user_id)
        playlist_with_user.append({
            'id': s.id,
            'title': s.title,
            'prompt': s.prompt,
            'model_name': s.model_name,
            'duration': s.duration,
            'image_url': s.image_url,
            'audio_url': s.audio_url,
            'username': user.username if user else 'Unknown'
        })
    # Untuk lagu utama juga
    song_user = db.session.get(User, song.user_id)
    song_dict = {
        'id': song.id,
        'title': song.title,
        'prompt': song.prompt,
        'model_name': song.model_name,
        'duration': song.duration,
        'image_url': song.image_url,
        'audio_url': song.audio_url,
        'username': song_user.username if song_user else 'Unknown'
    }
    # Get likes count for this song
    likes_count = Like.query.filter_by(content_type='song', content_id=str(song.id)).count()
    
    # Get comments for this song (only parent comments, not replies)
    comments = Comment.query.filter_by(
        content_type='song', 
        content_id=str(song.id),
        parent_id=None  # Only get parent comments
    ).order_by(Comment.created_at.desc()).all()
    
    # Check if current user has liked this song
    is_liked = False
    if 'user_id' in session:
        is_liked = Like.query.filter_by(
            user_id=session['user_id'], 
            content_type='song', 
            content_id=str(song.id)
        ).first() is not None
    
    all_songs = [song] + playlist
    total_duration = sum([(s.duration or 0) for s in all_songs])
    total_duration_minutes = int(total_duration // 60)
    total_duration_seconds = int(total_duration % 60)
    return render_template('post_musik.html', 
                         song=song_dict, 
                         playlist=playlist_with_user, 
                         database_songs=database_songs_with_user,
                         recommendations=recommendations_with_user,
                         likes_count=likes_count,
                         comments=comments,
                         is_liked=is_liked,
                         total_duration_minutes=total_duration_minutes, 
                         total_duration_seconds=total_duration_seconds)

@web_pages.route('/post_image/<int:image_id>')
def post_image(image_id):
    # Fetch image data from database
    image = Image.query.get_or_404(image_id)
    
    # Get user who posted the image
    user = db.session.get(User, image.user_id)
    
    # Get likes count for this image
    likes_count = Like.query.filter_by(content_type='image', content_id=str(image.id)).count()
    
    # Get comments for this image (only parent comments, not replies)
    comments = Comment.query.filter_by(
        content_type='image', 
        content_id=str(image.id),
        parent_id=None  # Only get parent comments
    ).order_by(Comment.created_at.desc()).all()
    
    # Check if current user has liked this image
    is_liked = False
    if 'user_id' in session:
        is_liked = Like.query.filter_by(
            user_id=session['user_id'], 
            content_type='image', 
            content_id=str(image.id)
        ).first() is not None
    
    return render_template('post_image.html', 
                         image=image, 
                         user=user, 
                         likes_count=likes_count, 
                         comments=comments, 
                         is_liked=is_liked)

@web_pages.route('/post_video/<int:video_id>')
def post_video(video_id):
    print(f"=== DEBUG: post_video called for video_id: {video_id} ===")
    
    # Ambil data video dari database
    video = Video.query.get_or_404(video_id)
    print(f"Video found: {video.id} - {video.caption}")
    
    # Ambil user yang mengunggah video
    user = db.session.get(User, video.user_id)
    print(f"Video user: {user.username if user else 'Unknown'}")
    
    # Hitung jumlah like untuk video ini
    likes_count = Like.query.filter_by(content_type='video', content_id=str(video.id)).count()
    print(f"Likes count: {likes_count}")
    
    # Ambil komentar untuk video ini (only parent comments, not replies)
    comments = Comment.query.filter_by(
        content_type='video', 
        content_id=str(video.id),
        parent_id=None  # Only get parent comments
    ).order_by(Comment.created_at.desc()).all()
    
    print(f"Comments found: {len(comments)}")
    for comment in comments:
        print(f"  - Comment {comment.id}: {comment.text[:50]}... by user {comment.user.username if comment.user else 'Unknown'}")
    
    # Cek apakah user saat ini sudah like video ini
    is_liked = False
    if 'user_id' in session:
        is_liked = Like.query.filter_by(
            user_id=session['user_id'], 
            content_type='video', 
            content_id=str(video.id)
        ).first() is not None
        print(f"Current user liked: {is_liked}")
    
    return render_template('post_video.html', 
                         video=video, 
                         user=user, 
                         likes_count=likes_count, 
                         comments=comments, 
                         is_liked=is_liked)

@web_pages.route('/post_video_iklan/<int:video_id>')
def post_video_iklan(video_id):
    video_iklan = VideoIklan.query.get_or_404(video_id)
    user = db.session.get(User, video_iklan.user_id)
    likes_count = Like.query.filter_by(content_type='video_iklan', content_id=str(video_iklan.id)).count()
    comments = Comment.query.filter_by(
        content_type='video_iklan', 
        content_id=str(video_iklan.id),
        parent_id=None  # Only get parent comments
    ).order_by(Comment.created_at.desc()).all()
    is_liked = False
    if 'user_id' in session:
        is_liked = Like.query.filter_by(
            user_id=session['user_id'], 
            content_type='video_iklan', 
            content_id=str(video_iklan.id)
        ).first() is not None
    return render_template('post_video_iklan.html', video_iklan=video_iklan, user=user, likes_count=likes_count, comments=comments, is_liked=is_liked)

@web_pages.route('/regenerate_image/<int:image_id>', methods=['POST'])
def regenerate_image(image_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in', 'error': 'Not logged in'}), 401
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found', 'error': 'User not found'}), 404
    if user.kredit < 15:
        return jsonify({'success': False, 'message': 'Kredit Anda tidak cukup untuk generate gambar (minimal 15)', 'error': 'Kredit Anda tidak cukup untuk generate gambar (minimal 15)'}), 403
    image = Image.query.get_or_404(image_id)
    data = request.get_json()
    new_prompt = data.get('prompt')
    aspect_ratio = data.get('aspect_ratio', '1:1')
    negative_prompt = data.get('negative_prompt', '')
    if not new_prompt:
        return jsonify({'success': False, 'message': 'Prompt tidak boleh kosong', 'error': 'Prompt tidak boleh kosong'}), 400

    import requests, time
    API_KEY = current_app.config.get('WAVESPEED_API_KEY')
    if not API_KEY:
        return jsonify({'success': False, 'message': 'API key tidak ditemukan', 'error': 'API key tidak ditemukan'}), 500
    # Use nano-banana model for regenerate
    url = 'https://api.wavespeed.ai/api/v3/google/nano-banana/text-to-image'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}',
    }
    payload = {
        'enable_base64_output': False,
        'enable_sync_mode': False,
        'output_format': 'png',
        'prompt': new_prompt
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f'Gagal request API: {response.text}')
        result = response.json().get('data')
        if not result or 'id' not in result:
            raise Exception('Response API tidak valid')
        request_id = result['id']
        # Polling status
        result_url = f'https://api.wavespeed.ai/api/v3/predictions/{request_id}/result'
        headers_result = {'Authorization': f'Bearer {API_KEY}'}
        image_url = None
        for _ in range(60):
            resp = requests.get(result_url, headers=headers_result)
            if resp.status_code == 200:
                res = resp.json().get('data')
                if res:
                    status = res.get('status')
                    if status == 'completed':
                        outputs = res.get('outputs', [])
                        if outputs:
                            image_url = outputs[0] if isinstance(outputs[0], str) else outputs[0].get('url')
                            break
                        else:
                            raise Exception('Tidak ada output gambar yang dihasilkan')
                    elif status == 'failed':
                        raise Exception(f'Task gagal: {res.get("error", "Unknown error")}')
            else:
                raise Exception(f'Gagal polling: {resp.text}')
            time.sleep(0.5)
        if not image_url:
            raise Exception('Timeout menunggu hasil generate')
        # Update DB
        user.kredit -= 15
        image.caption = new_prompt
        image.image_url = image_url
        db.session.commit()
        return jsonify({'success': True, 'message': 'Foto berhasil di-generate ulang dan diperbarui', 'image_url': image_url, 'caption': new_prompt, 'error': None})
    except Exception as e:
        # Fallback: only update caption, keep old image_url
        try:
            user.kredit -= 15
            image.caption = new_prompt
            db.session.commit()
        except Exception as e2:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Gagal update database', 'image_url': image.image_url, 'caption': new_prompt, 'error': str(e2)}), 500
        return jsonify({'success': False, 'message': f'Gagal generate gambar baru: {str(e)} (caption tetap diperbarui)', 'image_url': image.image_url, 'caption': new_prompt, 'error': str(e)}), 500

# In-memory playlist storage
playlist = []

@web_pages.route('/add', methods=['POST'])
def add_song():
    """Add a song to the playlist"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body tidak boleh kosong',
                'playlist': playlist
            }), 400
        
        lagu = data.get('lagu', '').strip()
        if not lagu:
            return jsonify({
                'status': 'error',
                'message': 'Judul lagu tidak boleh kosong',
                'playlist': playlist
            }), 400
        
        # Check if song already exists
        if lagu in playlist:
            return jsonify({
                'status': 'error',
                'message': f'Lagu "{lagu}" sudah ada di playlist',
                'playlist': playlist
            }), 400
        
        # Add song to playlist
        playlist.append(lagu)
        
        return jsonify({
            'status': 'success',
            'message': f'Lagu "{lagu}" berhasil ditambahkan ke playlist',
            'playlist': playlist
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}',
            'playlist': playlist
        }), 500

@web_pages.route('/remove', methods=['POST'])
def remove_song():
    """Remove a song from the playlist"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body tidak boleh kosong',
                'playlist': playlist
            }), 400
        
        lagu = data.get('lagu', '').strip()
        if not lagu:
            return jsonify({
                'status': 'error',
                'message': 'Judul lagu tidak boleh kosong',
                'playlist': playlist
            }), 400
        
        # Check if song exists in playlist
        if lagu not in playlist:
            return jsonify({
                'status': 'error',
                'message': f'Lagu "{lagu}" tidak ditemukan di playlist',
                'playlist': playlist
            }), 404
        
        # Remove song from playlist
        playlist.remove(lagu)
        
        return jsonify({
            'status': 'success',
            'message': f'Lagu "{lagu}" berhasil dihapus dari playlist',
            'playlist': playlist
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}',
            'playlist': playlist
        }), 500

@web_pages.route('/playlist', methods=['GET'])
def get_playlist():
    """Get all songs in the playlist"""
    try:
        return jsonify({
            'status': 'success',
            'message': f'Playlist berhasil diambil ({len(playlist)} lagu)',
            'playlist': playlist
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}',
            'playlist': []
        }), 500

@web_pages.route('/download_image/<int:image_id>')
def download_image(image_id):
    """Download image - only for the image owner"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not logged in'}), 401
    
    user_id = session['user_id']
    
    # Get image from database
    image = Image.query.get(image_id)
    if not image:
        return jsonify({'success': False, 'error': 'Image not found'}), 404
    
    # Check if user owns this image
    if image.user_id != user_id:
        return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
    
    try:
        # Get image URL
        image_url = image.image_url
        if not image_url:
            return jsonify({'success': False, 'error': 'Image URL not found'}), 404
        
        # Download image from URL
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        
        # Get filename from URL or use default
        parsed_url = urlparse(image_url)
        filename = os.path.basename(parsed_url.path)
        if not filename or '.' not in filename:
            filename = f"image_{image_id}.jpg"
        
        # Create response with proper headers
        from io import BytesIO
        image_data = BytesIO(response.content)
        
        return send_file(
            image_data,
            mimetype='image/jpeg',
            as_attachment=True,
            download_name=filename
        )
        
    except requests.RequestException as e:
        return jsonify({'success': False, 'error': f'Failed to download image: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@web_pages.route('/download_video/<int:video_id>')
def download_video(video_id):
    """Download video - only for the video owner"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not logged in'}), 401
    
    user_id = session['user_id']
    
    # Get video from database
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'success': False, 'error': 'Video not found'}), 404
    
    # Check if user owns this video
    if video.user_id != user_id:
        return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
    
    try:
        # Get video URL
        video_url = video.video_url
        if not video_url:
            return jsonify({'success': False, 'error': 'Video URL not found'}), 404
        
        # Download video from URL
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        
        # Get filename from URL or use default
        parsed_url = urlparse(video_url)
        filename = os.path.basename(parsed_url.path)
        if not filename or '.' not in filename:
            filename = f"video_{video_id}.mp4"
        
        # Create response with proper headers
        from io import BytesIO
        video_data = BytesIO(response.content)
        
        return send_file(
            video_data,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=filename
        )
        
    except requests.RequestException as e:
        return jsonify({'success': False, 'error': f'Failed to download video: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@web_pages.route('/user_profile/<int:user_id>')
def user_profile_by_id(user_id):
    """User profile page"""
    try:
        # Get the profile user
        profile_user = User.query.get(user_id)
        if not profile_user:
            return "User not found", 404
        
        # Get current user
        current_user_id = session.get('user_id')
        current_user = User.query.get(current_user_id) if current_user_id else None
        
        # Check if current user is following this profile user
        is_following = False
        if current_user_id and current_user_id != user_id:
            existing_follow = Follow.query.filter_by(
                follower_id=current_user_id,
                following_id=user_id
            ).first()
            is_following = existing_follow is not None
        
        # Get user's content counts
        image_count = Image.query.filter_by(user_id=user_id).count()
        video_count = Video.query.filter_by(user_id=user_id).count()
        song_count = Song.query.filter_by(user_id=user_id).count()
        
        # Get user's content (latest 20 of each type)
        images = Image.query.filter_by(user_id=user_id).order_by(Image.created_at.desc()).limit(20).all()
        videos = Video.query.filter_by(user_id=user_id).order_by(Video.created_at.desc()).limit(20).all()
        songs = Song.query.filter_by(user_id=user_id).order_by(Song.created_at.desc()).limit(20).all()
        
        # Add user info and counts to content
        for image in images:
            image.user = profile_user
            image.likes_count = Like.query.filter_by(content_type='image', content_id=str(image.id)).count()
            image.comments_count = Comment.query.filter_by(content_type='image', content_id=str(image.id)).count()
            image.is_following = is_following
        
        for video in videos:
            video.user = profile_user
            video.likes_count = Like.query.filter_by(content_type='video', content_id=str(video.id)).count()
            video.comments_count = Comment.query.filter_by(content_type='video', content_id=str(video.id)).count()
            video.is_following = is_following
        
        for song in songs:
            song.user = profile_user
            song.likes_count = Like.query.filter_by(content_type='song', content_id=str(song.id)).count()
            song.comments_count = Comment.query.filter_by(content_type='song', content_id=str(song.id)).count()
            song.is_following = is_following
        
        return render_template('profile.html', 
                             profile_user=profile_user,
                             current_user=current_user,
                             is_following=is_following,
                             image_count=image_count,
                             video_count=video_count,
                             song_count=song_count,
                             images=images,
                             videos=videos,
                             songs=songs)
        
    except Exception as e:
        print(f"Error in user_profile: {e}")
        return "Error loading profile", 500

@web_pages.route('/api/profile/infinite')
def api_profile_infinite():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    content_type = request.args.get('type', 'all')
    
    offset = (page - 1) * per_page
    user_id = session['user_id']
    
    all_media = []
    
    if content_type in ['all', 'image']:
        images = Image.query.filter_by(user_id=user_id).order_by(Image.created_at.desc()).offset(offset).limit(per_page).all()
        for image in images:
            all_media.append({
                'id': image.id,
                'type': 'image',
                'url': image.image_url,
                'caption': image.caption,
                'created_at': image.created_at.isoformat() if image.created_at else None
            })
    
    if content_type in ['all', 'video']:
        videos = Video.query.filter_by(user_id=user_id).order_by(Video.created_at.desc()).offset(offset).limit(per_page).all()
        for video in videos:
            all_media.append({
                'id': video.id,
                'type': 'video',
                'url': video.video_url,
                'caption': video.caption,
                'created_at': video.created_at.isoformat() if video.created_at else None
            })
    
    if content_type in ['all', 'music']:
        songs = Song.query.filter_by(user_id=user_id).order_by(Song.created_at.desc()).offset(offset).limit(per_page).all()
        for song in songs:
            all_media.append({
                'id': song.id,
                'type': 'music',
                'url': song.audio_url,
                'image_url': song.image_url,
                'title': song.title,
                'caption': song.prompt,
                'created_at': song.created_at.isoformat() if song.created_at else None
            })
    
    # Sort by creation date
    all_media.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Check if there are more items
    total_count = 0
    if content_type == 'all':
        total_count = Image.query.filter_by(user_id=user_id).count() + Video.query.filter_by(user_id=user_id).count() + Song.query.filter_by(user_id=user_id).count()
    elif content_type == 'image':
        total_count = Image.query.filter_by(user_id=user_id).count()
    elif content_type == 'video':
        total_count = Video.query.filter_by(user_id=user_id).count()
    elif content_type == 'music':
        total_count = Song.query.filter_by(user_id=user_id).count()
    
    has_more = (page * per_page) < total_count
    
    return jsonify({
        'success': True,
        'items': all_media,
        'has_more': has_more,
        'page': page,
        'total_count': total_count
    })

@web_pages.route('/api/feed')
def api_feed():
    """API endpoint for infinite scroll feed with algorithm-based personalization"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        feed_type = request.args.get('type', 'for_you')  # for_you, following, trending
        
        user_id = session['user_id']
        current_user = User.query.get(user_id)
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Algorithm-based feed logic
        if feed_type == 'for_you':
            # Personalized feed based on user preferences and engagement
            media_items = get_personalized_feed(current_user, page, per_page)
        elif feed_type == 'following':
            # Feed from followed users only
            media_items = get_following_feed(current_user, page, per_page)
        elif feed_type == 'trending':
            # Trending content based on engagement
            media_items = get_trending_feed(page, per_page)
        else:
            # Default to for_you
            media_items = get_personalized_feed(current_user, page, per_page)
        
        return jsonify({
            'success': True,
            'items': media_items,
            'has_more': len(media_items) == per_page,
            'next_page': page + 1 if len(media_items) == per_page else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_personalized_feed(user, page, per_page):
    """Get personalized feed based on user preferences and engagement"""
    offset = (page - 1) * per_page
    
    # Get user's following list
    following_ids = [f.following_id for f in user.following.all()]
    
    # Get user's engagement history (likes, comments)
    user_likes = Like.query.filter_by(user_id=user.id).all()
    liked_content_types = [like.content_type for like in user_likes]
    
    # Build personalized query
    # Priority: Following users > Liked content types > Recent content
    from sqlalchemy import text
    
    query = text("""
        SELECT 
            'image' as content_type,
            id as content_id,
            image_url as url,
            caption,
            created_at,
            user_id,
            view_count
        FROM images 
        WHERE user_id IN :following_ids OR user_id = :user_id
        UNION ALL
        SELECT 
            'video' as content_type,
            id as content_id,
            video_url as url,
            caption,
            created_at,
            user_id,
            view_count
        FROM videos 
        WHERE user_id IN :following_ids OR user_id = :user_id
        UNION ALL
        SELECT 
            'song' as content_type,
            id as content_id,
            audio_url as url,
            prompt as caption,
            created_at,
            user_id,
            view_count
        FROM songs 
        WHERE user_id IN :following_ids OR user_id = :user_id
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    
    result = db.session.execute(query, {
        'following_ids': tuple(following_ids) if following_ids else (0,),
        'user_id': user.id,
        'limit': per_page,
        'offset': offset
    })
    
    media_items = []
    for row in result:
        # Get user info
        content_user = User.query.get(row.user_id)
        
        # Get engagement counts
        likes_count = Like.query.filter_by(
            content_type=row.content_type, 
            content_id=str(row.content_id)
        ).count()
        
        comments_count = Comment.query.filter_by(
            content_type=row.content_type, 
            content_id=str(row.content_id)
        ).count()
        
        # Check if current user has liked this content
        is_liked = Like.query.filter_by(
            user_id=user.id,
            content_type=row.content_type,
            content_id=str(row.content_id)
        ).first() is not None
        
        media_items.append({
            'id': row.content_id,
            'type': row.content_type,
            'url': row.url,
            'caption': row.caption,
            'created_at': row.created_at.isoformat() if row.created_at else None,
            'user': {
                'id': content_user.id,
                'username': content_user.username,
                'avatar_url': content_user.avatar_url
            } if content_user else None,
            'likes_count': likes_count,
            'comments_count': comments_count,
            'view_count': row.view_count or 0,
            'is_liked': is_liked,
            'is_following': content_user.id in following_ids if content_user else False
        })
    
    return media_items

def get_following_feed(user, page, per_page):
    """Get feed from followed users only"""
    offset = (page - 1) * per_page
    
    # Get user's following list
    following_ids = [f.following_id for f in user.following.all()]
    
    if not following_ids:
        return []
    
    # Get content from followed users
    images = Image.query.filter(Image.user_id.in_(following_ids)).order_by(Image.created_at.desc()).limit(per_page).offset(offset).all()
    videos = Video.query.filter(Video.user_id.in_(following_ids)).order_by(Video.created_at.desc()).limit(per_page).offset(offset).all()
    songs = Song.query.filter(Song.user_id.in_(following_ids)).order_by(Song.created_at.desc()).limit(per_page).offset(offset).all()
    
    media_items = []
    
    # Process images
    for image in images:
        likes_count = Like.query.filter_by(content_type='image', content_id=str(image.id)).count()
        comments_count = Comment.query.filter_by(content_type='image', content_id=str(image.id)).count()
        is_liked = Like.query.filter_by(user_id=user.id, content_type='image', content_id=str(image.id)).first() is not None
        
        media_items.append({
            'id': image.id,
            'type': 'image',
            'url': image.image_url,
            'caption': image.caption,
            'created_at': image.created_at.isoformat() if image.created_at else None,
            'user': {
                'id': image.user.id,
                'username': image.user.username,
                'avatar_url': image.user.avatar_url
            } if image.user else None,
            'likes_count': likes_count,
            'comments_count': comments_count,
            'view_count': image.view_count or 0,
            'is_liked': is_liked,
            'is_following': True
        })
    
    # Process videos
    for video in videos:
        likes_count = Like.query.filter_by(content_type='video', content_id=str(video.id)).count()
        comments_count = Comment.query.filter_by(content_type='video', content_id=str(video.id)).count()
        is_liked = Like.query.filter_by(user_id=user.id, content_type='video', content_id=str(video.id)).first() is not None
        
        media_items.append({
            'id': video.id,
            'type': 'video',
            'url': video.video_url,
            'caption': video.caption,
            'created_at': video.created_at.isoformat() if video.created_at else None,
            'user': {
                'id': video.user.id,
                'username': video.user.username,
                'avatar_url': video.user.avatar_url
            } if video.user else None,
            'likes_count': likes_count,
            'comments_count': comments_count,
            'view_count': video.view_count or 0,
            'is_liked': is_liked,
            'is_following': True
        })
    
    # Process songs
    for song in songs:
        likes_count = Like.query.filter_by(content_type='song', content_id=song.id).count()
        comments_count = Comment.query.filter_by(content_type='song', content_id=song.id).count()
        is_liked = Like.query.filter_by(user_id=user.id, content_type='song', content_id=song.id).first() is not None
        
        media_items.append({
            'id': song.id,
            'type': 'song',
            'url': song.audio_url,
            'image_url': song.image_url,
            'title': song.title,
            'caption': song.prompt,
            'created_at': song.created_at.isoformat() if song.created_at else None,
            'user': {
                'id': song.user.id,
                'username': song.user.username,
                'avatar_url': song.user.avatar_url
            } if song.user else None,
            'likes_count': likes_count,
            'comments_count': comments_count,
            'view_count': song.view_count or 0,
            'is_liked': is_liked,
            'is_following': True
        })
    
    # Sort by creation date
    media_items.sort(key=lambda x: x['created_at'], reverse=True)
    return media_items[:per_page]

def get_trending_feed(page, per_page):
    """Get trending content based on engagement"""
    offset = (page - 1) * per_page
    
    # Get trending content based on likes and views
    from sqlalchemy import text
    
    query = text("""
        SELECT 
            'image' as content_type,
            i.id as content_id,
            i.image_url as url,
            i.caption,
            i.created_at,
            i.user_id,
            i.view_count,
            COUNT(l.id) as likes_count
        FROM images i
        LEFT JOIN likes l ON l.content_type = 'image' AND l.content_id = CAST(i.id AS VARCHAR)
        GROUP BY i.id, i.image_url, i.caption, i.created_at, i.user_id, i.view_count
        UNION ALL
        SELECT 
            'video' as content_type,
            v.id as content_id,
            v.video_url as url,
            v.caption,
            v.created_at,
            v.user_id,
            v.view_count,
            COUNT(l.id) as likes_count
        FROM videos v
        LEFT JOIN likes l ON l.content_type = 'video' AND l.content_id = CAST(v.id AS VARCHAR)
        GROUP BY v.id, v.video_url, v.caption, v.created_at, v.user_id, v.view_count
        UNION ALL
        SELECT 
            'song' as content_type,
            s.id as content_id,
            s.audio_url as url,
            s.prompt as caption,
            s.created_at,
            s.user_id,
            s.view_count,
            COUNT(l.id) as likes_count
        FROM songs s
        LEFT JOIN likes l ON l.content_type = 'song' AND l.content_id = s.id
        GROUP BY s.id, s.audio_url, s.prompt, s.created_at, s.user_id, s.view_count
        ORDER BY likes_count DESC, view_count DESC, created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    
    result = db.session.execute(query, {
        'limit': per_page,
        'offset': offset
    })
    
    media_items = []
    for row in result:
        content_user = User.query.get(row.user_id)
        
        comments_count = Comment.query.filter_by(
            content_type=row.content_type, 
            content_id=str(row.content_id)
        ).count()
        
        media_items.append({
            'id': row.content_id,
            'type': row.content_type,
            'url': row.url,
            'caption': row.caption,
            'created_at': row.created_at.isoformat() if row.created_at else None,
            'user': {
                'id': content_user.id,
                'username': content_user.username,
                'avatar_url': content_user.avatar_url
            } if content_user else None,
            'likes_count': row.likes_count or 0,
            'comments_count': comments_count,
            'view_count': row.view_count or 0,
            'is_liked': False,  # Will be updated by frontend
            'is_following': False  # Will be updated by frontend
        })
    
    return media_items

@web_pages.route('/explore')
def explore():
    """Explore page for discovering new content"""
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    
    # Simple in-memory cache check (5 minutes)
    cache_time = 300  # 5 minutes
    
    # Check if we have cached data
    if hasattr(explore, '_cache') and hasattr(explore, '_cache_time'):
        if time.time() - explore._cache_time < cache_time:
            return render_template('explore.html', **explore._cache)
    
    # Super simple queries without any complex relationships
    try:
        current_user_id = session.get('user_id')
        
        # Get basic content without any joins - optimized, exclude current user's content
        if current_user_id:
            # New content (latest)
            new_images = db.session.query(Image).filter(Image.user_id != current_user_id).order_by(Image.created_at.desc()).limit(20).all()
            new_videos = db.session.query(Video).filter(Video.user_id != current_user_id).order_by(Video.created_at.desc()).limit(20).all()
            new_songs = db.session.query(Song).filter(Song.user_id != current_user_id).order_by(Song.created_at.desc()).limit(20).all()
            
            # Trending content (by view count)
            trending_images = db.session.query(Image).filter(Image.user_id != current_user_id).order_by(Image.view_count.desc()).limit(20).all()
            trending_videos = db.session.query(Video).filter(Video.user_id != current_user_id).order_by(Video.view_count.desc()).limit(20).all()
            trending_songs = db.session.query(Song).filter(Song.user_id != current_user_id).order_by(Song.view_count.desc()).limit(20).all()
        else:
            # New content (latest)
            new_images = db.session.query(Image).order_by(Image.created_at.desc()).limit(20).all()
            new_videos = db.session.query(Video).order_by(Video.created_at.desc()).limit(20).all()
            new_songs = db.session.query(Song).order_by(Song.created_at.desc()).limit(20).all()
            
            # Trending content (by view count)
            trending_images = db.session.query(Image).order_by(Image.view_count.desc()).limit(20).all()
            trending_videos = db.session.query(Video).order_by(Video.view_count.desc()).limit(20).all()
            trending_songs = db.session.query(Song).order_by(Song.view_count.desc()).limit(20).all()
        
        # Add user info manually for new content
        for image in new_images:
            try:
                image.user = db.session.query(User).filter_by(id=image.user_id).first()
                image.likes_count = db.session.query(Like).filter_by(content_type='image', content_id=str(image.id)).count()
                image.comments_count = db.session.query(Comment).filter_by(content_type='image', content_id=str(image.id)).count()
                
                # Check if current user is following this content's user
                if current_user_id and image.user:
                    existing_follow = db.session.query(Follow).filter_by(
                        follower_id=current_user_id,
                        following_id=image.user.id
                    ).first()
                    image.is_following = existing_follow is not None
                else:
                    image.is_following = False
            except Exception as e:
                print(f"Error processing new image {image.id}: {e}")
                image.user = None
                image.likes_count = 0
                image.comments_count = 0
                image.is_following = False
        
        for video in new_videos:
            try:
                video.user = db.session.query(User).filter_by(id=video.user_id).first()
                video.likes_count = db.session.query(Like).filter_by(content_type='video', content_id=str(video.id)).count()
                video.comments_count = db.session.query(Comment).filter_by(content_type='video', content_id=str(video.id)).count()
                
                # Check if current user is following this content's user
                if current_user_id and video.user:
                    existing_follow = db.session.query(Follow).filter_by(
                        follower_id=current_user_id,
                        following_id=video.user.id
                    ).first()
                    video.is_following = existing_follow is not None
                else:
                    video.is_following = False
            except Exception as e:
                print(f"Error processing new video {video.id}: {e}")
                video.user = None
                video.likes_count = 0
                video.comments_count = 0
                video.is_following = False
        
        for song in new_songs:
            try:
                song.user = db.session.query(User).filter_by(id=song.user_id).first()
                song.likes_count = db.session.query(Like).filter_by(content_type='song', content_id=str(song.id)).count()
                song.comments_count = db.session.query(Comment).filter_by(content_type='song', content_id=str(song.id)).count()
                
                # Check if current user is following this content's user
                if current_user_id and song.user:
                    existing_follow = db.session.query(Follow).filter_by(
                        follower_id=current_user_id,
                        following_id=song.user.id
                    ).first()
                    song.is_following = existing_follow is not None
                else:
                    song.is_following = False
            except Exception as e:
                print(f"Error processing new song {song.id}: {e}")
                song.user = None
                song.likes_count = 0
                song.comments_count = 0
                song.is_following = False
        
        # Add user info manually for trending content
        for image in trending_images:
            try:
                image.user = db.session.query(User).filter_by(id=image.user_id).first()
                image.likes_count = db.session.query(Like).filter_by(content_type='image', content_id=str(image.id)).count()
                image.comments_count = db.session.query(Comment).filter_by(content_type='image', content_id=str(image.id)).count()
                
                # Check if current user is following this content's user
                if current_user_id and image.user:
                    existing_follow = db.session.query(Follow).filter_by(
                        follower_id=current_user_id,
                        following_id=image.user.id
                    ).first()
                    image.is_following = existing_follow is not None
                else:
                    image.is_following = False
            except Exception as e:
                print(f"Error processing image {image.id}: {e}")
                image.user = None
                image.likes_count = 0
                image.comments_count = 0
                image.is_following = False
        
        for video in trending_videos:
            try:
                video.user = db.session.query(User).filter_by(id=video.user_id).first()
                video.likes_count = db.session.query(Like).filter_by(content_type='video', content_id=str(video.id)).count()
                video.comments_count = db.session.query(Comment).filter_by(content_type='video', content_id=str(video.id)).count()
                
                # Check if current user is following this content's user
                if current_user_id and video.user:
                    existing_follow = db.session.query(Follow).filter_by(
                        follower_id=current_user_id,
                        following_id=video.user.id
                    ).first()
                    video.is_following = existing_follow is not None
                else:
                    video.is_following = False
            except Exception as e:
                print(f"Error processing video {video.id}: {e}")
                video.user = None
                video.likes_count = 0
                video.comments_count = 0
                video.is_following = False
        
        for song in trending_songs:
            try:
                song.user = db.session.query(User).filter_by(id=song.user_id).first()
                song.likes_count = db.session.query(Like).filter_by(content_type='song', content_id=str(song.id)).count()
                song.comments_count = db.session.query(Comment).filter_by(content_type='song', content_id=str(song.id)).count()
                
                # Check if current user is following this content's user
                if current_user_id and song.user:
                    existing_follow = db.session.query(Follow).filter_by(
                        follower_id=current_user_id,
                        following_id=song.user.id
                    ).first()
                    song.is_following = existing_follow is not None
                else:
                    song.is_following = False
            except Exception as e:
                print(f"Error processing song {song.id}: {e}")
                song.user = None
                song.likes_count = 0
                song.comments_count = 0
                song.is_following = False
                
    except Exception as e:
        print(f"Error in explore route: {e}")
        trending_images = []
        trending_videos = []
        trending_songs = []
    
    # Super simplified creators query - only get top 4 creators
    try:
        from sqlalchemy import func, text
        
        # Exclude current user from popular creators
        if current_user_id:
            popular_creators_query = text("""
                SELECT 
                    u.id, u.username, u.avatar_url,
                    COALESCE(i_count.count, 0) as image_count,
                    COALESCE(v_count.count, 0) as video_count,
                    COALESCE(s_count.count, 0) as song_count
                FROM users u
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as count 
                    FROM images 
                    GROUP BY user_id
                ) i_count ON u.id = i_count.user_id
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as count 
                    FROM videos 
                    GROUP BY user_id
                ) v_count ON u.id = v_count.user_id
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as count 
                    FROM songs 
                    GROUP BY user_id
                ) s_count ON u.id = s_count.user_id
                WHERE (i_count.count > 0 OR v_count.count > 0 OR s_count.count > 0)
                AND u.id != :current_user_id
                ORDER BY (COALESCE(i_count.count, 0) + COALESCE(v_count.count, 0) + COALESCE(s_count.count, 0)) DESC
                LIMIT 4
            """)
            popular_creators_result = db.session.execute(popular_creators_query, {'current_user_id': current_user_id})
        else:
            popular_creators_query = text("""
                SELECT 
                    u.id, u.username, u.avatar_url,
                    COALESCE(i_count.count, 0) as image_count,
                    COALESCE(v_count.count, 0) as video_count,
                    COALESCE(s_count.count, 0) as song_count
                FROM users u
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as count 
                    FROM images 
                    GROUP BY user_id
                ) i_count ON u.id = i_count.user_id
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as count 
                    FROM videos 
                    GROUP BY user_id
                ) v_count ON u.id = v_count.user_id
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as count 
                    FROM songs 
                    GROUP BY user_id
                ) s_count ON u.id = s_count.user_id
                WHERE (i_count.count > 0 OR v_count.count > 0 OR s_count.count > 0)
                ORDER BY (COALESCE(i_count.count, 0) + COALESCE(v_count.count, 0) + COALESCE(s_count.count, 0)) DESC
                LIMIT 4
            """)
            popular_creators_result = db.session.execute(popular_creators_query)
        popular_creators = []
        
        for row in popular_creators_result:
            # Check if current user is following this creator
            is_following = False
            if current_user_id:
                existing_follow = db.session.query(Follow).filter_by(
                    follower_id=current_user_id,
                    following_id=row.id
                ).first()
                is_following = existing_follow is not None
            
            creator_data = {
                'id': row.id,
                'username': row.username,
                'avatar_url': row.avatar_url,
                'image_count': row.image_count,
                'video_count': row.video_count,
                'song_count': row.song_count,
                'is_following': is_following
            }
            popular_creators.append(creator_data)
    except Exception as e:
        print(f"Error getting popular creators: {e}")
        popular_creators = []
    
    # Cache the data
    template_data = {
        'new_images': new_images,
        'new_videos': new_videos,
        'new_songs': new_songs,
        'trending_images': trending_images,
        'trending_videos': trending_videos,
        'trending_songs': trending_songs,
        'popular_creators': popular_creators
    }
    
    explore._cache = template_data
    explore._cache_time = time.time()
    
    return render_template('explore.html', **template_data)



@web_pages.route('/api/like', methods=['POST'])
def api_like():
    """API endpoint for liking/unliking content"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        content_type = data.get('content_type')
        content_id = data.get('content_id')
        user_id = session['user_id']
        
        if not content_type or not content_id:
            return jsonify({'error': 'Missing content_type or content_id'}), 400
        
        # Check if user already liked this content
        existing_like = Like.query.filter_by(
            user_id=user_id,
            content_type=content_type,
            content_id=str(content_id)
        ).first()
        
        if existing_like:
            # Unlike
            db.session.delete(existing_like)
            liked = False
        else:
            # Like
            new_like = Like(
                user_id=user_id,
                content_type=content_type,
                content_id=str(content_id)
            )
            db.session.add(new_like)
            liked = True
        
        db.session.commit()
        
        # Get updated like count
        like_count = Like.query.filter_by(
            content_type=content_type,
            content_id=str(content_id)
        ).count()
        
        return jsonify({
            'success': True,
            'liked': liked,
            'like_count': like_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@web_pages.route('/api/follow', methods=['POST'])
def api_follow():
    """API endpoint for following/unfollowing users"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        target_user_id = data.get('user_id')
        current_user_id = session['user_id']
        
        print(f"DEBUG: Follow request - Current user: {current_user_id}, Target user: {target_user_id}")
        
        if not target_user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        if target_user_id == current_user_id:
            print(f"DEBUG: User trying to follow themselves - Current: {current_user_id}, Target: {target_user_id}")
            return jsonify({'error': 'Cannot follow yourself', 'current_user': current_user_id, 'target_user': target_user_id}), 400
        
        current_user = User.query.get(current_user_id)
        target_user = User.query.get(target_user_id)
        
        print(f"DEBUG: Current user found: {current_user is not None}, Target user found: {target_user is not None}")
        
        if not current_user or not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if already following
        existing_follow = Follow.query.filter_by(
            follower_id=current_user_id,
            following_id=target_user_id
        ).first()
        
        print(f"DEBUG: Existing follow found: {existing_follow is not None}")
        
        if existing_follow:
            # Unfollow
            db.session.delete(existing_follow)
            following = False
            print(f"DEBUG: Unfollowing user {target_user_id}")
        else:
            # Follow
            new_follow = Follow(
                follower_id=current_user_id,
                following_id=target_user_id
            )
            db.session.add(new_follow)
            following = True
            print(f"DEBUG: Following user {target_user_id}")
        
        db.session.commit()
        print(f"DEBUG: Database commit successful")
        
        return jsonify({
            'success': True,
            'following': following
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error in follow API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@web_pages.route('/api/comment', methods=['POST'])
def api_comment():
    """API endpoint for adding comments to content"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        content_type = data.get('content_type')
        content_id = data.get('content_id')
        comment_text = data.get('comment_text')
        user_id = session['user_id']
        
        if not content_type or not content_id or not comment_text:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if len(comment_text.strip()) == 0:
            return jsonify({'error': 'Comment cannot be empty'}), 400
        
        # Create new comment
        new_comment = Comment(
            user_id=user_id,
            content_type=content_type,
            content_id=str(content_id),
            text=comment_text.strip()
        )
        db.session.add(new_comment)
        db.session.commit()
        
        # Get updated comment count
        comment_count = Comment.query.filter_by(
            content_type=content_type,
            content_id=str(content_id)
        ).count()
        
        return jsonify({
            'success': True,
            'comment_count': comment_count,
            'comment': {
                'id': new_comment.id,
                'text': new_comment.text,
                'user_id': new_comment.user_id,
                'created_at': new_comment.created_at.isoformat() if new_comment.created_at else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500