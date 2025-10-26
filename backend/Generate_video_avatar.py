import os
import requests
import json
import time
import uuid
from flask import Blueprint, render_template, request, jsonify, session, current_app, redirect
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from models import db, Video, User, Image

load_dotenv()

# Create blueprint
generate_video_avatar_bp = Blueprint('generate_video_avatar', __name__)

# Allowed file extensions for avatar images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Allowed file extensions for audio files
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_audio_file(filename):
    if not filename or '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    print(f"Checking audio file extension: {extension} against allowed: {ALLOWED_AUDIO_EXTENSIONS}")
    return extension in ALLOWED_AUDIO_EXTENSIONS

def calculate_avatar_credits(text_length, estimated_duration=5):
    """Calculate credits needed for avatar video generation"""
    # Base credits for avatar video (TTS + Avatar generation)
    base_credits = 50
    
    # Additional credits based on text length (more text = more processing)
    text_credits = min(text_length // 10, 50)  # Max 50 credits for text
    
    # Additional credits based on estimated duration
    duration_credits = estimated_duration * 10  # 10 credits per second
    
    total_credits = base_credits + text_credits + duration_credits
    return total_credits  # No cap - credits should match actual duration

def deduct_credits(user_id, credits):
    """Deduct credits from user account"""
    try:
        user = User.query.get(user_id)
        if not user:
            raise Exception("User not found")
        
        if user.kredit < credits:
            raise Exception(f"Insufficient credits. Required: {credits}, Available: {user.kredit}")
        
        user.kredit -= credits
        db.session.commit()
        print(f"Credits deducted: {credits}, Remaining: {user.kredit}")
        return True
    except Exception as e:
        print(f"Error deducting credits: {str(e)}")
        db.session.rollback()
        return False

def detect_language_and_voice(text):
    """Detect language and select appropriate voice ID based on text characteristics"""
    # Enhanced Indonesian language detection
    indonesian_indicators = [
        # Greetings
        'selamat', 'pagi', 'siang', 'sore', 'malam', 'terima', 'kasih', 'sama', 'saja',
        # Common words
        'tidak', 'ya', 'bisa', 'akan', 'sudah', 'belum', 'mau', 'ingin', 'perlu', 'harus',
        # Pronouns
        'ini', 'itu', 'saya', 'kamu', 'dia', 'kita', 'mereka', 'kami', 'anda', 'bapak', 'ibu',
        # Common verbs
        'adalah', 'ada', 'pergi', 'datang', 'makan', 'minum', 'tidur', 'bekerja', 'belajar',
        # Common adjectives
        'baik', 'buruk', 'besar', 'kecil', 'tinggi', 'rendah', 'panjang', 'pendek', 'baru', 'lama',
        # Common nouns
        'rumah', 'mobil', 'motor', 'jalan', 'kota', 'desa', 'negara', 'dunia', 'orang', 'anak',
        # Indonesian-specific words
        'yang', 'dengan', 'untuk', 'dari', 'ke', 'di', 'pada', 'dalam', 'atas', 'bawah'
    ]
    
    # Voice characteristics analysis
    formal_words = ['selamat', 'terima', 'kasih', 'anda', 'bapak', 'ibu', 'negara', 'dunia', 'hormat', 'salam']
    casual_words = ['kamu', 'gue', 'lo', 'teman', 'bro', 'sis', 'mantap', 'keren', 'asik', 'oke', 'yuk']
    emotional_words = ['senang', 'bahagia', 'gembira', 'sedih', 'marah', 'takut', 'bangga', 'haru', 'senyum', 'tawa']
    professional_words = ['presentasi', 'meeting', 'proyek', 'laporan', 'analisis', 'strategi', 'bisnis', 'perusahaan', 'manajemen']
    medical_words = ['pasien', 'dokter', 'obat', 'penyakit', 'kesehatan', 'rumah sakit', 'perawatan', 'terapi']
    educational_words = ['belajar', 'mengajar', 'sekolah', 'universitas', 'pendidikan', 'ilmu', 'pengetahuan', 'siswa']
    
    text_lower = text.lower()
    words = text_lower.split()
    total_words = len(words)
    
    # Calculate scores
    indonesian_score = sum(1 for word in indonesian_indicators if word in text_lower)
    formal_score = sum(1 for word in formal_words if word in text_lower)
    casual_score = sum(1 for word in casual_words if word in text_lower)
    emotional_score = sum(1 for word in emotional_words if word in text_lower)
    professional_score = sum(1 for word in professional_words if word in text_lower)
    medical_score = sum(1 for word in medical_words if word in text_lower)
    educational_score = sum(1 for word in educational_words if word in text_lower)
    
    indonesian_percentage = (indonesian_score / total_words * 100) if total_words > 0 else 0
    
    print(f"Indonesian words detected: {indonesian_score}/{total_words} ({indonesian_percentage:.1f}%)")
    print(f"Formal: {formal_score}, Casual: {casual_score}, Emotional: {emotional_score}")
    print(f"Professional: {professional_score}, Medical: {medical_score}, Educational: {educational_score}")
    
    # Voice selection logic based on text characteristics
    if indonesian_percentage >= 30 or indonesian_score >= 3:
        # Indonesian voices based on characteristics
        if medical_score > 0:
            # Medical content - caring and professional
            return "Indonesian_CaringMan", "Indonesian", "neutral"
        elif educational_score > 0:
            # Educational content - clear and confident
            return "Indonesian_ConfidentWoman", "Indonesian", "neutral"
        elif professional_score > 0 or formal_score > casual_score:
            # Professional/formal content
            if emotional_score > 0:
                return "Indonesian_ConfidentWoman", "Indonesian", "happy"
            else:
                return "Indonesian_BossyLeader", "Indonesian", "neutral"
        elif casual_score > formal_score:
            # Casual/friendly content
            if emotional_score > 0:
                return "Indonesian_CharmingGirl", "Indonesian", "happy"
            else:
                return "Indonesian_CaringMan", "Indonesian", "neutral"
        elif emotional_score > 0:
            # Emotional content
            return "Indonesian_SweetGirl", "Indonesian", "happy"
        else:
            # Default Indonesian
            return "Indonesian_ReservedYoungMan", "Indonesian", "happy"
    else:
        # Non-Indonesian or mixed content - use Patient_Man for better compatibility
        return "Patient_Man", "Indonesian", "neutral"

def generate_tts_audio(text, selected_voice_id=None, language_boost="Indonesian"):
    """Generate audio from text using Minimax TTS API with automatic language detection"""
    try:
        API_KEY = os.getenv("WAVESPEED_API_KEY")
        if not API_KEY:
            raise Exception("API key not found")
        
        # Use selected voice or auto-detect
        if selected_voice_id:
            voice_id = selected_voice_id
            # Determine language and emotion based on voice_id
            if selected_voice_id.startswith('Indonesian_'):
                language = language_boost  # Use selected language boost
                emotion = "happy" if any(word in selected_voice_id.lower() for word in ['sweet', 'charming', 'emotional']) else "neutral"
            else:
                language = language_boost  # Use selected language boost
                emotion = "neutral"
        else:
            # Auto-detect language and voice
            voice_id, language, emotion = detect_language_and_voice(text)
            language = language_boost  # Override with selected language boost
        
        url = "https://api.wavespeed.ai/api/v3/minimax/speech-2.5-turbo-preview"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }
        payload = {
            "emotion": emotion,
            "enable_sync_mode": False,
            "english_normalization": False,
            "language_boost": language_boost,
            "pitch": 0,
            "speed": 1,
            "text": text,
            "voice_id": voice_id,
            "volume": 1
        }

        print(f"Generating TTS audio for text: {text[:50]}...")
        print(f"Voice ID: {voice_id}, Language Boost: {language_boost}, Emotion: {emotion}")
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            result = response.json()["data"]
            request_id = result["id"]
            print(f"TTS task submitted successfully. Request ID: {request_id}")
        else:
            raise Exception(f"TTS API Error: {response.status_code}, {response.text}")

        # Poll for TTS results
        url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        max_attempts = 40  # 20 seconds max (reduced from 60)
        attempt = 0
        
        while attempt < max_attempts:
            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    result = response.json()["data"]
                    status = result["status"]

                    if status == "completed":
                        audio_url = result["outputs"][0]
                        print(f"TTS completed. Audio URL: {audio_url}")
                        return audio_url
                    elif status == "failed":
                        raise Exception(f"TTS failed: {result.get('error', 'Unknown error')}")
                    else:
                        print(f"TTS still processing. Status: {status}")
                        if attempt % 10 == 0:  # Every 5 seconds
                            progress_percent = (attempt / max_attempts) * 100
                            print(f"TTS Progress: {attempt}/{max_attempts} attempts ({progress_percent:.1f}%)")
                else:
                    raise Exception(f"TTS polling error: {response.status_code}, {response.text}")
            except requests.exceptions.Timeout:
                print(f"TTS polling timeout, continuing... (attempt {attempt + 1}/{max_attempts})")
            except requests.exceptions.RequestException as e:
                print(f"TTS polling request error: {str(e)}, continuing... (attempt {attempt + 1}/{max_attempts})")

            time.sleep(0.5)
            attempt += 1
        
        raise Exception("TTS timeout - took too long to complete")
        
    except Exception as e:
        print(f"TTS Error: {str(e)}")
        raise e

def generate_avatar_video(audio_url, image_url, image_path=None):
    """Generate avatar video using Bytedance Avatar API"""
    try:
        API_KEY = os.getenv("WAVESPEED_API_KEY")
        if not API_KEY:
            raise Exception("API key not found")
        
        url = "https://api.wavespeed.ai/api/v3/bytedance/avatar-omni-human-1.5"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }
        # Try to use base64 encoding if URL is not accessible
        if image_path and os.path.exists(image_path):
            try:
                # First, try to access the image URL to see if it's accessible
                test_response = requests.head(image_url, timeout=5)
                if test_response.status_code != 200:
                    print(f"Image URL not accessible, using base64 encoding")
                    # Read image file and convert to base64
                    import base64
                    with open(image_path, 'rb') as f:
                        image_data = f.read()
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    payload = {
                        "audio": audio_url,
                        "image": f"data:image/jpeg;base64,{image_base64}",
                        "enable_base64_output": False
                    }
                else:
                    payload = {
                        "audio": audio_url,
                        "image": image_url,
                        "enable_base64_output": False
                    }
            except Exception as e:
                print(f"Error testing image URL, using base64 encoding: {str(e)}")
                # Fallback to base64 encoding
                import base64
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                payload = {
                    "audio": audio_url,
                    "image": f"data:image/jpeg;base64,{image_base64}",
                    "enable_base64_output": False
                }
        else:
            # Use URL directly if no local path available
            payload = {
                "audio": audio_url,
                "image": image_url,
                "enable_base64_output": False
            }

        print(f"Generating avatar video with audio: {audio_url} and image: {image_url}")
        
        # Add timeout and retry mechanism for initial request
        max_retries = 3
        for retry in range(max_retries):
            try:
                response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
                break
            except requests.exceptions.Timeout:
                if retry == max_retries - 1:
                    raise Exception("API request timeout after multiple retries")
                print(f"Request timeout, retrying... ({retry + 1}/{max_retries})")
                time.sleep(2)
            except requests.exceptions.RequestException as e:
                if retry == max_retries - 1:
                    raise Exception(f"API request failed: {str(e)}")
                print(f"Request failed, retrying... ({retry + 1}/{max_retries}): {str(e)}")
                time.sleep(2)
        
        if response.status_code == 200:
            result = response.json()["data"]
            request_id = result["id"]
            print(f"Avatar video task submitted successfully. Request ID: {request_id}")
            
            # Return request ID immediately for polling
            return request_id
        else:
            raise Exception(f"Avatar API Error: {response.status_code}, {response.text}")
        
    except Exception as e:
        print(f"Avatar Video Error: {str(e)}")
        raise e

def download_and_save_file(url, filepath):
    """Download file from URL and save to local path"""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Ensure the file has .mp4 extension
        if not filepath.endswith('.mp4'):
            filepath = filepath + '.mp4'
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"File saved to: {filepath}")
        
        # Verify file was saved and has content
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            print(f"Video file verified: {os.path.getsize(filepath)} bytes")
            return True
        else:
            print("Error: Video file is empty or doesn't exist")
            return False
            
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        return False

def upload_manual_audio(audio_file):
    """Handle manual audio file upload and return the URL"""
    try:
        if not audio_file or not audio_file.filename:
            raise Exception("No audio file provided")
        
        if not allowed_audio_file(audio_file.filename):
            print(f"Audio file validation failed for: {audio_file.filename}")
            raise Exception("Invalid audio file type. Please upload MP3, WAV, M4A, AAC, OGG, or FLAC")
        
        # Check file size (max 50MB)
        if hasattr(audio_file, 'content_length') and audio_file.content_length > 50 * 1024 * 1024:
            raise Exception("Audio file too large. Maximum 50MB allowed")
        
        # Generate unique filename
        filename = secure_filename(audio_file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        audio_path = os.path.join(current_app.static_folder, 'uploads', 'audio', unique_filename)
        
        # Ensure uploads directory exists
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        
        # Save audio file
        audio_file.save(audio_path)
        
        # Verify file was saved
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            # Get public URL for the uploaded audio
            audio_url = f"/static/uploads/audio/{unique_filename}"
            domain_public = current_app.config.get('DOMAIN_PUBLIC', request.host_url.rstrip('/'))
            full_audio_url = f"{domain_public}{audio_url}"
            
            print(f"Manual audio uploaded successfully: {full_audio_url}")
            return full_audio_url, audio_path
        else:
            raise Exception("Failed to save audio file")
            
    except Exception as e:
        print(f"Error uploading manual audio: {str(e)}")
        raise e

@generate_video_avatar_bp.route('/generate_video_avatar')
def generate_video_avatar_page():
    """Render the generate video avatar page"""
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect('/login')
    
    # Check if user has premium access
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return redirect('/login')
    
    # Check if user role is not free (premium, premier, or admin)
    if user.role == 'free':
        return redirect('/home')  # Redirect to home if not premium
    
    return render_template('Generate_video_avatar.html')

@generate_video_avatar_bp.route('/api/gallery/images', methods=['GET'])
def gallery_images():
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login', 'redirect': '/login'}), 401
    
    # Check if user has premium access
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User tidak ditemukan', 'redirect': '/login'}), 401
    
    if user.role == 'free':
        return jsonify({'error': 'Fitur ini hanya tersedia untuk user premium', 'redirect': '/home'}), 403
    
    images = Image.query.order_by(Image.created_at.desc()).limit(50).all()
    data = [
        {
            'id': img.id,
            'url': img.image_url,
            'caption': img.caption or ''
        } for img in images
    ]
    return jsonify({'success': True, 'images': data})

@generate_video_avatar_bp.route('/api/gallery/generated', methods=['GET'])
def gallery_generated_images():
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login', 'redirect': '/login'}), 401
    
    # Check if user has premium access
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User tidak ditemukan', 'redirect': '/login'}), 401
    
    if user.role == 'free':
        return jsonify({'error': 'Fitur ini hanya tersedia untuk user premium', 'redirect': '/home'}), 403
    
    # Ambil video yang punya thumbnail atau image_url
    videos = Video.query.order_by(Video.created_at.desc()).limit(50).all()
    data = [
        {
            'id': vid.id,
            'url': getattr(vid, 'image_url', None) or '',
            'caption': vid.caption or ''
        } for vid in videos if getattr(vid, 'image_url', None)
    ]
    return jsonify({'success': True, 'images': data})

@generate_video_avatar_bp.route('/api/avatar_status/<request_id>', methods=['GET'])
def check_avatar_status(request_id):
    """Check if avatar generation is still processing"""
    try:
        print(f"=== CHECKING AVATAR STATUS ===")
        print(f"Request ID: {request_id}")
        print(f"User ID: {session.get('user_id')}")
        
        # Check if user is logged in
        if 'user_id' not in session:
            print("Error: User not logged in")
            return jsonify({'error': 'Please login first'}), 401
        
        # Check if user has premium access
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            print("Error: User not found")
            return jsonify({'error': 'User not found'}), 401
        
        if user.role == 'free':
            print("Error: User does not have premium access")
            return jsonify({'error': 'Fitur ini hanya tersedia untuk user premium'}), 403
        
        API_KEY = os.getenv("WAVESPEED_API_KEY")
        if not API_KEY:
            print("Error: API key not found")
            return jsonify({'error': 'API key not found'}), 500
        
        # Check status with external API
        url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
        headers = {"Authorization": f"Bearer {API_KEY}"}
        print(f"Checking external API: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=30)  # Increased timeout
            print(f"External API response status: {response.status_code}")
            
            if response.status_code == 200:
                full_response = response.json()
                print(f"Full external API response: {full_response}")
                
                if "data" in full_response:
                    result = full_response["data"]
                    status = result["status"]
                    print(f"External API status: {status}")
                    print(f"External API result: {result}")
                else:
                    print(f"No 'data' field in response: {full_response}")
                    # Check if response has direct status field
                    if "status" in full_response:
                        status = full_response["status"]
                        result = full_response
                        print(f"Direct status from response: {status}")
                    else:
                        print(f"No status field found in response: {full_response}")
                        # Check if there are any outputs even without status
                        if "outputs" in full_response and len(full_response["outputs"]) > 0:
                            print(f"Found outputs without status, treating as completed")
                            video_url = full_response["outputs"][0]
                            print(f"Video completed! URL: {video_url}")
                            
                            # Download and save the video
                            video_filename = f"avatar_video_{uuid.uuid4()}.mp4"
                            video_path = os.path.join(current_app.static_folder, 'outputs', video_filename)
                            
                            # Ensure outputs directory exists
                            os.makedirs(os.path.dirname(video_path), exist_ok=True)
                            
                            if download_and_save_file(video_url, video_path):
                                # Ensure the filename has .mp4 extension
                                if not video_filename.endswith('.mp4'):
                                    video_filename = video_filename + '.mp4'
                                local_video_url = f"/static/outputs/{video_filename}"
                                print(f"Video saved locally: {local_video_url}")
                                
                                # Save to database
                                user_id = session.get('user_id')
                                text = request.args.get('text', '')  # Get text from query params
                                caption = f"AI Avatar Video: {text[:100]}{'...' if len(text) > 100 else ''}"
                                
                                try:
                                    video_record = Video(
                                        user_id=user_id,
                                        video_url=local_video_url,
                                        caption=caption
                                    )
                                    db.session.add(video_record)
                                    db.session.commit()
                                    print(f"Video avatar saved to database with ID: {video_record.id}")
                                except Exception as e:
                                    print(f"Error saving video to database: {str(e)}")
                                    db.session.rollback()
                                
                                return jsonify({
                                    'success': True,
                                    'status': 'completed',
                                    'video_url': local_video_url,
                                    'message': 'Avatar video generation completed successfully!'
                                })
                            else:
                                print("Failed to download video")
                                return jsonify({
                                    'success': False,
                                    'status': 'failed',
                                    'error': 'Failed to download generated video'
                                })
                        else:
                            return jsonify({
                                'success': True,
                                'status': 'processing',
                                'message': 'Avatar generation is still in progress'
                            })
                
                if status == "completed" or status == "succeeded" or status == "done":
                    print(f"Status is completed! Checking outputs...")
                    print(f"Result keys: {result.keys()}")
                    
                    if "outputs" in result and len(result["outputs"]) > 0:
                        video_url = result["outputs"][0]
                        print(f"Video completed! URL: {video_url}")
                    elif "outputs" in full_response and len(full_response["outputs"]) > 0:
                        video_url = full_response["outputs"][0]
                        print(f"Video completed! URL from full response: {video_url}")
                    else:
                        print(f"No outputs found in completed result: {result}")
                        print(f"Full response: {full_response}")
                        # Check if there are any other fields that might contain the video URL
                        for key, value in full_response.items():
                            if isinstance(value, str) and (value.endswith('.mp4') or value.endswith('.avi') or value.endswith('.mov')):
                                print(f"Found video URL in field {key}: {value}")
                                video_url = value
                                break
                        else:
                            return jsonify({
                                'success': False,
                                'status': 'failed',
                                'error': 'No video output found in completed result'
                            })
                    
                    # Download and save the video
                    video_filename = f"avatar_video_{uuid.uuid4()}.mp4"
                    video_path = os.path.join(current_app.static_folder, 'outputs', video_filename)
                    
                    # Ensure outputs directory exists
                    os.makedirs(os.path.dirname(video_path), exist_ok=True)
                    
                    if download_and_save_file(video_url, video_path):
                        # Ensure the filename has .mp4 extension
                        if not video_filename.endswith('.mp4'):
                            video_filename = video_filename + '.mp4'
                        local_video_url = f"/static/outputs/{video_filename}"
                        print(f"Video saved locally: {local_video_url}")
                        
                        # Save to database
                        user_id = session.get('user_id')
                        text = request.args.get('text', '')  # Get text from query params
                        caption = f"AI Avatar Video: {text[:100]}{'...' if len(text) > 100 else ''}"
                        
                        try:
                            video_record = Video(
                                user_id=user_id,
                                video_url=local_video_url,
                                caption=caption
                            )
                            db.session.add(video_record)
                            db.session.commit()
                            print(f"Video avatar saved to database with ID: {video_record.id}")
                        except Exception as e:
                            print(f"Error saving video to database: {str(e)}")
                            db.session.rollback()
                        
                        return jsonify({
                            'success': True,
                            'status': 'completed',
                            'video_url': local_video_url,
                            'message': 'Avatar video generation completed successfully!'
                        })
                    else:
                        print("Failed to download video")
                        return jsonify({
                            'success': False,
                            'status': 'failed',
                            'error': 'Failed to download generated video'
                        })
                elif status == "failed" or status == "error" or status == "cancelled":
                    error_msg = result.get('error', 'Unknown error')
                    print(f"Video generation failed: {error_msg}")
                    return jsonify({
                        'success': False,
                        'status': 'failed',
                        'error': f'Avatar video failed: {error_msg}'
                    })
                else:
                    print(f"Video still processing: {status}")
                    print(f"Full result for processing: {result}")
                    
                    # Check execution time to provide better feedback
                    execution_time = result.get('executionTime', 0)
                    print(f"Execution time so far: {execution_time} seconds")
                    
                    # Check if there are any outputs even if status is not completed
                    if "outputs" in result and len(result["outputs"]) > 0:
                        print(f"Found outputs in processing status, treating as completed")
                        video_url = result["outputs"][0]
                        print(f"Video completed! URL: {video_url}")
                    elif "outputs" in full_response and len(full_response["outputs"]) > 0:
                        print(f"Found outputs in full response, treating as completed")
                        video_url = full_response["outputs"][0]
                        print(f"Video completed! URL from full response: {video_url}")
                    else:
                        # Check if there are any other fields that might contain the video URL
                        video_url = None
                        for key, value in full_response.items():
                            if isinstance(value, str) and (value.endswith('.mp4') or value.endswith('.avi') or value.endswith('.mov')):
                                print(f"Found video URL in field {key}: {value}")
                                video_url = value
                                break
                        
                        if video_url:
                            print(f"Video completed! URL: {video_url}")
                        else:
                            # Provide more informative message based on execution time
                            if execution_time > 300:  # More than 5 minutes
                                message = f'Avatar generation is taking longer than expected (over {execution_time//60} minutes). This is normal for longer text. Please continue waiting...'
                            elif execution_time > 120:  # More than 2 minutes
                                message = f'Avatar generation is in progress ({execution_time//60} minutes elapsed). Longer text takes more time to process...'
                            else:
                                message = 'Avatar generation is in progress. Please wait...'
                            
                            return jsonify({
                                'success': True,
                                'status': 'processing',
                                'message': message,
                                'execution_time': execution_time
                            })
                    
                    # Download and save the video
                    video_filename = f"avatar_video_{uuid.uuid4()}.mp4"
                    video_path = os.path.join(current_app.static_folder, 'outputs', video_filename)
                    
                    # Ensure outputs directory exists
                    os.makedirs(os.path.dirname(video_path), exist_ok=True)
                    
                    if download_and_save_file(video_url, video_path):
                        # Ensure the filename has .mp4 extension
                        if not video_filename.endswith('.mp4'):
                            video_filename = video_filename + '.mp4'
                        local_video_url = f"/static/outputs/{video_filename}"
                        print(f"Video saved locally: {local_video_url}")
                        
                        # Save to database
                        user_id = session.get('user_id')
                        text = request.args.get('text', '')  # Get text from query params
                        caption = f"AI Avatar Video: {text[:100]}{'...' if len(text) > 100 else ''}"
                        
                        try:
                            video_record = Video(
                                user_id=user_id,
                                video_url=local_video_url,
                                caption=caption
                            )
                            db.session.add(video_record)
                            db.session.commit()
                            print(f"Video avatar saved to database with ID: {video_record.id}")
                        except Exception as e:
                            print(f"Error saving video to database: {str(e)}")
                            db.session.rollback()
                        
                        return jsonify({
                            'success': True,
                            'status': 'completed',
                            'video_url': local_video_url,
                            'message': 'Avatar video generation completed successfully!'
                        })
                    else:
                        print("Failed to download video")
                        return jsonify({
                            'success': False,
                            'status': 'failed',
                            'error': 'Failed to download generated video'
                        })
            else:
                print(f"External API error: {response.status_code}")
                try:
                    error_response = response.json()
                    print(f"Error response: {error_response}")
                except:
                    print(f"Error response text: {response.text}")
                return jsonify({
                    'success': True,
                    'status': 'processing',
                    'message': 'Avatar generation is still in progress'
                })
        except requests.exceptions.RequestException as e:
            print(f"External API request error: {str(e)}")
            return jsonify({
                'success': True,
                'status': 'processing',
                'message': 'Checking avatar generation status... (API temporarily unavailable)'
            })
        except Exception as e:
            print(f"Unexpected error in status check: {str(e)}")
            return jsonify({
                'success': True,
                'status': 'processing',
                'message': 'Avatar generation is still in progress...'
            })
            
    except Exception as e:
        print(f"Error in check_avatar_status: {str(e)}")
        return jsonify({'error': 'Failed to check status'}), 500

@generate_video_avatar_bp.route('/api/check_video_status/<request_id>', methods=['GET'])
def check_video_status_simple(request_id):
    """Simple endpoint to check if video is ready without complex processing"""
    try:
        print(f"=== SIMPLE VIDEO STATUS CHECK ===")
        print(f"Request ID: {request_id}")
        
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'error': 'Please login first'}), 401
        
        # Check if user has premium access
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        if user.role == 'free':
            return jsonify({'error': 'Fitur ini hanya tersedia untuk user premium'}), 403
        
        API_KEY = os.getenv("WAVESPEED_API_KEY")
        if not API_KEY:
            return jsonify({'error': 'API key not found'}), 500
        
        # Check status with external API
        url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                full_response = response.json()
                print(f"Simple check response: {full_response}")
                
                if "data" in full_response:
                    result = full_response["data"]
                    status = result["status"]
                    
                    if status == "completed" and "outputs" in result and len(result["outputs"]) > 0:
                        video_url = result["outputs"][0]
                        return jsonify({
                            'success': True,
                            'status': 'completed',
                            'video_url': video_url,
                            'message': 'Video is ready!'
                        })
                    elif status == "failed":
                        return jsonify({
                            'success': False,
                            'status': 'failed',
                            'error': result.get('error', 'Video generation failed')
                        })
                    else:
                        execution_time = result.get('executionTime', 0)
                        return jsonify({
                            'success': True,
                            'status': 'processing',
                            'message': f'Still processing... ({execution_time//60}m {execution_time%60}s)',
                            'execution_time': execution_time
                        })
                else:
                    return jsonify({
                        'success': True,
                        'status': 'processing',
                        'message': 'Checking status...'
                    })
            else:
                return jsonify({
                    'success': True,
                    'status': 'processing',
                    'message': 'API temporarily unavailable, still checking...'
                })
        except Exception as e:
            print(f"Simple check error: {str(e)}")
            return jsonify({
                'success': True,
                'status': 'processing',
                'message': 'Still processing...'
            })
    except Exception as e:
        print(f"Error in simple check: {str(e)}")
        return jsonify({'error': 'Failed to check status'}), 500

@generate_video_avatar_bp.route('/api/upload_from_url', methods=['POST'])
def upload_from_url():
    """Upload image from URL for avatar generation"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'error': 'Please login first'}), 401
        
        # Check if user has premium access
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        if user.role == 'free':
            return jsonify({'error': 'Fitur ini hanya tersedia untuk user premium'}), 403
        
        data = request.get_json()
        image_url = data.get('image_url', '').strip()
        
        if not image_url:
            return jsonify({'error': 'Image URL is required'}), 400
        
        # Validate URL
        if not image_url.startswith(('http://', 'https://')):
            return jsonify({'error': 'Invalid image URL'}), 400
        
        # Return the URL as is, since it's already accessible
        return jsonify({
            'success': True,
            'url': image_url,
            'message': 'Image URL ready for processing'
        })
        
    except Exception as e:
        print(f"Error in upload_from_url: {str(e)}")
        return jsonify({'error': 'Failed to process image URL'}), 500

@generate_video_avatar_bp.route('/generate_video_avatar', methods=['POST'])
def generate_video_avatar():
    """Handle video avatar generation request"""
    try:
        print("=== Generate Video Avatar Request Started ===")
        print(f"Request method: {request.method}")
        print(f"Request content type: {request.content_type}")
        print(f"Request headers: {dict(request.headers)}")
        
        # Check if user is logged in
        if 'user_id' not in session:
            print("Error: User not logged in")
            return jsonify({'error': 'Please login first'}), 401
        
        # Check if user has premium access
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            print("Error: User not found")
            return jsonify({'error': 'User not found'}), 401
        
        # Check if user role is not free (premium, premier, or admin)
        if user.role == 'free':
            print("Error: User does not have premium access")
            return jsonify({'error': 'Fitur ini hanya tersedia untuk user premium. Silakan upgrade akun Anda terlebih dahulu.'}), 403
        
        # Get form data
        voice_mode = request.form.get('voice_mode', 'automatic').strip()
        text = request.form.get('text', '').strip()
        voice_id = request.form.get('voice_id', '').strip()
        language_boost = request.form.get('language_boost', 'Indonesian').strip()
        avatar_file = request.files.get('avatar_image')
        avatar_url = request.form.get('avatar_url', '').strip()
        manual_audio_file = request.files.get('manual_audio')
        
        print(f"Form data received:")
        print(f"  Voice Mode: {voice_mode}")
        print(f"  Text: {text[:50]}...")
        print(f"  Voice ID: {voice_id}")
        print(f"  Language Boost: {language_boost}")
        print(f"  Avatar file: {avatar_file.filename if avatar_file else 'None'}")
        print(f"  Avatar URL: {avatar_url}")
        print(f"  Manual audio file: {manual_audio_file.filename if manual_audio_file else 'None'}")
        
        # Validate inputs based on voice mode
        if voice_mode == 'automatic':
            if not text:
                print("Error: Text narration is required for automatic mode")
                return jsonify({'error': 'Text narration is required for automatic mode'}), 400
        elif voice_mode == 'manual':
            if not manual_audio_file:
                print("Error: Manual audio file is required for manual mode")
                return jsonify({'error': 'Manual audio file is required for manual mode'}), 400
            
            # Validate audio file
            if not allowed_audio_file(manual_audio_file.filename):
                print(f"Backend validation failed for audio file: {manual_audio_file.filename}")
                return jsonify({'error': 'Invalid audio file type. Please upload MP3, WAV, M4A, AAC, OGG, or FLAC'}), 400
        else:
            return jsonify({'error': 'Invalid voice mode'}), 400
        
        if not avatar_file and not avatar_url:
            return jsonify({'error': 'Avatar image is required'}), 400
        
        if avatar_file and not allowed_file(avatar_file.filename):
            return jsonify({'error': 'Invalid file type. Please upload PNG, JPG, JPEG, GIF, or WEBP'}), 400
        
        # Calculate and check credits based on voice mode
        if voice_mode == 'automatic':
            # Estimate duration based on text length (roughly 150 words per minute)
            estimated_duration = max(5, len(text.split()) // 2.5)  # Minimum 5 seconds
            required_credits = calculate_avatar_credits(len(text), estimated_duration)
        else:  # manual mode
            # For manual mode, use base credits (no TTS cost, only avatar generation)
            # We'll calculate the actual duration later from the audio file
            required_credits = 50  # Base credits only, will adjust if needed
        
        if user.kredit < required_credits:
            return jsonify({
                'error': f'Kredit tidak cukup. Diperlukan: {required_credits} kredit, Tersedia: {user.kredit} kredit'
            }), 403
        
        # Deduct credits before processing
        if not deduct_credits(user_id, required_credits):
            return jsonify({'error': 'Gagal memotong kredit'}), 500
        
        # Get domain_public first
        domain_public = current_app.config.get('DOMAIN_PUBLIC', request.host_url.rstrip('/'))
        
        # Handle avatar image (file upload or URL)
        avatar_path = None  # Initialize avatar_path
        if avatar_file:
            # Handle file upload
            filename = secure_filename(avatar_file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            avatar_path = os.path.join(current_app.static_folder, 'uploads', unique_filename)
            
            # Ensure uploads directory exists
            os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
            avatar_file.save(avatar_path)
            
            # Get public URL for the uploaded image
            avatar_url = f"/static/uploads/{unique_filename}"
            full_avatar_url = f"{domain_public}{avatar_url}"
        elif avatar_url:
            # Handle URL from gallery
            full_avatar_url = avatar_url
            # For gallery images, we don't have a local path, so we'll pass None
            avatar_path = None
        else:
            return jsonify({'error': 'Avatar image is required'}), 400
        
        print(f"Processing video avatar generation...")
        print(f"Voice mode: {voice_mode}")
        print(f"Text: {text[:100]}...")
        print(f"Avatar image URL: {full_avatar_url}")
        print(f"Domain public: {domain_public}")
        
        # Step 1: Handle audio based on voice mode
        if voice_mode == 'automatic':
            print("Step 1: Generating TTS audio...")
            start_time = time.time()
            audio_url = generate_tts_audio(text, voice_id, language_boost)
            tts_time = time.time() - start_time
            print(f"TTS completed in {tts_time:.2f} seconds")
        else:  # manual mode
            print("Step 1: Processing manual audio upload...")
            start_time = time.time()
            audio_url, audio_path = upload_manual_audio(manual_audio_file)
            upload_time = time.time() - start_time
            print(f"Manual audio upload completed in {upload_time:.2f} seconds")
        
        # Step 2: Generate avatar video
        print("Step 2: Generating avatar video...")
        start_time = time.time()
        
        # Get request ID from avatar video generation
        avatar_result = generate_avatar_video(audio_url, full_avatar_url, avatar_path)
        
        # Check if result is a URL (completed) or request ID (processing)
        if isinstance(avatar_result, str) and avatar_result.startswith('http'):
            # Video completed immediately
            video_url = avatar_result
            avatar_time = time.time() - start_time
            print(f"Avatar video completed in {avatar_time:.2f} seconds")
        else:
            # Video is still processing, return request ID
            request_id = avatar_result
            print(f"Avatar video processing started. Request ID: {request_id}")
            return jsonify({
                'success': True,
                'status': 'processing',
                'request_id': request_id,
                'message': 'Avatar video generation started. Please wait...'
            })
        
        # Step 3: Download and save video
        print("Step 3: Downloading and saving video...")
        start_time = time.time()
        video_filename = f"avatar_video_{uuid.uuid4()}.mp4"
        video_path = os.path.join(current_app.static_folder, 'outputs', video_filename)
        
        # Ensure outputs directory exists
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        
        if download_and_save_file(video_url, video_path):
            download_time = time.time() - start_time
            print(f"Video download completed in {download_time:.2f} seconds")
            
            # Save to database
            local_video_url = f"/static/outputs/{video_filename}"
            
            # User ID already obtained above
            
            # Create caption for the video based on voice mode
            if voice_mode == 'automatic':
                caption = f"AI Avatar Video: {text[:100]}{'...' if len(text) > 100 else ''}"
            else:  # manual mode
                # Use audio filename for caption since no text is provided
                audio_filename = manual_audio_file.filename if manual_audio_file else 'Custom Audio'
                caption = f"Avatar Video (Manual Audio): {audio_filename}"
            
            # Save video to database
            try:
                video_record = Video(
                    user_id=user_id,
                    video_url=local_video_url,
                    caption=caption
                )
                db.session.add(video_record)
                db.session.commit()
                
                print(f"Video avatar saved to database with ID: {video_record.id}")
                
                return jsonify({
                    'success': True,
                    'video_url': local_video_url,
                    'video_id': video_record.id,
                    'message': 'Video avatar generated and saved successfully!'
                })
            except Exception as e:
                print(f"Error saving video to database: {str(e)}")
                db.session.rollback()
                # Still return success even if database save fails
                return jsonify({
                    'success': True,
                    'video_url': local_video_url,
                    'message': 'Video avatar generated successfully! (Database save failed)'
                })
        else:
            return jsonify({'error': 'Failed to download generated video'}), 500
            
    except Exception as e:
        print(f"=== ERROR in generate_video_avatar ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"Error details: {repr(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        print("=== END ERROR ===")
        
        # Ensure we always return JSON
        try:
            return jsonify({'error': f'Generation failed: {str(e)}'}), 500
        except Exception as json_error:
            print(f"Error creating JSON response: {str(json_error)}")
            # Fallback to simple text response if JSON fails
            from flask import Response
            return Response(
                f'{{"error": "Generation failed: {str(e)}"}}',
                status=500,
                mimetype='application/json'
            )
