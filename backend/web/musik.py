import os
from flask import Flask, request, jsonify, render_template, send_from_directory, Blueprint, session, make_response
import requests
import time
import json
import glob
import uuid
from models import Song, db
from config import Config
import re
from datetime import datetime

musik_bp = Blueprint('musik', __name__)

# Mengambil konfigurasi dari config.py
SUNO_API_KEY = Config.SUNO_API_KEY
SUNO_BASE_URL = Config.SUNO_BASE_URL
CALLBACK_DOMAIN = Config.CALLBACK_DOMAIN
CALLBACK_RESULT_FILE = 'suno_callback_result.json'

def clean_lyrics_for_suno(lyrics):
    """
    Membersihkan lirik dari kata-kata yang bisa dianggap sebagai nama artis oleh Suno API
    """
    if not lyrics:
        return lyrics
    
    # Daftar kata yang sering dianggap sebagai nama artis oleh Suno
    forbidden_words = [
        'irama', 'rhythm', 'beat', 'melody', 'harmoni', 'harmony',
        'musik', 'music', 'lagu', 'song', 'artis', 'artist',
        'penyanyi', 'singer', 'band', 'group', 'duo', 'trio',
        'rapper', 'mc', 'dj', 'producer', 'composer'
    ]
    
    # Replacement words
    replacements = {
        'irama': 'nada',
        'rhythm': 'tempo', 
        'beat': 'ketukan',
        'melody': 'melodi',
        'harmoni': 'keselarasan',
        'harmony': 'keharmonisan',
        'musik': 'suara',
        'music': 'sound',
        'lagu': 'nyanyian',
        'song': 'tune',
        'artis': 'pencipta',
        'artist': 'creator',
        'penyanyi': 'penyair',
        'singer': 'vocalist',
        'band': 'grup',
        'group': 'kumpulan',
        'duo': 'pasangan',
        'trio': 'tiga serangkai'
    }
    
    # Replace problematic words
    cleaned_lyrics = lyrics
    for word, replacement in replacements.items():
        # Case insensitive replacement
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        cleaned_lyrics = pattern.sub(replacement, cleaned_lyrics)
    
    return cleaned_lyrics

@musik_bp.route('/musik')
def musik_page():
    return render_template('musik.html')

@musik_bp.route('/api/music/test')
def test_music_endpoint():
    """Test endpoint untuk memastikan routing berfungsi"""
    return jsonify({'message': 'Music endpoint working', 'timestamp': datetime.utcnow().isoformat()})

@musik_bp.route('/api/music/debug-session')
def debug_session():
    """Debug endpoint untuk memeriksa session"""
    session_data = {
        'session_id': session.get('session_id'),
        'user_id': session.get('user_id'),
        'all_session_keys': list(session.keys()),
        'timestamp': datetime.utcnow().isoformat()
    }
    return jsonify(session_data)

@musik_bp.route('/api/music/history', methods=['GET'])
def get_music_history():
    """
    Endpoint untuk mengambil history musik dari database
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    try:
        # Ambil musik dari database, urutkan berdasarkan created_at DESC
        songs = Song.query.filter_by(user_id=user_id).order_by(Song.created_at.desc()).limit(20).all()
        
        music_list = []
        for song in songs:
            music_list.append({
                'id': song.id,
                'title': song.title or 'Untitled',
                'duration': song.duration or 0,
                'audio_url': song.audio_url,
                'image_url': song.image_url,
                'cover_url': song.image_url,  # Use image_url as cover
                'lyrics': song.lyrics or '',
                'genre': song.genre or 'AI Generated',
                'mode': song.mode or 'prompt',
                'prompt': song.prompt or '',
                'model_name': song.model_name or 'V4_5PLUS',
                'created_at': song.created_at.isoformat() if song.created_at else None
            })
        
        return jsonify({'success': True, 'music': music_list})
        
    except Exception as e:
        print(f"Error getting music history: {e}")
        return jsonify({'error': 'Gagal mengambil history musik'}), 500

@musik_bp.route('/api/music/download/<song_id>', methods=['GET', 'OPTIONS'])
def download_music(song_id):
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Content-Disposition')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response
    
    """
    Endpoint untuk download musik dengan proper headers
    """
    print(f"🔍 Download request for song_id: {song_id}")
    user_id = session.get('user_id')
    if not user_id:
        print(f"❌ User not logged in")
        return jsonify({'error': 'User belum login'}), 401
    
    try:
        # Ambil song dari database
        print(f"🔍 Querying song with id: {song_id}, user_id: {user_id}")
        
        # Check if song_id is valid UUID format
        try:
            uuid.UUID(song_id)
            print(f"✅ song_id is valid UUID: {song_id}")
        except ValueError:
            print(f"❌ Invalid UUID format: {song_id}")
            return jsonify({'error': 'ID lagu tidak valid'}), 400
        
        # Query database
        try:
            song = Song.query.filter_by(id=song_id, user_id=user_id).first()
            print(f"🔍 Database query completed")
        except Exception as db_error:
            print(f"❌ Database query error: {db_error}")
            return jsonify({'error': 'Database error'}), 500
        
        if not song:
            print(f"❌ Song not found with id: {song_id}")
            return jsonify({'error': 'File tidak ditemukan'}), 404
        
        if not song.audio_url:
            print(f"❌ Song found but no audio_url: {song_id}")
            return jsonify({'error': 'File audio tidak tersedia'}), 404
        
        print(f"✅ Song found: {song.title}, audio_url: {song.audio_url}")
        
        # Extract filename from URL
        filename = song.title or 'music'
        filename = re.sub(r'[^\w\s-]', '', filename)  # Remove special characters
        filename = re.sub(r'[-\s]+', '-', filename)   # Replace spaces with hyphens
        filename = f"{filename}.mp3"
        
        # Get audio file from Suno URL with streaming for faster download
        response = requests.get(song.audio_url, stream=True)
        response.raise_for_status()
        
        # Create streaming response for faster download
        from flask import Response
        
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        
        return Response(
            generate(),
            mimetype='audio/mpeg',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"; filename*=UTF-8\'\'{filename}',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Content-Disposition, Accept, Accept-Encoding, Accept-Language',
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'Accept-Ranges': 'bytes',
                'Content-Transfer-Encoding': 'binary',
                'Transfer-Encoding': 'chunked'
            }
        )
        
    except Exception as e:
        print(f"❌ Error downloading music: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Gagal download file'}), 500

@musik_bp.route('/api/generate-lyrics', methods=['POST'])
def api_generate_lyrics():
    """Generate lirik lagu dari judul menggunakan AI"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User belum login'}), 401
        
        data = request.get_json()
        title = data.get('title', '').strip()
        genre = data.get('genre', 'pop')
        mood = data.get('mood', 'happy')
        persona = data.get('persona', 'female')
        
        if not title:
            return jsonify({'success': False, 'message': 'Judul lagu tidak boleh kosong'})
        
        # Check user credits
        from models import User
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User tidak ditemukan'})
        if user.kredit < 5:
            return jsonify({'success': False, 'message': 'Kredit Anda tidak cukup untuk generate lirik (minimal 5 kredit)'})
        
        # Deduct credits
        user.kredit -= 5
        db.session.commit()
        
        # Generate lirik menggunakan AI
        lyrics = generate_lyrics_from_title(title, genre, mood, persona)
        
        # Suggest genre and mood based on title
        suggested_genre = suggest_genre_from_title(title)
        suggested_mood = suggest_mood_from_title(title)
        suggested_persona = suggest_persona_from_title(title)
        
        return jsonify({
            'success': True,
            'lyrics': lyrics,
            'suggested_genre': suggested_genre,
            'suggested_mood': suggested_mood,
            'suggested_persona': suggested_persona,
            'message': 'Lirik berhasil di-generate!'
        })
        
    except Exception as e:
        print(f"Error in api_generate_lyrics: {e}")
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500

@musik_bp.route('/api/generate', methods=['POST'])
def api_generate_music():
    """
    Endpoint API untuk generate musik dari berbagai mode (lyrics, image, prompt)
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User belum login'}), 401
        
        data = request.get_json()
        mode = data.get('mode')  # 'lyrics', 'image', 'prompt'
        
        if mode == 'lyrics':
            return handle_lyrics_generation(data)
        elif mode == 'image':
            return handle_image_generation(data)
        elif mode == 'prompt':
            return handle_prompt_generation(data)
        else:
            return jsonify({'success': False, 'message': 'Mode tidak valid'}), 400
            
    except Exception as e:
        print(f"Error in api_generate_music: {e}")
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500

def extract_title_from_analysis(description, lyrics):
    """Extract judul musik dari hasil analisis AI atau prompt"""
    try:
        # Cari kata kunci untuk tema utama dari deskripsi/prompt
        description_lower = description.lower()
        lyrics_lower = lyrics.lower() if lyrics else ""
        
        # Coba ekstrak judul dari baris pertama yang bermakna
        lines = [line.strip() for line in description.split('\n') if line.strip()]
        for line in lines:
            line_clean = line.strip()
            # Skip baris yang tidak cocok untuk judul
            if (line_clean.startswith('[') and line_clean.endswith(']')) or \
               line_clean.lower() in ['verse', 'chorus', 'bridge', 'intro', 'outro', 'verse 1', 'chorus 1'] or \
               len(line_clean) < 3 or len(line_clean) > 50:
                continue
            
            # Jika baris ini cocok untuk judul, gunakan
            if len(line_clean) >= 3 and len(line_clean) <= 50:
                # Bersihkan karakter khusus
                clean_title = re.sub(r'[^\w\s\-]', '', line_clean)
                clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                
                if clean_title and len(clean_title) >= 3:
                    return clean_title
        
        # Keywords untuk tema yang bisa dijadikan judul
        if "malam" in description_lower or "night" in description_lower:
            if "gemerlap" in description_lower or "kilau" in description_lower:
                return "Gemerlap Malam"
            elif "pesta" in description_lower or "club" in description_lower or "klub" in description_lower:
                return "Raja Malam"
            elif "dj" in description_lower or "panggung" in description_lower:
                return "Panggung Sandiwara"
            else:
                return "Malam yang Indah"
        
        elif "cahaya" in description_lower or "lampu" in description_lower:
            if "neon" in description_lower:
                return "Cahaya Neon"
            elif "panggung" in description_lower:
                return "Sorot Lampu Panggung"
            else:
                return "Dalam Cahaya"
        
        elif "dansa" in description_lower or "dance" in description_lower:
            return "Lantai Dansa"
        
        elif "berlari" in description_lower or "running" in description_lower:
            return "Lari di Pagi"
        
        elif "berjalan" in description_lower or "walking" in description_lower:
            return "Jalan Santai"
        
        elif "berenang" in description_lower or "swimming" in description_lower:
            return "Berenang di Laut"
        
        elif "terbang" in description_lower or "flying" in description_lower:
            return "Terbang Bebas"
        
        elif "menari" in description_lower or "dancing" in description_lower:
            return "Tarian Jiwa"
        
        elif "bernyanyi" in description_lower or "singing" in description_lower:
            return "Nyanyian Hati"
        
        elif "bermain" in description_lower or "playing" in description_lower:
            return "Permainan Ceria"
        
        elif "musik" in description_lower or "music" in description_lower:
            return "Irama Jiwa"
        
        elif "bidadari" in description_lower or "angel" in description_lower:
            return "Bidadari Malam"
        
        elif "raja" in description_lower or "king" in description_lower:
            return "Raja Malam"
        
        elif "mimpi" in description_lower or "dream" in description_lower:
            return "Mimpi dalam Musik"
        
        elif "cinta" in description_lower or "love" in description_lower:
            return "Melodi Cinta"
        
        # Coba ekstrak kata kunci dari prompt untuk membuat judul yang lebih spesifik
        words = description_lower.split()
        if len(words) >= 2:
            # Ambil 2-3 kata pertama yang bermakna
            meaningful_words = []
            skip_words = ['buat', 'create', 'generate', 'musik', 'music', 'lagu', 'song', 'yang', 'yang', 'untuk', 'for', 'dengan', 'with', 'adalah', 'is', 'a', 'an', 'the']
            
            for word in words[:5]:  # Ambil 5 kata pertama
                if word not in skip_words and len(word) > 2:
                    meaningful_words.append(word.capitalize())
                    if len(meaningful_words) >= 2:
                        break
            
            if meaningful_words:
                return " ".join(meaningful_words)
        
        # Default berdasarkan mood umum
        if any(word in description_lower for word in ["energik", "semangat", "powerful", "energetic"]):
            return "Energi Tak Terbatas"
        elif any(word in description_lower for word in ["romantis", "romantic", "sweet", "love"]):
            return "Kisah Romantis"
        elif any(word in description_lower for word in ["sedih", "melankolis", "sad", "melancholic"]):
            return "Lagu Hati"
        elif any(word in description_lower for word in ["bahagia", "happy", "joyful", "gembira"]):
            return "Lagu Bahagia"
        elif any(word in description_lower for word in ["tenang", "calm", "peaceful", "damai"]):
            return "Lagu Tenang"
        else:
            # Ambil kata pertama yang bermakna dari prompt
            first_meaningful = None
            for word in words:
                if len(word) > 3 and word not in ['buat', 'create', 'generate', 'musik', 'music', 'lagu', 'song']:
                    first_meaningful = word.capitalize()
                    break
            
            if first_meaningful:
                return f"Musik {first_meaningful}"
            else:
                return "Karya Musik Baru"
            
    except Exception as e:
        return "Musik dari Gambar"

def extract_title_from_lyrics(lyrics, genre, mood, persona):
    """Extract judul musik dari lirik lagu yang diinput user"""
    try:
        if not lyrics:
            return "Lagu Tanpa Judul"
        
        lyrics_lower = lyrics.lower()
        genre_lower = genre.lower() if genre else ""
        mood_lower = mood.lower() if mood else ""
        persona_lower = persona.lower() if persona else ""
        
        # Cari baris pertama yang bermakna (biasanya chorus atau verse pertama)
        lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
        
        # Cari baris yang cocok untuk judul
        for line in lines:
            line_clean = line.strip()
            # Skip baris yang tidak cocok untuk judul
            if (line_clean.startswith('[') and line_clean.endswith(']')) or \
               line_clean.lower() in ['verse', 'chorus', 'bridge', 'intro', 'outro', 'verse 1', 'chorus 1'] or \
               len(line_clean) < 3 or len(line_clean) > 50:
                continue
            
            # Jika baris ini cocok untuk judul, gunakan
            if len(line_clean) >= 3 and len(line_clean) <= 50:
                # Bersihkan karakter khusus
                clean_title = re.sub(r'[^\w\s\-]', '', line_clean)
                clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                
                if clean_title and len(clean_title) >= 3:
                    return clean_title
        
        # Cari kata kunci emosional yang bisa dijadikan judul
        emotional_keywords = {
            'bahagia': 'Lagu Bahagia',
            'gembira': 'Lagu Gembira',
            'sukacita': 'Lagu Sukacita',
            'senang': 'Lagu Senang',
            'sedih': 'Lagu Sedih',
            'duka': 'Lagu Duka',
            'pilu': 'Lagu Pilu',
            'haru': 'Lagu Haru',
            'semangat': 'Lagu Semangat',
            'energik': 'Lagu Energik',
            'berapi': 'Lagu Berapi',
            'tenang': 'Lagu Tenang',
            'damai': 'Lagu Damai',
            'sejuk': 'Lagu Sejuk',
            'romantis': 'Lagu Romantis',
            'mesra': 'Lagu Mesra',
            'manis': 'Lagu Manis',
            'misterius': 'Lagu Misterius',
            'gelap': 'Lagu Gelap',
            'nostalgia': 'Lagu Nostalgia',
            'kenangan': 'Lagu Kenangan',
            'epik': 'Lagu Epik',
            'dramatis': 'Lagu Dramatis',
            'funky': 'Lagu Funky',
            'groovy': 'Lagu Groovy',
            'mimpi': 'Lagu Mimpi',
            'khayalan': 'Lagu Khayalan',
            'agresif': 'Lagu Agresif',
            'keras': 'Lagu Keras',
            'melankolis': 'Lagu Melankolis',
            'reflektif': 'Lagu Reflektif'
        }
        
        # Cek kata kunci emosional
        for keyword, title in emotional_keywords.items():
            if keyword in lyrics_lower:
                return title
        
        # Jika tidak ada baris yang cocok, buat judul berdasarkan tema
        if "cinta" in lyrics_lower or "love" in lyrics_lower or "kasih" in lyrics_lower:
            if "romantis" in mood_lower or "romantic" in mood_lower:
                return "Melodi Cinta Romantis"
            elif "sedih" in mood_lower or "sad" in mood_lower:
                return "Lagu Cinta yang Hilang"
            elif "energik" in mood_lower or "energetic" in mood_lower:
                return "Cinta yang Berapi"
            else:
                return "Melodi Cinta"
        
        elif "malam" in lyrics_lower or "night" in lyrics_lower:
            if "pesta" in lyrics_lower or "party" in lyrics_lower:
                return "Pesta Malam"
            elif "sepi" in lyrics_lower or "quiet" in lyrics_lower:
                return "Malam yang Sepi"
            else:
                return "Malam yang Indah"
        
        elif "mimpi" in lyrics_lower or "dream" in lyrics_lower:
            return "Mimpi dalam Musik"
        
        elif "hati" in lyrics_lower or "heart" in lyrics_lower:
            return "Suara Hati"
        
        elif "senja" in lyrics_lower or "sunset" in lyrics_lower:
            if "indah" in lyrics_lower:
                return "Senja yang Indah"
            elif "merah" in lyrics_lower:
                return "Senja Merah"
            else:
                return "Waktu Senja"
        
        elif "pagi" in lyrics_lower or "morning" in lyrics_lower:
            if "cerah" in lyrics_lower:
                return "Pagi yang Cerah"
            elif "embun" in lyrics_lower:
                return "Pagi Berembun"
            else:
                return "Suara Pagi"
        
        elif "siang" in lyrics_lower or "noon" in lyrics_lower:
            return "Terik Siang"
        
        elif "sore" in lyrics_lower or "afternoon" in lyrics_lower:
            return "Sore yang Tenang"
        
        elif "malam" in lyrics_lower or "night" in lyrics_lower:
            if "gelap" in lyrics_lower:
                return "Malam yang Gelap"
            elif "sepi" in lyrics_lower:
                return "Malam yang Sepi"
            elif "indah" in lyrics_lower:
                return "Malam yang Indah"
            else:
                return "Suara Malam"
        
        elif "musim" in lyrics_lower or "season" in lyrics_lower:
            if "hujan" in lyrics_lower:
                return "Musim Hujan"
            elif "kemarau" in lyrics_lower:
                return "Musim Kemarau"
            elif "semi" in lyrics_lower:
                return "Musim Semi"
            elif "gugur" in lyrics_lower:
                return "Musim Gugur"
            elif "dingin" in lyrics_lower:
                return "Musim Dingin"
            elif "panas" in lyrics_lower:
                return "Musim Panas"
        
        elif "musik" in lyrics_lower or "music" in lyrics_lower:
            if "jiwa" in lyrics_lower:
                return "Irama Jiwa"
            elif "hati" in lyrics_lower:
                return "Musik dari Hati"
            else:
                return "Irama Musik"
        
        elif "warna" in lyrics_lower or "color" in lyrics_lower:
            if "biru" in lyrics_lower:
                return "Warna Biru"
            elif "merah" in lyrics_lower:
                return "Warna Merah"
            elif "hijau" in lyrics_lower:
                return "Warna Hijau"
            elif "kuning" in lyrics_lower:
                return "Warna Kuning"
            elif "ungu" in lyrics_lower:
                return "Warna Ungu"
            elif "hitam" in lyrics_lower:
                return "Warna Hitam"
            elif "putih" in lyrics_lower:
                return "Warna Putih"
            else:
                return "Palet Warna"
        
        elif "angin" in lyrics_lower or "wind" in lyrics_lower:
            if "sepoi" in lyrics_lower:
                return "Angin Sepoi"
            elif "kencang" in lyrics_lower:
                return "Angin Kencang"
            else:
                return "Suara Angin"
        
        elif "awan" in lyrics_lower or "cloud" in lyrics_lower:
            if "putih" in lyrics_lower:
                return "Awan Putih"
            elif "mendung" in lyrics_lower:
                return "Awan Mendung"
            else:
                return "Awan di Langit"
        
        elif "langit" in lyrics_lower or "sky" in lyrics_lower:
            if "biru" in lyrics_lower:
                return "Langit Biru"
            elif "mendung" in lyrics_lower:
                return "Langit Mendung"
            else:
                return "Langit yang Luas"
        
        elif "laut" in lyrics_lower or "sea" in lyrics_lower or "ocean" in lyrics_lower:
            if "gelombang" in lyrics_lower:
                return "Gelombang Laut"
            elif "ombak" in lyrics_lower:
                return "Ombak Laut"
            else:
                return "Suara Laut"
        
        elif "gunung" in lyrics_lower or "mountain" in lyrics_lower:
            if "puncak" in lyrics_lower:
                return "Puncak Gunung"
            elif "lereng" in lyrics_lower:
                return "Lereng Gunung"
            else:
                return "Gunung yang Tinggi"
        
        elif "hujan" in lyrics_lower or "rain" in lyrics_lower:
            if "tetesan" in lyrics_lower:
                return "Tetesan Hujan"
            elif "rintik" in lyrics_lower:
                return "Rintik Hujan"
            else:
                return "Suara Hujan"
        
        elif "matahari" in lyrics_lower or "sun" in lyrics_lower:
            if "terbit" in lyrics_lower:
                return "Matahari Terbit"
            elif "terbenam" in lyrics_lower:
                return "Matahari Terbenam"
            else:
                return "Sinar Matahari"
        
        elif "bulan" in lyrics_lower or "moon" in lyrics_lower:
            if "purnama" in lyrics_lower:
                return "Bulan Purnama"
            elif "sabit" in lyrics_lower:
                return "Bulan Sabit"
            else:
                return "Cahaya Bulan"
        
        elif "bintang" in lyrics_lower or "star" in lyrics_lower:
            if "malam" in lyrics_lower:
                return "Bintang di Malam"
            elif "berkilau" in lyrics_lower:
                return "Bintang Berkilau"
            else:
                return "Bintang di Langit"
        
        elif "jalan" in lyrics_lower or "road" in lyrics_lower or "path" in lyrics_lower:
            if "panjang" in lyrics_lower:
                return "Jalan yang Panjang"
            elif "berliku" in lyrics_lower:
                return "Jalan Berliku"
            else:
                return "Jalan Kehidupan"
        
        elif "rumah" in lyrics_lower or "home" in lyrics_lower:
            if "keluarga" in lyrics_lower:
                return "Rumah Keluarga"
            elif "hangat" in lyrics_lower:
                return "Rumah yang Hangat"
            else:
                return "Rumah Kita"
        
        elif "kota" in lyrics_lower or "city" in lyrics_lower:
            if "ramai" in lyrics_lower:
                return "Kota yang Ramai"
            elif "malam" in lyrics_lower:
                return "Kota di Malam"
            else:
                return "Suara Kota"
        
        elif "desa" in lyrics_lower or "village" in lyrics_lower:
            if "damai" in lyrics_lower:
                return "Desa yang Damai"
            elif "sepi" in lyrics_lower:
                return "Desa yang Sepi"
            else:
                return "Suara Desa"
        
        # Judul berdasarkan genre
        if genre_lower:
            if "pop" in genre_lower:
                if "happy" in mood_lower or "ceria" in mood_lower:
                    return "Pop Ceria"
                elif "romantic" in mood_lower or "romantis" in mood_lower:
                    return "Pop Romantis"
                else:
                    return "Pop Song"
            elif "rock" in genre_lower:
                if "energetic" in mood_lower or "energik" in mood_lower:
                    return "Rock Energik"
                elif "aggressive" in mood_lower or "agresif" in mood_lower:
                    return "Rock Agresif"
                else:
                    return "Rock Anthem"
            elif "jazz" in genre_lower:
                if "smooth" in mood_lower or "lembut" in mood_lower:
                    return "Jazz Lembut"
                elif "lounge" in mood_lower:
                    return "Jazz Lounge"
                else:
                    return "Jazz Melody"
            elif "electronic" in genre_lower:
                if "dance" in mood_lower or "dansa" in mood_lower:
                    return "Electronic Dance"
                elif "ambient" in mood_lower:
                    return "Electronic Ambient"
                else:
                    return "Electronic Beats"
            elif "classical" in genre_lower:
                if "orchestral" in mood_lower:
                    return "Classical Orchestral"
                elif "piano" in mood_lower:
                    return "Classical Piano"
                else:
                    return "Classical Piece"
            elif "hip-hop" in genre_lower or "hip hop" in genre_lower:
                if "energetic" in mood_lower:
                    return "Hip Hop Energik"
                else:
                    return "Hip Hop Beats"
            elif "r&b" in genre_lower or "rnb" in genre_lower:
                if "romantic" in mood_lower:
                    return "R&B Romantis"
                else:
                    return "R&B Soul"
            elif "country" in genre_lower:
                return "Country Song"
            elif "folk" in genre_lower:
                return "Folk Melody"
            elif "blues" in genre_lower:
                return "Blues Soul"
            elif "reggae" in genre_lower:
                return "Reggae Vibes"
            elif "latin" in genre_lower:
                return "Latin Rhythm"
            elif "indie" in genre_lower:
                return "Indie Song"
            elif "alternative" in genre_lower:
                return "Alternative Rock"
            elif "punk" in genre_lower:
                return "Punk Rock"
            elif "metal" in genre_lower:
                return "Metal Power"
            elif "ambient" in genre_lower:
                return "Ambient Music"
            elif "lo-fi" in genre_lower or "lofi" in genre_lower:
                return "Lo-Fi Chill"
        
        # Judul berdasarkan mood
        if mood_lower:
            if "happy" in mood_lower or "ceria" in mood_lower or "gembira" in lyrics_lower:
                return "Lagu Ceria"
            elif "sad" in mood_lower or "sedih" in mood_lower or "duka" in lyrics_lower:
                return "Lagu Sedih"
            elif "energetic" in mood_lower or "energik" in mood_lower or "semangat" in lyrics_lower:
                return "Lagu Energik"
            elif "calm" in mood_lower or "tenang" in mood_lower or "damai" in lyrics_lower:
                return "Lagu Tenang"
            elif "romantic" in mood_lower or "romantis" in mood_lower:
                return "Lagu Romantis"
            elif "mysterious" in mood_lower or "misterius" in mood_lower:
                return "Lagu Misterius"
            elif "nostalgic" in mood_lower or "nostalgia" in mood_lower:
                return "Lagu Nostalgia"
            elif "epic" in mood_lower or "epik" in mood_lower:
                return "Lagu Epik"
            elif "funky" in mood_lower or "funky" in mood_lower:
                return "Lagu Funky"
            elif "dreamy" in mood_lower or "mimpi" in mood_lower:
                return "Lagu Mimpi"
            elif "aggressive" in mood_lower or "agresif" in mood_lower:
                return "Lagu Agresif"
            elif "melancholic" in mood_lower or "melankolis" in mood_lower:
                return "Lagu Melankolis"
            elif "joyful" in mood_lower or "sukacita" in mood_lower:
                return "Lagu Sukacita"
            elif "serene" in mood_lower or "tenang" in mood_lower:
                return "Lagu Tenang"
            elif "passionate" in mood_lower or "berapi" in mood_lower:
                return "Lagu Berapi"
            elif "playful" in mood_lower or "lucu" in mood_lower:
                return "Lagu Lucu"
        
        # Judul berdasarkan persona
        if persona_lower:
            if "male" in persona_lower:
                if "romantic" in mood_lower:
                    return "Suara Pria Romantis"
                else:
                    return "Lagu Pria"
            elif "female" in persona_lower:
                if "romantic" in mood_lower:
                    return "Suara Wanita Romantis"
                else:
                    return "Lagu Wanita"
            elif "choir" in persona_lower:
                return "Paduan Suara"
            elif "instrumental" in persona_lower:
                return "Musik Instrumental"
            elif "duet" in persona_lower:
                return "Duet Romantis"
            elif "acapella" in persona_lower:
                return "A Capella"
            elif "rap" in persona_lower:
                return "Rap Song"
            elif "opera" in persona_lower:
                return "Opera"
            elif "whisper" in persona_lower:
                return "Bisikan Lembut"
            elif "robotic" in persona_lower:
                return "Suara Robot"
            elif "child" in persona_lower:
                return "Suara Anak-anak"
            elif "elderly" in persona_lower:
                return "Suara Senior"
            elif "screaming" in persona_lower:
                return "Suara Berteriak"
            elif "auto-tune" in persona_lower:
                return "Auto-Tune Song"
        
        # Default judul yang bermakna berdasarkan kombinasi
        if "cinta" in lyrics_lower and "malam" in lyrics_lower:
            return "Cinta di Malam Hari"
        elif "musik" in lyrics_lower and "hati" in lyrics_lower:
            return "Musik dari Hati"
        elif "mimpi" in lyrics_lower and "cahaya" in lyrics_lower:
            return "Mimpi dalam Cahaya"
        elif "langit" in lyrics_lower and "bintang" in lyrics_lower:
            return "Bintang di Langit"
        elif "laut" in lyrics_lower and "angin" in lyrics_lower:
            return "Angin di Laut"
        elif "gunung" in lyrics_lower and "awan" in lyrics_lower:
            return "Awan di Gunung"
        elif "hujan" in lyrics_lower and "jalan" in lyrics_lower:
            return "Hujan di Jalan"
        elif "matahari" in lyrics_lower and "senja" in lyrics_lower:
            return "Senja Matahari"
        elif "bulan" in lyrics_lower and "malam" in lyrics_lower:
            return "Bulan di Malam"
        elif "rumah" in lyrics_lower and "keluarga" in lyrics_lower:
            return "Rumah Keluarga"
        elif "kota" in lyrics_lower and "malam" in lyrics_lower:
            return "Kota di Malam"
        elif "desa" in lyrics_lower and "damai" in lyrics_lower:
            return "Desa yang Damai"
        else:
            return "Karya Musik Baru"
        
    except Exception as e:
        print(f"Error extracting title from lyrics: {e}")
        return "Lagu dari Lirik"

def extract_style_from_analysis(description, lyrics, instrumental):
    """Extract style musik dari hasil analisis AI"""
    try:
        description_lower = description.lower()
        lyrics_lower = lyrics.lower() if lyrics else ""
        
        style_parts = []
        
        # Genre berdasarkan deskripsi
        if "klub" in description_lower or "dj" in description_lower or "neon" in description_lower or "club" in description_lower:
            style_parts.append("Electronic Dance Music")
            style_parts.append("Club Anthem")
            style_parts.append("Party Vibe")
        elif "panggung" in description_lower or "concert" in description_lower:
            style_parts.append("Stadium Rock")
            style_parts.append("Arena Anthem")
        elif "klasik" in description_lower or "elegant" in description_lower:
            style_parts.append("Classical Pop")
            style_parts.append("Orchestral")
        elif "jazz" in description_lower or "lounge" in description_lower:
            style_parts.append("Smooth Jazz")
            style_parts.append("Lounge")
        else:
            style_parts.append("Contemporary Pop")
        
        # Mood berdasarkan lirik dan deskripsi
        if "energik" in description_lower or "powerful" in lyrics_lower:
            style_parts.append("High Energy")
            style_parts.append("Driving Beat")
        elif "romantis" in description_lower or "cinta" in lyrics_lower:
            style_parts.append("Romantic Ballad")
            style_parts.append("Emotional")
        elif "misterius" in description_lower or "dark" in description_lower:
            style_parts.append("Mysterious")
            style_parts.append("Atmospheric")
        elif "gemerlap" in description_lower or "glamour" in description_lower:
            style_parts.append("Glamorous")
            style_parts.append("Uplifting")
        else:
            style_parts.append("Feel-good")
        
        # Vokal style
        if instrumental:
            style_parts.append("Instrumental")
            style_parts.append("Cinematic")
        else:
            if "male" in description_lower or "pria" in description_lower:
                style_parts.append("Male Vocals")
            elif "female" in description_lower or "wanita" in description_lower:
                style_parts.append("Female Vocals")
            else:
                style_parts.append("Expressive Vocals")
        
        # Production style
        if "modern" in description_lower or "kontemporer" in description_lower:
            style_parts.append("Modern Production")
        elif "vintage" in description_lower or "retro" in description_lower:
            style_parts.append("Vintage Style")
        
        return ", ".join(style_parts[:6])  # Limit to 6 style elements
        
    except Exception as e:
        return "Contemporary Pop, Emotional" if not instrumental else "Instrumental, Cinematic"

def extract_genre_from_analysis(description, lyrics):
    """Extract genre musik dari hasil analisis AI"""
    try:
        description_lower = description.lower()
        lyrics_lower = lyrics.lower() if lyrics else ""
        
        # Deteksi genre berdasarkan kata kunci
        if any(word in description_lower for word in ["elektronik", "edm", "dj", "remix", "beat"]):
            return "Electronic Dance Music"
        elif any(word in description_lower for word in ["rock", "guitar", "band", "drummer"]):
            return "Rock"
        elif any(word in description_lower for word in ["jazz", "blues", "piano", "saxophone"]):
            return "Jazz"
        elif any(word in description_lower for word in ["klasik", "orchestra", "symphony", "violin"]):
            return "Classical"
        elif any(word in description_lower for word in ["folk", "akustik", "acoustic", "campfire"]):
            return "Folk"
        elif any(word in description_lower for word in ["reggae", "jamaica", "caribbean"]):
            return "Reggae"
        elif any(word in description_lower for word in ["country", "banjo", "harmonica"]):
            return "Country"
        elif any(word in description_lower for word in ["hip hop", "rap", "urban", "street"]):
            return "Hip Hop"
        elif any(word in description_lower for word in ["latin", "salsa", "tango", "rumba"]):
            return "Latin"
        else:
            return "Pop"
            
    except Exception as e:
        return "Pop"

def generate_lyrics_from_title(title, genre, mood, persona):
    """Generate lirik lagu dari judul menggunakan AI"""
    try:
        title_lower = title.lower()
        
        # Template lirik berdasarkan tema dan mood
        if "cinta" in title_lower or "love" in title_lower or "kasih" in title_lower:
            if "romantis" in mood or "romantic" in mood:
                return f"""[Verse 1]
{title}
Mengalir dalam hati yang dalam
Setiap kata penuh makna
Menggambarkan cinta yang abadi

[Chorus]
{title}
Melodi yang indah dan lembut
Menggugah jiwa yang rindu
Dalam harmoni yang sempurna

[Verse 2]
{title}
Bercerita tentang kisah kita
Tentang mimpi dan harapan
Yang selalu bersama selamanya

[Bridge]
{title}
Dalam setiap nada dan lirik
Tersimpan cinta yang tulus
Yang takkan pernah pudar

[Chorus]
{title}
Melodi yang indah dan lembut
Menggugah jiwa yang rindu
Dalam harmoni yang sempurna

[Outro]
{title}
Selamanya dalam hati kita"""
            
            elif "sedih" in mood or "sad" in mood:
                return f"""[Verse 1]
{title}
Mengalir dalam air mata
Setiap kata penuh kepedihan
Menggambarkan cinta yang hilang

[Chorus]
{title}
Melodi yang pilu dan sedih
Menggugah jiwa yang terluka
Dalam kesedihan yang mendalam

[Verse 2]
{title}
Bercerita tentang kenangan
Tentang cinta yang tak terbalas
Yang selalu menyakitkan hati

[Bridge]
{title}
Dalam setiap nada dan lirik
Tersimpan luka yang dalam
Yang takkan pernah sembuh

[Chorus]
{title}
Melodi yang pilu dan sedih
Menggugah jiwa yang terluka
Dalam kesedihan yang mendalam

[Outro]
{title}
Selamanya dalam kenangan"""
            
            else:
                return f"""[Verse 1]
{title}
Mengalir dalam jiwa yang dalam
Setiap kata penuh makna
Menggambarkan cinta yang indah

[Chorus]
{title}
Melodi yang hangat dan lembut
Menggugah jiwa yang rindu
Dalam harmoni yang sempurna

[Verse 2]
{title}
Bercerita tentang perasaan
Tentang mimpi dan harapan
Yang selalu ada dalam hati

[Bridge]
{title}
Dalam setiap nada dan lirik
Tersimpan cinta yang tulus
Yang takkan pernah pudar

[Chorus]
{title}
Melodi yang hangat dan lembut
Menggugah jiwa yang rindu
Dalam harmoni yang sempurna

[Outro]
{title}
Selamanya dalam hati kita"""
        
        elif "malam" in title_lower or "night" in title_lower:
            return f"""[Verse 1]
{title}
Mengalir dalam kegelapan
Setiap nada penuh misteri
Menggambarkan malam yang indah

[Chorus]
{title}
Melodi yang misterius dan dalam
Menggugah jiwa yang sepi
Dalam keheningan malam

[Verse 2]
{title}
Bercerita tentang bintang
Tentang bulan dan cahaya
Yang selalu menemani kita

[Bridge]
{title}
Dalam setiap nada dan lirik
Tersimpan keindahan malam
Yang takkan pernah pudar

[Chorus]
{title}
Melodi yang misterius dan dalam
Menggugah jiwa yang sepi
Dalam keheningan malam

[Outro]
{title}
Selamanya dalam malam"""
        
        elif "pagi" in title_lower or "morning" in title_lower:
            return f"""[Verse 1]
{title}
Mengalir dalam cahaya pagi
Setiap nada penuh semangat
Menggambarkan pagi yang cerah

[Chorus]
{title}
Melodi yang ceria dan segar
Menggugah jiwa yang bangun
Dalam semangat pagi hari

[Verse 2]
{title}
Bercerita tentang harapan
Tentang matahari dan embun
Yang selalu menyegarkan jiwa

[Bridge]
{title}
Dalam setiap nada dan lirik
Tersimpan semangat pagi
Yang takkan pernah pudar

[Chorus]
{title}
Melodi yang ceria dan segar
Menggugah jiwa yang bangun
Dalam semangat pagi hari

[Outro]
{title}
Selamanya dalam pagi"""
        
        elif "bahagia" in title_lower or "happy" in title_lower or "gembira" in title_lower:
            return f"""[Verse 1]
{title}
Mengalir dalam kegembiraan
Setiap nada penuh sukacita
Menggambarkan kebahagiaan yang abadi

[Chorus]
{title}
Melodi yang ceria dan riang
Menggugah jiwa yang bahagia
Dalam kegembiraan yang mendalam

[Verse 2]
{title}
Bercerita tentang kebahagiaan
Tentang tawa dan senyuman
Yang selalu mengiringi kita

[Bridge]
{title}
Dalam setiap nada dan lirik
Tersimpan kebahagiaan yang tulus
Yang takkan pernah pudar

[Chorus]
{title}
Melodi yang ceria dan riang
Menggugah jiwa yang bahagia
Dalam kegembiraan yang mendalam

[Outro]
{title}
Selamanya dalam kebahagiaan"""
        
        elif "mimpi" in title_lower or "dream" in title_lower:
            return f"""[Verse 1]
{title}
Terbang tinggi di awan putih
Membawa harapan dan keinginan
Menuju tempat yang tak terbatas

[Chorus]
{title}
Mimpi indah yang tak pernah pudar
Menggugah jiwa yang berharap
Dalam dunia yang penuh warna

[Verse 2]
{title}
Bercerita tentang angan-angan
Tentang masa depan yang cerah
Yang selalu kita impikan

[Bridge]
{title}
Dalam setiap nada dan lirik
Tersimpan mimpi yang indah
Yang takkan pernah sirna

[Chorus]
{title}
Mimpi indah yang tak pernah pudar
Menggugah jiwa yang berharap
Dalam dunia yang penuh warna

[Outro]
{title}
Selamanya dalam mimpi kita"""
        
        else:
            # Default template untuk judul lainnya
            return f"""[Verse 1]
{title}
Mengalir dalam jiwa yang dalam
Setiap nada penuh makna
Menggambarkan cerita yang indah

[Chorus]
{title}
Melodi yang indah dan lembut
Menggugah jiwa yang rindu
Dalam harmoni yang sempurna

[Verse 2]
{title}
Bercerita tentang kehidupan
Tentang mimpi dan harapan
Yang selalu mengiringi kita

[Bridge]
{title}
Dalam setiap nada dan lirik
Tersimpan makna yang dalam
Yang takkan pernah pudar

[Chorus]
{title}
Melodi yang indah dan lembut
Menggugah jiwa yang rindu
Dalam harmoni yang sempurna

[Outro]
{title}
Selamanya dalam hati kita"""
            
    except Exception as e:
        print(f"Error generating lyrics from title: {e}")
        return f"""[Verse 1]
{title}
Mengalir dalam jiwa yang dalam
Setiap nada penuh makna
Menggambarkan cerita yang indah

[Chorus]
{title}
Melodi yang indah dan lembut
Menggugah jiwa yang rindu
Dalam harmoni yang sempurna

[Verse 2]
{title}
Bercerita tentang kehidupan
Tentang mimpi dan harapan
Yang selalu mengiringi kita

[Bridge]
{title}
Dalam setiap nada dan lirik
Tersimpan makna yang dalam
Yang takkan pernah pudar

[Chorus]
{title}
Melodi yang indah dan lembut
Menggugah jiwa yang rindu
Dalam harmoni yang sempurna

[Outro]
{title}
Selamanya dalam hati kita"""

def suggest_genre_from_title(title):
    """Suggest genre berdasarkan judul lagu"""
    try:
        title_lower = title.lower()
        
        if any(word in title_lower for word in ["cinta", "love", "romantis", "romantic"]):
            return "pop"
        elif any(word in title_lower for word in ["malam", "night", "misterius", "mysterious"]):
            return "electronic"
        elif any(word in title_lower for word in ["pagi", "morning", "cerah", "bright"]):
            return "pop"
        elif any(word in title_lower for word in ["bahagia", "happy", "gembira", "joyful"]):
            return "pop"
        elif any(word in title_lower for word in ["sedih", "sad", "pilu", "melancholic"]):
            return "jazz"
        elif any(word in title_lower for word in ["energik", "energetic", "semangat", "powerful"]):
            return "rock"
        elif any(word in title_lower for word in ["tenang", "calm", "damai", "peaceful"]):
            return "ambient"
        else:
            return "pop"
            
    except Exception as e:
        return "pop"

def suggest_mood_from_title(title):
    """Suggest mood berdasarkan judul lagu"""
    try:
        title_lower = title.lower()
        
        if any(word in title_lower for word in ["cinta", "love", "romantis", "romantic"]):
            return "romantic"
        elif any(word in title_lower for word in ["malam", "night", "misterius", "mysterious"]):
            return "mysterious"
        elif any(word in title_lower for word in ["pagi", "morning", "cerah", "bright"]):
            return "happy"
        elif any(word in title_lower for word in ["bahagia", "happy", "gembira", "joyful"]):
            return "happy"
        elif any(word in title_lower for word in ["sedih", "sad", "pilu", "melancholic"]):
            return "sad"
        elif any(word in title_lower for word in ["energik", "energetic", "semangat", "powerful"]):
            return "energetic"
        elif any(word in title_lower for word in ["tenang", "calm", "damai", "peaceful"]):
            return "calm"
        else:
            return "happy"
            
    except Exception as e:
        return "happy"

def suggest_persona_from_title(title):
    """Suggest persona berdasarkan judul lagu"""
    try:
        title_lower = title.lower()
        
        if any(word in title_lower for word in ["cinta", "love", "romantis", "romantic"]):
            return "female"  # Biasanya lagu cinta lebih cocok dengan suara wanita
        elif any(word in title_lower for word in ["malam", "night", "misterius", "mysterious"]):
            return "male"    # Biasanya lagu misterius lebih cocok dengan suara pria
        elif any(word in title_lower for word in ["pagi", "morning", "cerah", "bright"]):
            return "female"  # Biasanya lagu pagi lebih cocok dengan suara wanita
        elif any(word in title_lower for word in ["bahagia", "happy", "gembira", "joyful"]):
            return "female"  # Biasanya lagu bahagia lebih cocok dengan suara wanita
        elif any(word in title_lower for word in ["sedih", "sad", "pilu", "melancholic"]):
            return "male"    # Biasanya lagu sedih lebih cocok dengan suara pria
        elif any(word in title_lower for word in ["energik", "energetic", "semangat", "powerful"]):
            return "male"    # Biasanya lagu energik lebih cocok dengan suara pria
        elif any(word in title_lower for word in ["tenang", "calm", "damai", "peaceful"]):
            return "female"  # Biasanya lagu tenang lebih cocok dengan suara wanita
        else:
            return "female"  # Default ke suara wanita
            
    except Exception as e:
        return "female"

def generate_music_with_suno(data):
    """Generate musik menggunakan Suno API yang sudah ada"""
    try:
        # Hapus semua file callback lama sebelum generate baru
        for f in glob.glob('suno_callback_result_*.json'):
            try:
                os.remove(f)
            except Exception as e:
                print(f"Gagal menghapus file lama: {f}, error: {e}")
        
        mode = data.get('mode', 'prompt')
        prompt = data.get('prompt', '')
        description = data.get('description', '')
        lyrics = data.get('lyrics', '')
        instrumental = data.get('instrumental', False)
        title = data.get('title', 'Karya Musik Baru')
        model = data.get('model', 'V4_5PLUS')
        genre = data.get('genre', '')
        mood = data.get('mood', '')
        persona = data.get('persona', '')
        
        # Handle different modes with appropriate settings
        customMode = False  # Default to simple mode
        style = ""
        print(f"🎛️ Using Custom Mode: {customMode} for mode: {mode}")
        
        if mode == 'lyrics':
            if not lyrics or not lyrics.strip():
                return jsonify({'success': False, 'message': 'Lyrics wajib diisi untuk mode lyrics'})
            
            # For lyrics mode, use custom mode to support long lyrics
            customMode = True
            prompt = lyrics
            instrumental = False
            
            # Build style from genre, mood, persona
            style_parts = []
            if genre:
                style_parts.append(genre)
            if mood:
                style_parts.append(mood)
            if persona:
                style_parts.append(persona)
            
            style = ", ".join(style_parts) if style_parts else "Pop"
            
        elif mode == 'image':
            if not description or not description.strip():
                return jsonify({'success': False, 'message': 'Description wajib diisi untuk mode image'})
            
            # For image mode, use custom mode for detailed AI analysis
            customMode = True
            
            # Extract AI-generated information for custom mode
            ai_title = extract_title_from_analysis(description, lyrics)
            ai_style = extract_style_from_analysis(description, lyrics, instrumental)
            ai_genre = extract_genre_from_analysis(description, lyrics)
            
            # Override title with AI-generated title
            title = ai_title
            style = ai_style
            
            if instrumental:
                # For instrumental, use description as prompt
                prompt = description
            else:
                # For vocal, use lyrics as prompt
                if not lyrics or not lyrics.strip():
                    return jsonify({'success': False, 'message': 'Lyrics wajib diisi untuk mode image non-instrumental'})
                prompt = lyrics
            
        elif mode == 'prompt':
            if not prompt or not prompt.strip():
                return jsonify({'success': False, 'message': 'Prompt wajib diisi untuk mode prompt'})
            
            # For prompt mode, use simple mode (not custom)
            customMode = False
            style = ""  # No style for simple mode
            instrumental = False
        
        # Validate prompt length based on mode
        if customMode:
            # Custom mode validation (for lyrics and image)
            prompt_limit = 5000 if model in ['V4_5PLUS', 'V4_5'] else 3000
            style_limit = 1000 if model in ['V4_5PLUS', 'V4_5'] else 200
            
            if len(prompt) > prompt_limit:
                return jsonify({'success': False, 'message': f'Prompt terlalu panjang. Maksimal {prompt_limit} karakter untuk model {model}'})
            
            if len(style) > style_limit:
                return jsonify({'success': False, 'message': f'Style terlalu panjang. Maksimal {style_limit} karakter untuk model {model}'})
        else:
            # Simple mode validation (for prompt)
            if model == 'V3_5':
                prompt_limit = 400  # V3.5 simple mode limit
            else:
                prompt_limit = 3000  # Other models
            
            if len(prompt) > prompt_limit:
                return jsonify({'success': False, 'message': f'Prompt terlalu panjang. Maksimal {prompt_limit} karakter untuk simple mode dengan model {model}'})
        
        # Clean prompt/lyrics to avoid artist name detection by Suno API
        cleaned_prompt = clean_lyrics_for_suno(prompt)
        
        # Gunakan callback domain dari konfigurasi
        callback_url = f"{CALLBACK_DOMAIN}/musik/callback"
        
        # Build payload based on mode
        if customMode:
            # Custom mode payload (for lyrics and image)
            payload = {
                "prompt": cleaned_prompt,
                "customMode": customMode,
                "instrumental": instrumental,
                "model": model,
                "callBackUrl": callback_url,
                "title": title[:100] if title else "Karya Musik Baru",
                "style": style[:1000] if style else "Pop"  # Style is required for custom mode
            }
        else:
            # Simple mode payload (for prompt)
            payload = {
                "prompt": cleaned_prompt,
                "customMode": customMode,
                "instrumental": instrumental,
                "model": model,
                "callBackUrl": callback_url,
                "title": title[:100] if title else "Karya Musik Baru"
                # No style for simple mode
            }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {SUNO_API_KEY}'
        }
        
        # Debug logging
        print(f"🎵 Suno API Request:")
        print(f"   Mode: {mode}")
        print(f"   Model: {model}")
        print(f"   CustomMode: {customMode}")
        print(f"   Prompt: {cleaned_prompt[:100]}...")
        print(f"   Style: {style[:100] if style else 'None'}")
        print(f"   Payload: {payload}")
        
        # Call Suno API
        response = requests.post(f"{SUNO_BASE_URL}/api/v1/generate", headers=headers, json=payload)
        res_json = response.json()
        
        print(f"🎵 Suno API Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {res_json}")
        
        if res_json.get("code") != 200:
            error_msg = res_json.get("msg", "Unknown error from Suno API")
            print(f"❌ Suno API Error: {error_msg}")
            return jsonify({'success': False, 'message': error_msg})
        
        task_id = res_json["data"]["taskId"]
        
        # Wait for callback result (polling)
        callback_file = f'suno_callback_result_{task_id}.json'
        for i in range(60):  # 5 menit
            if os.path.exists(callback_file):
                try:
                    with open(callback_file, 'r', encoding='utf-8') as f:
                        callback_data = json.load(f)
                except Exception as e:
                    os.remove(callback_file)
                    continue
                
                # Validate callback data
                if not callback_data or not isinstance(callback_data, dict) or 'data' not in callback_data:
                    os.remove(callback_file)
                    continue
                
                cb_data = callback_data.get('data', {})
                cb_task_id = cb_data.get('task_id')
                
                if not cb_task_id or not isinstance(cb_data.get('data', []), list):
                    os.remove(callback_file)
                    continue
                
                songs_data = cb_data.get('data', [])
                if not songs_data:
                    os.remove(callback_file)
                    continue
                
                # Process the first song result
                song_data = songs_data[0]
                audio_url = song_data.get('audio_url', '')
                title_result = song_data.get('title', title)
                duration = song_data.get('duration', 0)  # Get duration from Suno API
                model_name = song_data.get('model_name', model)  # Get model name from Suno API
                
                if not audio_url:
                    os.remove(callback_file)
                    continue
                
                # Save to database
                from models import db, Song
                
                # For image mode, use AI extracted genre
                if mode == 'image':
                    final_genre = data.get('ai_genre', genre or 'AI Generated')
                else:
                    final_genre = genre or 'AI Generated'
                
                music = Song(
                    id=str(uuid.uuid4()),
                    user_id=session['user_id'],
                    title=title_result,
                    lyrics=lyrics if not instrumental else "",
                    genre=final_genre,
                    mode=mode,
                    prompt=prompt,
                    audio_url=audio_url,
                    image_url=song_data.get('image_url', ''),
                    duration=duration,  # Save duration from Suno API
                    model_name=model_name,  # Save model name from Suno API
                    created_at=datetime.now()
                )
                db.session.add(music)
                db.session.commit()
                

                
                # Clean up callback file
                os.remove(callback_file)
                
                return jsonify({
                    'success': True,
                    'message': 'Musik berhasil dibuat dengan Suno AI!',
                    'task_id': task_id,
                    'music': {
                        'id': music.id,
                        'title': music.title,
                        'audio_url': music.audio_url,
                        'image_url': music.image_url,
                        'lyrics': music.lyrics,
                        'genre': music.genre,
                        'mode': music.mode,
                        'prompt': music.prompt,
                        'duration': music.duration,
                        'model_name': music.model_name,
                        'created_at': music.created_at.isoformat()
                    }
                })
            
            time.sleep(5)  # Wait 5 seconds before next check
        
        # Timeout
        return jsonify({'success': False, 'message': 'Timeout menunggu hasil dari Suno API'})
        
    except Exception as e:
        print(f"Error in generate_music_with_suno: {e}")
        return jsonify({'success': False, 'message': f'Gagal generate musik: {str(e)}'})

def handle_lyrics_generation(data):
    """Handle generation dari lyrics menggunakan Suno API"""
    try:
        lyrics = data.get('lyrics', '').strip()
        genre = data.get('genre', '')
        mood = data.get('mood', '')
        persona = data.get('persona', '')
        
        if not lyrics:
            return jsonify({'success': False, 'message': 'Lirik tidak boleh kosong'})
        
        # Check user credits
        from models import User
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'User tidak ditemukan'})
        if user.kredit < 15:
            return jsonify({'success': False, 'message': 'Kredit Anda tidak cukup untuk generate musik (minimal 15 kredit)'})
        
        # Deduct credits
        user.kredit -= 15
        db.session.commit()
        
        # Extract judul dari lirik
        ai_title = extract_title_from_lyrics(lyrics, genre, mood, persona)
        
        # Generate musik menggunakan Suno API
        return generate_music_with_suno({
            'mode': 'lyrics',
            'lyrics': lyrics,
            'genre': genre,
            'mood': mood,
            'persona': persona,
            'title': ai_title,  # Use AI generated title from lyrics
            'model': 'V4_5PLUS'
        })
        
    except Exception as e:
        print(f"Error in handle_lyrics_generation: {e}")
        return jsonify({'success': False, 'message': f'Gagal membuat musik: {str(e)}'})

def handle_image_generation(data):
    """Handle generation dari image analysis menggunakan Suno API"""
    try:
        description = data.get('description', '').strip()
        lyrics = data.get('lyrics', '').strip()
        instrumental = data.get('instrumental', False)
        
        if not description and not lyrics:
            return jsonify({'success': False, 'message': 'Deskripsi atau lirik harus ada'})
        
        # Check user credits
        from models import User
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'User tidak ditemukan'})
        if user.kredit < 15:
            return jsonify({'success': False, 'message': 'Kredit Anda tidak cukup untuk generate musik (minimal 15 kredit)'})
        
        # Deduct credits
        user.kredit -= 15
        db.session.commit()
        
        # Extract AI info for custom mode
        ai_title = extract_title_from_analysis(description, lyrics)
        ai_style = extract_style_from_analysis(description, lyrics, instrumental)
        ai_genre = extract_genre_from_analysis(description, lyrics)
        
        # Generate musik menggunakan Suno API dengan AI extracted info
        return generate_music_with_suno({
            'mode': 'image',
            'description': description,
            'lyrics': lyrics,
            'instrumental': instrumental,
            'title': ai_title,  # Use AI generated title
            'model': 'V4_5PLUS',
            'ai_genre': ai_genre  # Pass AI genre to be saved
        })
        
    except Exception as e:
        print(f"Error in handle_image_generation: {e}")
        return jsonify({'success': False, 'message': f'Gagal membuat musik: {str(e)}'})

def handle_prompt_generation(data):
    """Handle generation dari prompt menggunakan Suno API"""
    try:
        prompt = data.get('prompt', '').strip()
        custom_title = data.get('title', '').strip()
        model = data.get('model', 'suno-v3.5')
        duration = data.get('duration', '60')
        
        if not prompt:
            return jsonify({'success': False, 'message': 'Prompt tidak boleh kosong'})
        
        # Map frontend model names to Suno API model names
        model_mapping = {
            'suno-v3.5': 'V3_5',
            'suno-v4.5': 'V4_5PLUS'
        }
        
        suno_model = model_mapping.get(model, 'V3_5')  # Default to V3_5 for simple mode
        
        # Check user credits
        from models import User
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'User tidak ditemukan'})
        if user.kredit < 15:
            return jsonify({'success': False, 'message': 'Kredit Anda tidak cukup untuk generate musik (minimal 15 kredit)'})
        
        # Deduct credits
        user.kredit -= 15
        db.session.commit()
        
        # Determine title: use custom title if provided, otherwise generate from prompt
        if custom_title:
            final_title = custom_title
        else:
            final_title = extract_title_from_analysis(prompt, "")
        
        # Generate musik menggunakan Suno API
        return generate_music_with_suno({
            'mode': 'prompt',
            'prompt': prompt,
            'title': final_title,  # Use custom title or AI generated title
            'model': suno_model
        })
        
    except Exception as e:
        print(f"Error in handle_prompt_generation: {e}")
        return jsonify({'success': False, 'message': f'Gagal membuat musik: {str(e)}'})

@musik_bp.route('/api/analyze-image', methods=['POST'])
def analyze_image():
    """
    Endpoint untuk menganalisis gambar dan menghasilkan deskripsi + lirik menggunakan AI
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image file selected'}), 400
    
    try:
        # Simpan file sementara
        filename = f"temp_image_{uuid.uuid4().hex}.jpg"
        filepath = os.path.join('static', 'uploads', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        
        # Save uploaded image
        
        try:
            # Use GeminiChatService for image analysis
            import sys
            import base64
            
            # Add parent directory to path for import
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            if parent_dir not in sys.path:
                sys.path.append(parent_dir)
            
            try:
                # Check if chat.py exists
                chat_path = os.path.join(parent_dir, 'chat.py')
                print(f"🔍 Looking for chat.py at: {chat_path}")
                print(f"🔍 File exists: {os.path.exists(chat_path)}")
                
                from chat import gemini_service
                print("✅ Successfully imported gemini_service")
            except ImportError as ie:
                print(f"❌ Failed to import gemini_service: {ie}")
                print(f"❌ Current sys.path: {sys.path}")
                raise ie
            
            # Convert image to base64 untuk AI analysis
            with open(filepath, 'rb') as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            

            
            # Analyze image using GeminiChatService
            print("🔍 Starting AI analysis...")
            analysis_result = gemini_service.analyze_image_for_music(image_data)
            print(f"🔍 AI Analysis Result: {analysis_result}")
            
            if analysis_result and analysis_result.get('success'):
                # Get analysis text from the result
                analysis_text = analysis_result.get('analysis', '')
                print(f"🤖 Raw AI Analysis Text:")
                print("=" * 50)
                print(analysis_text)
                print("=" * 50)
                
                # Parse hasil analisis AI dengan format yang lebih advanced
                lines = analysis_text.split('\n')
                description = ""
                mood = ""
                genre = ""
                lyrics = ""
                
                current_section = ""
                lyrics_started = False
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('Deskripsi:'):
                        description = line.replace('Deskripsi:', '').strip()
                        print(f"📝 Found Description: {description}")
                        current_section = "description"
                    elif line.startswith('Mood:'):
                        mood = line.replace('Mood:', '').strip()
                        print(f"😊 Found Mood: {mood}")
                        current_section = "mood"
                    elif line.startswith('Genre:'):
                        genre = line.replace('Genre:', '').strip()
                        print(f"🎵 Found Genre: {genre}")
                        current_section = "genre"
                    elif line.startswith('Lirik:'):
                        current_section = "lyrics"
                        lyrics_started = True
                        print("🎤 Starting lyrics section")
                        continue
                    elif lyrics_started and line:
                        # Include all lyrics sections (Verse, Chorus, Bridge, etc.)
                        if lyrics:
                            lyrics += "\n" + line
                        else:
                            lyrics = line
                    elif current_section == "description" and line and not any(x in line for x in ['Mood:', 'Genre:', 'Lirik:']):
                        # Continue description if it spans multiple lines
                        description += " " + line
                    elif current_section == "mood" and line and not any(x in line for x in ['Deskripsi:', 'Genre:', 'Lirik:']):
                        # Continue mood if it spans multiple lines
                        mood += " " + line
                    elif current_section == "genre" and line and not any(x in line for x in ['Deskripsi:', 'Mood:', 'Lirik:']):
                        # Continue genre if it spans multiple lines
                        genre += " " + line
                
                print(f"🎤 Parsed Lyrics Length: {len(lyrics)} characters")
                print(f"📝 Final Description: {description}")
                print(f"😊 Final Mood: {mood}")
                print(f"🎵 Final Genre: {genre}")
                if lyrics:
                    print(f"🎤 First 200 chars of lyrics: {lyrics[:200]}...")
                
                # If no structured parsing worked, try to extract lyrics from full text
                if not lyrics and "lirik" in analysis_text.lower():
                    print("🔍 Trying alternative lyrics extraction...")
                    # Find lyrics section in the text
                    text_lower = analysis_text.lower()
                    lyrics_start = text_lower.find("lirik:")
                    if lyrics_start != -1:
                        lyrics_section = analysis_text[lyrics_start + 6:].strip()
                        # Take everything after "Lirik:" as lyrics
                        lyrics = lyrics_section
                        print(f"🎤 Alternative extraction found: {len(lyrics)} characters")
                
                # If still no lyrics, try to find verse/chorus patterns
                if not lyrics:
                    print("🔍 Trying pattern-based lyrics extraction...")
                    verse_pattern = r'\(Verse.*?\)(.*?)(?=\(|\Z)'
                    chorus_pattern = r'\(Chorus.*?\)(.*?)(?=\(|\Z)'
                    import re
                    
                    verses = re.findall(verse_pattern, analysis_text, re.DOTALL | re.IGNORECASE)
                    choruses = re.findall(chorus_pattern, analysis_text, re.DOTALL | re.IGNORECASE)
                    
                    if verses or choruses:
                        lyrics_parts = []
                        for i, verse in enumerate(verses):
                            lyrics_parts.append(f"(Verse {i+1}){verse.strip()}")
                        for i, chorus in enumerate(choruses):
                            lyrics_parts.append(f"(Chorus){chorus.strip()}")
                        lyrics = "\n\n".join(lyrics_parts)
                        print(f"🎤 Pattern extraction found: {len(lyrics)} characters")
                
                # Ensure we have meaningful content
                if not description:
                    # Try to extract description from the beginning of analysis
                    first_sentences = '. '.join(analysis_text.split('.')[:3])
                    description = first_sentences if len(first_sentences) > 20 else "Gambar yang menginspirasi musik"
                    print(f"📝 Fallback description: {description[:100]}...")
                
                # Ensure we have meaningful lyrics - if parsing failed, use the full analysis
                if not lyrics:
                    print("⚠️ No lyrics found in structured parsing, using full analysis text")
                    lyrics = analysis_text
                
                # Clean lyrics to avoid Suno API issues
                cleaned_lyrics = clean_lyrics_for_suno(lyrics)
                print(f"✨ Final cleaned lyrics length: {len(cleaned_lyrics)} characters")
                
                # Final validation and cleanup
                final_description = description.strip() if description else "Gambar yang menginspirasi musik"
                final_mood = mood.strip() if mood else "inspiratif"
                final_genre = genre.strip() if genre else "Pop"
                
                print(f"🎯 Sending to frontend:")
                print(f"   Description: {final_description[:100]}...")
                print(f"   Mood: {final_mood}")
                print(f"   Genre: {final_genre}")
                print(f"   Lyrics length: {len(cleaned_lyrics)} chars")
                
                return jsonify({
                    'success': True,
                    'description': final_description,
                    'mood': final_mood,
                    'genre': final_genre,
                    'lyrics': cleaned_lyrics,
                    'image_url': f'/static/uploads/{filename}',
                    'raw_analysis': analysis_text  # Untuk debugging
                })
            else:
                error_msg = analysis_result.get('error', 'Unknown error') if analysis_result else 'No result'
                print(f"❌ AI Analysis Failed: {error_msg}")
                print(f"❌ Analysis Result: {analysis_result}")
                # Return error instead of fallback data
                return jsonify({
                    'success': False,
                    'message': f'AI analysis failed: {error_msg}',
                    'error': error_msg
                })
                
        except ImportError as ie:
            print(f"Import error: {ie}")
            # Return error instead of fallback data
            return jsonify({
                'success': False,
                'message': f'Import error: {str(ie)}',
                'error': str(ie)
            })
        
    except Exception as e:
        return jsonify({'error': f'Failed to analyze image: {str(e)}'}), 500

@musik_bp.route('/api/music/convert-midi', methods=['POST'])
def convert_to_midi():
    """
    Endpoint untuk mengkonversi audio ke MIDI
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No audio file selected'}), 400
    
    try:
        # Simpan file audio
        filename = f"audio_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join('static', 'uploads', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        
        # TODO: Implementasi konversi audio ke MIDI
        # Untuk sementara, buat file MIDI dummy
        midi_filename = f"midi_{uuid.uuid4().hex}.mid"
        midi_filepath = os.path.join('static', 'uploads', midi_filename)
        
        # Buat file MIDI dummy (binary data sederhana)
        with open(midi_filepath, 'wb') as f:
            # Header MIDI sederhana
            f.write(b'MThd\x00\x00\x00\x06\x00\x01\x00\x01\x01\x00')
            f.write(b'MTrk\x00\x00\x00\x04\x00\xFF\x02\x00')
        
        return jsonify({
            'success': True,
            'midi_url': f'/static/uploads/{midi_filename}',
            'message': 'Audio converted to MIDI successfully'
        })
        
    except Exception as e:
        print(f"Error converting audio to MIDI: {e}")
        return jsonify({'error': 'Failed to convert audio to MIDI'}), 500

@musik_bp.route('/api/music/generate-with-reference', methods=['POST'])
def generate_with_reference():
    """
    Endpoint untuk generate musik dengan reference audio
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    if 'reference_audio' not in request.files:
        return jsonify({'error': 'No reference audio file provided'}), 400
    
    file = request.files['reference_audio']
    if file.filename == '':
        return jsonify({'error': 'No reference audio file selected'}), 400
    
    prompt = request.form.get('prompt', '')
    model = request.form.get('model', 'V4_5PLUS')
    
    try:
        # Simpan file reference audio
        filename = f"reference_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join('static', 'uploads', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        
        # TODO: Implementasi generate musik dengan reference
        # Untuk sementara, gunakan endpoint generate_lyrics yang sudah ada
        payload = {
            'prompt': f"Create music similar to the reference audio. {prompt}",
            'instrumental': False,
            'model': model,
            'customMode': False
        }
        
        # Panggil endpoint generate_lyrics yang sudah ada
        from flask import current_app
        with current_app.test_request_context('/generate_lyrics', method='POST', json=payload):
            return generate_lyrics()
        
    except Exception as e:
        print(f"Error generating music with reference: {e}")
        return jsonify({'error': 'Failed to generate music with reference'}), 500

@musik_bp.route('/generate_lyrics', methods=['POST'])
def generate_lyrics():
    """
    Endpoint untuk menerima deskripsi lagu dari frontend dan mengirim permintaan
    ke API Suno untuk menghasilkan lirik.
    """
    # Hapus semua file callback lama sebelum generate baru
    for f in glob.glob('suno_callback_result_*.json'):
        try:
            os.remove(f)
        except Exception as e:
            print(f"Gagal menghapus file lama: {f}, error: {e}")
    data = request.get_json()
    mode = data.get('mode', 'prompt')  # lyrics, image, prompt, reference
    prompt = data.get('prompt', '')
    instrumental = data.get('instrumental', False)
    style = data.get('style', '')
    title = data.get('title', '')
    customMode = data.get('customMode', False)
    model = data.get('model', 'V4_5PLUS')
    
    # Handle different modes
    if mode == 'lyrics':
        lyrics = data.get('lyrics', '')
        genre = data.get('genre', '')
        mood = data.get('mood', '')
        persona = data.get('persona', '')
        
        if not lyrics or not lyrics.strip():
            return jsonify({"error": "Lyrics wajib diisi untuk mode lyrics."}), 400
        
        # Build prompt from lyrics and additional parameters
        prompt_parts = [lyrics]
        if genre:
            prompt_parts.append(f"Genre: {genre}")
        if mood:
            prompt_parts.append(f"Mood: {mood}")
        if persona:
            prompt_parts.append(f"Persona: {persona}")
        
        prompt = " | ".join(prompt_parts)
        customMode = False
        instrumental = False
        # Generate dynamic title based on lyrics analysis
        title = extract_title_from_lyrics(lyrics, genre, mood, persona)
        
    elif mode == 'image':
        description = data.get('description', '')
        lyrics = data.get('lyrics', '')
        
        if not description or not description.strip():
            return jsonify({"error": "Description wajib diisi untuk mode image."}), 400
        
        if not instrumental and (not lyrics or not lyrics.strip()):
            return jsonify({"error": "Lyrics wajib diisi untuk mode image non-instrumental."}), 400
        
        if instrumental:
            prompt = description
        else:
            prompt = lyrics
        
        customMode = False
        # Generate dynamic title based on image analysis
        title = extract_title_from_analysis(description, lyrics)
        
    elif mode == 'prompt':
        if not prompt or not prompt.strip():
            return jsonify({"error": "Prompt wajib diisi untuk mode prompt."}), 400
        
        customMode = False
        # Generate dynamic title based on prompt analysis
        title = extract_title_from_analysis(prompt, "")
    # Validate model
    valid_models = ['V4_5PLUS', 'V4_5', 'V4', 'V3_5']
    if model not in valid_models:
        return jsonify({"error": f"Model {model} tidak valid. Model yang tersedia: {', '.join(valid_models)}"}), 400
    
    negativeTags = data.get('negativeTags', '')
    lyrics = data.get('lyrics', '')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    from models import User
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User tidak ditemukan'}), 404
    if user.kredit < 15:
        return jsonify({'error': 'Kredit Anda tidak cukup untuk generate musik (minimal 15 kredit)'}), 403
    user.kredit -= 15
    db.session.commit()
    # Gunakan callback domain dari konfigurasi
    callback_url = f"{CALLBACK_DOMAIN}/musik/callback"

    # Get character limits based on model
    def get_prompt_limit(model):
        if model in ['V4_5PLUS', 'V4_5']:
            return 5000  # V4.5+ and V4.5 have 5000 character limit
        else:
            return 3000  # V4 and V3.5 have 3000 character limit
    
    def get_style_limit(model):
        if model in ['V4_5PLUS', 'V4_5']:
            return 1000  # V4.5+ and V4.5 have 1000 character limit
        else:
            return 200   # V4 and V3.5 have 200 character limit
    
    prompt_limit = get_prompt_limit(model)
    style_limit = get_style_limit(model)
    
    # Batasi prompt di non-custom mode berdasarkan model
    if not customMode:
        if not prompt or not prompt.strip():
            return jsonify({"error": "Deskripsi lagu (prompt) wajib diisi untuk simple mode."}), 400
        if prompt:
            prompt = prompt[:prompt_limit]
        if len(prompt) > prompt_limit:
            return jsonify({"error": f"Deskripsi lagu (prompt) di mode non-custom tidak boleh lebih dari {prompt_limit} karakter untuk model {model}."}), 400

    # Pada custom mode:
    # - Jika instrumental: prompt = deskripsi
    # - Jika non-instrumental: prompt = lirik user
    if customMode:
        # Validate custom mode requirements
        if not title or not title.strip():
            return jsonify({"error": "Title wajib diisi untuk custom mode."}), 400
        if not style or not style.strip():
            return jsonify({"error": "Style wajib diisi untuk custom mode."}), 400
        
        if instrumental:
            # For instrumental mode, prompt should contain the description
            if not prompt or not prompt.strip():
                return jsonify({"error": "Description wajib diisi untuk custom mode instrumental."}), 400
            if len(prompt) > prompt_limit:
                return jsonify({"error": f"Description tidak boleh lebih dari {prompt_limit} karakter untuk model {model}."}), 400
        else:
            # For non-instrumental mode, prompt should contain lyrics
            if not lyrics or not lyrics.strip():
                return jsonify({"error": "Lyrics wajib diisi untuk custom mode non-instrumental."}), 400
            if len(lyrics) > prompt_limit:
                return jsonify({"error": f"Lyrics tidak boleh lebih dari {prompt_limit} karakter untuk model {model}."}), 400
            prompt = lyrics  # lirik user
            # Clear any existing prompt for non-instrumental mode
            data['prompt'] = ''

    # Clean prompt/lyrics to avoid artist name detection by Suno API
    cleaned_prompt = clean_lyrics_for_suno(prompt)
    
    payload = {
        "prompt": cleaned_prompt,
        "customMode": customMode,
        "instrumental": instrumental,
        "model": model,
        "callBackUrl": callback_url
    }
    if style:
        # Validate style length based on model
        if len(style) > style_limit:
            return jsonify({"error": f"Style tidak boleh lebih dari {style_limit} karakter untuk model {model}."}), 400
        payload["style"] = style
    if title:
        # Validate title length (max 100 characters)
        if len(title) > 100:
            return jsonify({"error": "Title tidak boleh lebih dari 100 karakter."}), 400
        payload["title"] = title
    if negativeTags:
        payload["negativeTags"] = negativeTags

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {SUNO_API_KEY}'
    }

    try:
        response = requests.post(f"{SUNO_BASE_URL}/api/v1/generate", headers=headers, json=payload)
        res_json = response.json()

        if res_json.get("code") != 200:
            return jsonify({"error": res_json.get("msg", "Unknown error")}), 500
        task_id = res_json["data"]["taskId"]
    except Exception as e:
        return jsonify({"error": f"Gagal membuat task: {e}"}), 500


    callback_file = f'suno_callback_result_{task_id}.json'
    for _ in range(60):  # 5 menit
        if os.path.exists(callback_file):
            try:
                with open(callback_file, 'r', encoding='utf-8') as f:
                    callback_data = json.load(f)
            except Exception as e:
                os.remove(callback_file)
                continue  # lanjut polling jika file rusak
            # Jika file kosong atau tidak valid, hapus dan lanjut polling
            if not callback_data or not isinstance(callback_data, dict) or 'data' not in callback_data:
                os.remove(callback_file)
                continue
            # Pastikan struktur callback benar
            cb_data = callback_data.get('data', {})
            cb_task_id = cb_data.get('task_id')
            if not cb_task_id or not isinstance(cb_data.get('data', []), list):
                os.remove(callback_file)
                continue
            if cb_task_id == task_id:
                callback_type = cb_data.get('callbackType', '')
                result_list = cb_data.get('data', [])
                has_audio = any(item.get('audio_url') for item in result_list)
                all_audio = all(item.get('audio_url') for item in result_list)
                results = []
                for item in result_list:
                    results.append({
                        "audio_url": item.get('audio_url', ''),
                        "lyrics": item.get('prompt', ''),
                        "title": item.get('title', ''),
                        "image_url": item.get('image_url', ''),
                        "tags": item.get('tags', ''),
                        "duration": item.get('duration', 0),
                        "createTime": item.get('createTime', 0),
                        "model_name": item.get('model_name', '')
                    })
                # Batasi maksimal 2 lagu
                results = sorted(results, key=lambda x: x.get('createTime', 0))[:2]
                # Hapus file callback jika sudah complete, semua audio_url sudah ada, atau file kosong/tidak valid
                if callback_type == 'complete' or all_audio:
                    os.remove(callback_file)
                    user_id = session.get('user_id')
                    if user_id and result_list:
                        # Process all results
                        for song_item in result_list:
                            if song_item.get('audio_url'):
                                exists = Song.query.filter_by(user_id=user_id, audio_url=song_item.get('audio_url')).first()
                                if not exists:
                                    new_song = Song(
                                        id=str(uuid.uuid4()),
                                        user_id=user_id,
                                        title=song_item.get('title', '') or title,
                                        prompt=song_item.get('prompt', '') or prompt,
                                        model_name=song_item.get('model_name', '') or model,
                                        duration=song_item.get('duration', 0),
                                        image_url=song_item.get('image_url', ''),
                                        audio_url=song_item.get('audio_url', ''),
                                        stream_audio_url=song_item.get('stream_audio_url', ''),
                                        source_audio_url=song_item.get('source_audio_url', ''),
                                        source_image_url=song_item.get('source_image_url', ''),
                                        source_stream_audio_url=song_item.get('source_stream_audio_url', ''),
                                        genre=data.get('genre', ''),
                                        mode=mode
                                    )
                                    db.session.add(new_song)
                                    db.session.commit()
                                    
            # Jika file kosong ({}), hapus juga
            if callback_data == {}:
                os.remove(callback_file)
                continue
                
            return jsonify({
                "success": True,
                "results": results,
                "message": "Sukses! Musik telah dibuat.",
                "task_id": task_id
            })
        time.sleep(5)
    return jsonify({"error": "Timeout menunggu hasil callback dari Suno API. Pastikan koneksi dan callback URL (ngrok) aktif."}), 504

@musik_bp.route('/get_music_result/<task_id>', methods=['GET'])
def get_music_result(task_id):
    callback_file = f'suno_callback_result_{task_id}.json'
    if not os.path.exists(callback_file):
        return jsonify({"status": "processing", "message": "Musik sedang diproses..."}), 200
    try:
        with open(callback_file, 'r', encoding='utf-8') as f:
            callback_data = json.load(f)
        cb_data = callback_data.get('data', {})
        result_list = cb_data.get('data', [])
        # Ambil hasil pertama (atau semua jika mau)
        if result_list:
            item = result_list[0]
            user_id = session.get('user_id')
            if user_id and item.get('audio_url'):
                # If result_list contains multiple songs, handle both
                for item in result_list:
                    exists = Song.query.filter_by(user_id=user_id, audio_url=item.get('audio_url')).first()
                    if not exists:
                        new_song = Song(
                            id=str(uuid.uuid4()),
                            user_id=user_id,
                            title=item.get('title', ''),
                            prompt=item.get('prompt', ''),
                            model_name=item.get('model_name', ''),
                            duration=item.get('duration', 0),
                            image_url=item.get('image_url', ''),
                            audio_url=item.get('audio_url', ''),
                            stream_audio_url=item.get('stream_audio_url', ''),
                            source_audio_url=item.get('source_audio_url', ''),
                            source_image_url=item.get('source_image_url', ''),
                            source_stream_audio_url=item.get('source_stream_audio_url', '')
                        )
                        db.session.add(new_song)
                        db.session.commit()

            return jsonify({
                "status": "complete" if item.get('audio_url') else "processing",
                "lyrics": item.get('prompt', ''),
                "audio_url": item.get('audio_url', ''),
                "image_url": item.get('image_url', ''),
                "title": item.get('title', ''),
                "tags": item.get('tags', ''),
                "duration": item.get('duration', 0),
                "model_name": item.get('model_name', '')
            }), 200
        else:
            return jsonify({"status": "processing", "message": "Belum ada hasil."}), 200
    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan: {e}"}), 500

# Endpoint untuk menerima callback dari Suno API
@musik_bp.route('/callback', methods=['POST'])
def suno_callback():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Empty callback data"}), 400
        task_id = data.get('data', {}).get('task_id')
        if not task_id:
            return jsonify({"error": "No task_id in callback"}), 400
        callback_file = f'suno_callback_result_{task_id}.json'
        with open(callback_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"status": "success", "message": "Callback received"}), 200
    except Exception as e:
        return jsonify({"error": f"Callback processing error: {str(e)}"}), 500

@musik_bp.route('/foto/<path:filename>')
def foto_static(filename):
    return send_from_directory('foto', filename)

# Contoh endpoint generate musik (dummy, sesuaikan dengan logic lama)
@musik_bp.route('/musik/generate', methods=['POST'])
def generate_musik():
    data = request.json
    prompt = data.get('prompt')
    genre = data.get('genre')
    title = data.get('title')
    instrumental = data.get('instrumental', False)
    duration = int(data.get('duration', 30))
    # Simulasi hasil musik, ganti dengan model asli jika ada
    dummy_path = "dummy.mp3"
    if not os.path.exists(dummy_path):
        with open(dummy_path, "wb") as f:
            f.write(b"\x00\x00\x00\x00")  # file kosong
    os.makedirs("static/audio_results", exist_ok=True)
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = os.path.join("static/audio_results", filename)
    with open(dummy_path, "rb") as src, open(filepath, "wb") as dst:
        dst.write(src.read())
    return jsonify({"audio_url": f"/static/audio_results/{filename}", "message": "Musik berhasil dibuat dan disimpan"})

@musik_bp.route('/audio_results/<filename>')
def serve_audio_result(filename):
    return send_from_directory('audio_results', filename)

@musik_bp.route('/generate_music', methods=['POST'])
def generate_music():
    data = request.json
    prompt = data.get('prompt')
    genre = data.get('genre')
    title = data.get('title')
    instrumental = data.get('instrumental', False)
    duration = int(data.get('duration', 30))
    # Kredit logic
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    from models import User
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User tidak ditemukan'}), 404
    if user.kredit < 15:
        return jsonify({'error': 'Kredit Anda tidak cukup untuk generate musik (minimal 15 kredit)'}), 403
    user.kredit -= 15
    db.session.commit()
    # Simulasi hasil musik, ganti dengan model asli jika ada
    dummy_path = "dummy.mp3"
    if not os.path.exists(dummy_path):
        with open(dummy_path, "wb") as f:
            f.write(b"\x00\x00\x00\x00")  # file kosong
    os.makedirs("static/audio_results", exist_ok=True)
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = os.path.join("static/audio_results", filename)
    with open(dummy_path, "rb") as src, open(filepath, "wb") as dst:
        dst.write(src.read())
    return jsonify({"audio_url": f"/static/audio_results/{filename}", "message": "Musik berhasil dibuat dan disimpan"})
