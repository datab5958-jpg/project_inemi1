from flask import Blueprint, render_template, request, jsonify, session, current_app, url_for
from flask.testing import FlaskClient
import requests
import re
import time
import os
import json
import google.generativeai as genai
from config import Config
from models import db, Image, User, Video, Song

ai_generate_bp = Blueprint('ai_generate', __name__)

# Initialize Gemini for chat
GEMINI_API_KEY = Config.GEMINI_API_KEY
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    text_model = genai.GenerativeModel('gemini-2.0-flash')
else:
    text_model = None

# Chat history storage (in-memory, consider using Redis in production)
chat_history = {}

# Task ID to User ID mapping (for callback handling)
# Format: {task_id: {'user_id': user_id, 'created_at': datetime}}
task_user_mapping = {}


@ai_generate_bp.route('/ai_generate', methods=['GET'])
def ai_generate_page():
    return render_template('ai_generate.html')


@ai_generate_bp.route('/api/ai_generate/check-session', methods=['GET'])
def check_session():
    """Debug endpoint to check session status"""
    return jsonify({
        'logged_in': 'user_id' in session,
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'session_keys': list(session.keys()),
        'has_cookie': 'Cookie' in request.headers
    })


@ai_generate_bp.route('/api/ai_generate/upload', methods=['POST'])
def upload_file():
    """Upload file for attachment (image/video)"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        import base64
        from werkzeug.utils import secure_filename
        
        # Validasi ekstensi file
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'mov', 'avi', 'webm'}
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        
        if ext not in allowed_extensions:
            return jsonify({'error': 'Tipe file tidak didukung. Gunakan PNG, JPG, JPEG, GIF, WEBP, MP4, MOV, AVI, atau WEBM'}), 400
        
        # Validasi MIME type
        allowed_mimes = {
            'image/png', 'image/jpeg', 'image/gif', 'image/webp',
            'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm'
        }
        mime_type = file.content_type or ('image/jpeg' if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp'] else 'video/mp4')
        
        if mime_type not in allowed_mimes:
            return jsonify({'error': 'Tipe MIME file tidak valid'}), 400
        
        # Batasi ukuran file (10MB untuk image, 50MB untuk video)
        file.seek(0, 2)  # move to end
        file_length = file.tell()
        file.seek(0)
        
        max_size = 50 * 1024 * 1024 if 'video' in mime_type else 10 * 1024 * 1024
        if file_length > max_size:
            max_size_mb = 50 if 'video' in mime_type else 10
            return jsonify({'error': f'Ukuran file terlalu besar (maksimal {max_size_mb}MB)'}), 400
        
        # Convert to base64 data URL
        file_content = file.read()
        base64_data = base64.b64encode(file_content).decode('utf-8')
        data_url = f"data:{mime_type};base64,{base64_data}"
        
        return jsonify({
            'success': True,
            'url': data_url,
            'type': 'image' if 'image' in mime_type else 'video',
            'filename': filename,
            'size': file_length
        })
    
    return jsonify({'error': 'Upload gagal'}), 500


def detect_intent(prompt: str, has_image: bool, mode: str = None) -> str:
    """Detect user intent from prompt. Returns 'chat' for general conversation, or specific generation type."""
    text = (prompt or '').lower().strip()
    
    # Chat-only phrases - ALWAYS treat as chat, even if mode is explicitly set
    # This check MUST be FIRST to override any explicit mode selection
    chat_only_phrases = [
        'halo', 'hello', 'hi', 'hai', 'hey',
        'selamat pagi', 'selamat siang', 'selamat sore', 'selamat malam',
        'good morning', 'good afternoon', 'good evening', 'good night',
        'terima kasih', 'thanks', 'thank you',
        'sama-sama', 'you\'re welcome',
        'apa kabar', 'how are you',
        'baik', 'fine', 'ok', 'oke',
        'boleh tanya', 'bisa tanya', 'can i ask',
        'tolong', 'please', 'bantu',
        'help', 'bantuan'
    ]
    
    # If mode is explicitly set (not empty string), use it FIRST (before any other checks)
    # This ensures user's explicit selection is ALWAYS respected
    # Only pure greetings can override explicit mode, and only if it's a very clear greeting
    if mode and mode.strip() and mode != 'auto':
        # Check if it's a pure greeting (very short, only greeting words)
        # Only override if it's REALLY a greeting, not a prompt that happens to contain greeting words
        words = text.split()
        is_really_greeting = False
        
        # Check if prompt is VERY short (1-3 words) and ONLY contains greeting phrases
        if len(words) <= 3:
            # Check if ALL words are greeting-related
            greeting_word_count = sum(1 for word in words if any(phrase in word.lower() for phrase in chat_only_phrases))
            if greeting_word_count == len(words) and len(words) > 0:
                is_really_greeting = True
        
        # If it's really just a greeting, allow chat override
        # Otherwise, use the explicit mode
        if is_really_greeting:
            print(f"[AI Generate] Pure greeting detected '{text}' - forcing chat intent (overriding mode: {mode})")
            return 'chat'
        else:
            print(f"[AI Generate] User explicitly selected mode: '{mode}' - using explicit mode (not a pure greeting)")
            return mode.strip()
    
    # If no explicit mode, check for pure greetings
    # This check is for AUTO-DETECT mode only
    is_pure_greeting = any(phrase in text for phrase in chat_only_phrases)
    if is_pure_greeting:
        # Check if prompt also contains generation action keywords
        # If yes, user might be saying "halo" then asking to generate something
        has_generation_action = any(kw in text for kw in ['buat', 'create', 'generate', 'bikin', 'buatkan', 'edit', 'ubah', 'jadikan'])
        if not has_generation_action:
            # Check if it's really just a greeting (short prompt, mostly greeting words)
            words = text.split()
            if len(words) <= 3:
                greeting_word_count = sum(1 for word in words if any(phrase in word.lower() for phrase in chat_only_phrases))
                if greeting_word_count == len(words) and len(words) > 0:
                    print(f"[AI Generate] Detected pure chat-only phrase: '{text[:50]}' - forcing chat intent")
                    return 'chat'
        # If has generation action, continue to check auto-detect
    
    # Also check for very short prompts (likely chat, not generation)
    # BUT: Only apply this if mode is AUTO-DETECT (not explicit)
    # If user explicitly selected a mode, they know what they want
    words = text.split()
    if len(words) <= 2 and not any(kw in text for kw in ['buat', 'create', 'generate', 'bikin', 'edit', 'ubah']):
        # Short prompt without action keywords
        # But if user has image, they might want to do something with it
        if has_image:
            # User has image but short prompt - might want to edit or convert
            # Let auto-detect handle it based on image presence
            print(f"[AI Generate] Short prompt '{text}' with image - will auto-detect based on context")
        else:
            # Short prompt without image - likely chat
            print(f"[AI Generate] Short prompt without action keywords: '{text}' - treating as chat")
            return 'chat'
    
    # Explicit generation action verbs - must be present for generation
    action_keywords = [
        'buat', 'create', 'generate', 'bikin', 'buatkan', 'buatlah', 'buatkanlah',
        'edit', 'ubah', 'perbaiki', 'modify', 'editlah', 'ubahlah',
        'jadikan', 'convert', 'transform', 'konversi'
    ]
    
    # Content type keywords
    content_keywords = {
        'image': ['gambar', 'image', 'foto', 'picture', 'photo', 'fotografi'],
        'video': ['video', 'vidio', 'film', 'movie'],
        'music': ['musik', 'music', 'lagu', 'song', 'audio', 'sound'],
        'edit': ['edit', 'ubah', 'perbaiki', 'modify', 'perbaiki', 'rubah']
    }
    
    # Check if prompt contains explicit generation action
    has_action = any(kw in text for kw in action_keywords)
    
    # If no explicit action keyword, treat as chat
    # Exception: Only if user has image AND explicitly mentions edit/video with action keyword
    if not has_action:
        # If user has image but no action keyword, it's still chat
        # They might be asking about the image or just chatting
        return 'chat'
    
    # Has action keyword - now check specific intents
    # Priority 1: Image edit (if has image AND mentions edit/ubah)
    if has_image and any(k in text for k in content_keywords['edit']):
        return 'image_edit'
    
    # Priority 2: Image to video (if has image AND mentions video conversion)
    if has_image and any(k in text for k in ['video', 'vidio', 'i2v', 'gambar jadi video', 'gambar jadi vidio']):
        return 'image_to_video'
    
    # Priority 3: Video generation (with action keyword)
    if has_action and any(k in text for k in content_keywords['video']):
        return 'video_generate'
    
    # Priority 4: Music generation (with action keyword)
    if has_action and any(k in text for k in content_keywords['music']):
        return 'music_generate'
    
    # Priority 5: Image generation (with action keyword)
    if has_action and any(k in text for k in content_keywords['image']):
        return 'image_generate'
    
    # If has action but unclear intent, treat as chat (let AI help clarify)
    return 'chat'


@ai_generate_bp.route('/api/ai_generate', methods=['POST'])
def api_ai_generate():
    # Check session - use same pattern as other endpoints
    # Try multiple ways to check session
    user_id = None
    
    # Method 1: Direct session.get
    if 'user_id' in session:
        user_id = session.get('user_id')
        print(f"[AI Generate] User ID from session: {user_id}")
    else:
        # Method 2: Check if session is empty
        print(f"[AI Generate DEBUG] Session check failed")
        print(f"  - Session keys: {list(session.keys())}")
        print(f"  - Session permanent: {session.permanent}")
        print(f"  - Request method: {request.method}")
        print(f"  - Request content type: {request.content_type}")
        print(f"  - Has Cookie header: {'Cookie' in request.headers}")
        if 'Cookie' in request.headers:
            print(f"  - Cookie header: {request.headers.get('Cookie')[:100]}...")  # First 100 chars
    
    if not user_id:
        return jsonify({
            'success': False, 
            'message': 'User belum login. Silakan login ulang.',
            'error': 'User belum login',
            'debug_info': {
                'session_keys': list(session.keys()),
                'has_user_id': 'user_id' in session
            }
        }), 401
    
    print(f"[AI Generate] Processing request for user_id: {user_id}")

    try:
        data = request.get_json(silent=True) or {}
        print(f"[AI Generate] Received data: {data}")
        prompt = (data.get('prompt') or '').strip()
        image_url = (data.get('image_url') or '').strip()
        mode = data.get('mode')
        print(f"[AI Generate] Parsed - prompt: '{prompt[:50]}...', image_url: '{image_url[:50] if image_url else 'None'}...', mode: {mode}")
    except Exception as e:
        print(f"[AI Generate] Error parsing request data: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error parsing request: {str(e)}'}), 400

    if not prompt:
        return jsonify({'success': False, 'message': 'Prompt tidak boleh kosong'}), 400

    try:
        intent = detect_intent(prompt, bool(image_url), mode)
        print(f"[AI Generate] Detected intent: {intent}")
    except Exception as e:
        print(f"[AI Generate] Error detecting intent: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error detecting intent: {str(e)}'}), 500

    base_url = current_app.config.get('DOMAIN_PUBLIC', 'http://127.0.0.1:5000')
    # Include session cookie in headers for internal requests
    headers = {
        "Content-Type": "application/json",
        "Cookie": request.headers.get('Cookie', '')
    }

    try:
        print(f"[AI Generate] Starting intent handling for: {intent}")
        # Handle chat conversation with Gemini
        if intent == 'chat':
            print(f"[AI Generate] Handling chat intent")
            if not text_model:
                return jsonify({'success': False, 'message': 'Gemini API tidak dikonfigurasi'}), 500
            
            user_id_str = str(user_id)
            if user_id_str not in chat_history:
                chat_history[user_id_str] = []
            
            # Add user message to history
            chat_history[user_id_str].append({'role': 'user', 'parts': [prompt]})
            
            # Get history for context (last 10 messages)
            history_for_gemini = chat_history[user_id_str][:-1]
            if len(history_for_gemini) > 10:
                history_for_gemini = history_for_gemini[-10:]
            
            # Create system instruction for more helpful and flexible AI assistant
            system_instruction = """Kamu adalah asisten AI yang cerdas dan fleksibel untuk platform generasi konten AI. 

Kemampuanmu:
1. **Chat Umum**: Menjawab pertanyaan, memberikan informasi, dan berdiskusi tentang berbagai topik
2. **Bantuan Prompt**: Membantu user membuat prompt yang efektif untuk generate gambar, video, atau musik
3. **Saran & Tips**: Memberikan saran dan tips untuk menghasilkan konten yang lebih baik
4. **Fleksibel**: Bisa merespons berbagai jenis pertanyaan dan permintaan

Fitur yang tersedia di platform ini:
- Generate Gambar (AI Image Generation)
- Edit Gambar (Image Editing dengan AI)
- Generate Video (Video Generation dengan Sora-2)
- Gambar ke Video (Image to Video dengan Sora-2)
- Generate Musik (Music Generation dengan Suno AI)

Selalu jawab dalam bahasa Indonesia yang ramah dan informatif. Jika user bertanya tentang cara membuat prompt atau membutuhkan bantuan, berikan saran yang praktis dan spesifik. Jika user ingin generate sesuatu, bantu mereka membuat prompt yang efektif."""

            # Start chat with history
            chat = text_model.start_chat(history=history_for_gemini)
            
            # For first message in conversation, include system instruction
            if not history_for_gemini:
                # First message - include system instruction in prompt
                enhanced_prompt = f"{system_instruction}\n\nUser: {prompt}\n\nAsisten: Jawab dengan ramah dan informatif dalam bahasa Indonesia."
            else:
                # Continue conversation - just add language instruction
                enhanced_prompt = f"{prompt}\n\nJawab dengan ramah dan informatif dalam bahasa Indonesia."
            
            response = chat.send_message(enhanced_prompt)
            
            # Clean markdown from response
            # Note: 're' is already imported at module level
            def bersihkan_markdown(teks):
                teks = re.sub(r'\*\*(.*?)\*\*', r'\1', teks)
                teks = re.sub(r'\*(.*?)\*', r'\1', teks)
                teks = re.sub(r'_(.*?)_', r'\1', teks)
                teks = re.sub(r'`(.*?)`', r'\1', teks)
                teks = re.sub(r'#+\s*', '', teks)
                teks = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', teks)
                teks = re.sub(r'!\[.*?\]\(.*?\)', '', teks)
                teks = re.sub(r'(?m)^\s*\d+\.\s+', '\n• ', teks)
                teks = re.sub(r'(?m)^\s*[-*+]\s+', '\n• ', teks)
                teks = re.sub(r'(?m)^\s*>\s*', '\n  ', teks)
                teks = re.sub(r'(?m)^\s+', '', teks)
                teks = re.sub(r'\n{3,}', '\n\n', teks)
                teks = re.sub(r'[ \t]+$', '', teks, flags=re.MULTILINE)
                return teks.strip()
            
            clean_response = bersihkan_markdown(response.text)
            
            # Add assistant response to history
            chat_history[user_id_str].append({'role': 'model', 'parts': [clean_response]})
            
            # Keep history manageable (last 20 messages total)
            if len(chat_history[user_id_str]) > 20:
                chat_history[user_id_str] = chat_history[user_id_str][-20:]
            
            return jsonify({
                'success': True,
                'type': 'chat',
                'message': clean_response,
                'history': chat_history[user_id_str]
            })
        
        if intent == 'image_edit':
            print(f"[AI Generate] Handling image_edit intent")
            # Use nano-banana edit logic from fusigaya
            if not image_url:
                return jsonify({'success': False, 'message': 'Image URL diperlukan untuk edit gambar'}), 400
            
            # Get user from database
            user = db.session.get(User, user_id)
            if not user:
                return jsonify({'success': False, 'message': 'User tidak ditemukan'}), 404
            
            # Check credits (nano-banana edit costs 15 credits in fusigaya)
            required_credits = 15
            if user.kredit < required_credits:
                return jsonify({
                    'success': False,
                    'message': f'Kredit Anda tidak cukup untuk edit gambar (minimal {required_credits} kredit)'
                }), 403
            
            # Get API key
            API_KEY = current_app.config.get('WAVESPEED_API_KEY')
            if not API_KEY:
                return jsonify({'success': False, 'message': 'API key tidak ditemukan'}), 500
            
            # Validate image URL or base64 data
            validated_images = []
            if image_url.startswith(('http://', 'https://')):
                try:
                    test_response = requests.head(image_url, timeout=5, allow_redirects=True)
                    if test_response.status_code in [200, 301, 302]:
                        validated_images.append(image_url)
                except Exception as e:
                    print(f'DEBUG: Image URL validation failed: {e}')
            elif image_url.startswith('data:image/'):
                # Base64 data URL
                if 'base64,' in image_url and len(image_url.split('base64,')[1]) > 0:
                    validated_images.append(image_url)
            
            if not validated_images:
                return jsonify({
                    'success': False,
                    'message': 'Gambar tidak valid. Gunakan URL (http/https) atau base64 data (data:image/...).'
                }), 400
            
            # Nano-banana edit endpoint
            url = "https://api.wavespeed.ai/api/v3/google/nano-banana/edit"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            }
            payload = {
                "enable_base64_output": False,
                "enable_sync_mode": False,
                "images": validated_images,
                "output_format": "jpeg",
                "prompt": prompt
            }
            
            print(f'[AI Generate] Nano-banana edit request')
            print(f'  - Image URL: {image_url[:100]}...')
            print(f'  - Prompt: {prompt[:100]}...')
            
            # Make initial request
            image_url_result = None
            error_message = None
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                print(f'[AI Generate] Nano-banana response: {response.status_code}')
                
                if response.status_code == 200:
                    result = response.json()
                    if "data" not in result:
                        error_message = 'Response API tidak valid: no data field'
                        raise Exception(error_message)
                    
                    result_data = result["data"]
                    if "id" not in result_data:
                        error_message = 'Response API tidak valid: no request id'
                        raise Exception(error_message)
                    
                    request_id = result_data["id"]
                    print(f'[AI Generate] Request ID: {request_id}')
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_msg = error_data['error']
                        elif 'message' in error_data:
                            error_msg = error_data['message']
                    except:
                        pass
                    
                    if response.status_code == 400:
                        error_message = f'Nano-banana edit gagal: {error_msg}. Pastikan gambar valid dan prompt sesuai.'
                    elif response.status_code == 422:
                        error_message = f'Format data tidak valid: {error_msg}. Periksa URL gambar dan prompt.'
                    else:
                        error_message = f'Server error: {error_msg}'
                    raise Exception(error_message)
            except requests.exceptions.Timeout:
                error_message = 'Request timeout. Coba lagi.'
                return jsonify({'success': False, 'message': error_message}), 504
            except Exception as e:
                error_message = str(e) if not error_message else error_message
                print(f'[AI Generate] Error: {error_message}')
                return jsonify({'success': False, 'message': error_message}), 500
            
            # Polling for results
            if 'request_id' in locals():
                poll_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
                poll_headers = {"Authorization": f"Bearer {API_KEY}"}
                
                max_attempts = 600  # 60 seconds with 0.1s interval
                attempt = 0
                
                while attempt < max_attempts:
                    try:
                        poll_response = requests.get(poll_url, headers=poll_headers, timeout=30)
                        
                        if poll_response.status_code == 200:
                            poll_result = poll_response.json()
                            if "data" not in poll_result:
                                attempt += 1
                                time.sleep(0.1)
                                continue
                            
                            poll_data = poll_result["data"]
                            status = poll_data.get("status")
                            
                            if status == "completed":
                                outputs = poll_data.get("outputs", [])
                                if outputs and len(outputs) > 0:
                                    image_url_result = outputs[0]
                                    print(f'[AI Generate] Edit completed: {image_url_result}')
                                    break
                                else:
                                    error_message = 'Tidak ada output gambar yang dihasilkan'
                                    raise Exception(error_message)
                            elif status == "failed":
                                error_msg = poll_data.get('error', 'Unknown error')
                                # Check for specific error types and provide user-friendly messages
                                error_msg_lower = error_msg.lower()
                                if 'content flagged' in error_msg_lower or 'potentially sensitive' in error_msg_lower:
                                    error_message = 'Konten dianggap tidak sesuai oleh sistem. Silakan coba dengan prompt yang berbeda atau lebih umum. Hindari konten yang mungkin dianggap sensitif.'
                                elif 'safety' in error_msg_lower or 'policy' in error_msg_lower:
                                    error_message = 'Prompt tidak memenuhi kebijakan konten. Silakan gunakan prompt yang lebih sesuai dengan pedoman konten.'
                                else:
                                    error_message = f'Task gagal: {error_msg}'
                                raise Exception(error_message)
                            elif status == "processing":
                                pass
                        else:
                            error_message = f'Gagal polling: HTTP {poll_response.status_code}'
                            raise Exception(error_message)
                    except Exception as e:
                        if 'error_message' not in locals() or not error_message:
                            error_message = str(e)
                        print(f'[AI Generate] Polling error: {error_message}')
                        if 'Task gagal' in error_message or 'Tidak ada output' in error_message:
                            break
                    
                    attempt += 1
                    time.sleep(0.1)
                
                # If failed, rollback credits and return error
                if not image_url_result:
                    try:
                        user.kredit += required_credits
                        db.session.commit()
                        print(f'[AI Generate] Credits rolled back due to failure')
                    except:
                        db.session.rollback()
                    
                    return jsonify({
                        'success': False,
                        'message': error_message or 'Timeout: Task took too long to complete'
                    }), 500
                
                # Success - deduct credits and save to database
                try:
                    user.kredit -= required_credits
                    image = Image(user_id=user_id, image_url=image_url_result, caption=f"Edit: {prompt}")
                    db.session.add(image)
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'type': 'image',
                        'action': 'edit',
                        'url': image_url_result,
                        'data': {
                            'photo_url': image_url_result,
                            'message': 'Gambar berhasil diedit menggunakan nano-banana',
                            'credits_used': required_credits
                        }
                    })
                except Exception as e:
                    db.session.rollback()
                    # Even if DB save fails, return success with URL
                    return jsonify({
                        'success': True,
                        'type': 'image',
                        'action': 'edit',
                        'url': image_url_result,
                        'data': {
                            'photo_url': image_url_result,
                            'message': 'Gambar berhasil diedit (gagal menyimpan ke database)',
                            'credits_used': required_credits
                        }
                    })

        if intent == 'image_to_video':
            print(f"[AI Generate] Handling image_to_video intent")
            
            # Validate image_url
            if not image_url:
                return jsonify({'success': False, 'message': 'Gambar tidak ditemukan. Silakan upload gambar terlebih dahulu.'}), 400
            
            # Check API key
            API_KEY = current_app.config.get('WAVESPEED_API_KEY')
            if not API_KEY:
                return jsonify({'success': False, 'message': 'API key tidak ditemukan'}), 500
            
            # Get user from database
            user = db.session.get(User, user_id)
            if not user:
                return jsonify({'success': False, 'message': 'User tidak ditemukan'}), 404
            
            # Check credits (Image to Video with Sora-2 costs 30 credits, same as text-to-video)
            required_credits = 30
            if user.kredit < required_credits:
                return jsonify({
                    'success': False,
                    'message': f'Kredit Anda tidak cukup untuk generate video dari gambar (minimal {required_credits} kredit)'
                }), 403
            
            # Deduct credits before starting generation
            try:
                user.kredit -= required_credits
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Gagal mengurangi kredit: {str(e)}'}), 500
            
            # Get parameters - Sora-2 image-to-video uses duration (default 4 seconds)
            duration = data.get('duration', 4)
            
            # Use Sora-2 image-to-video API endpoint
            url = "https://api.wavespeed.ai/api/v3/openai/sora-2/image-to-video"
            headers_api = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            }
            payload = {
                "duration": duration,
                "image": image_url,
                "prompt": prompt
            }
            
            print(f'[AI Generate] Sora-2 image-to-video request')
            print(f'  - Image URL: {image_url[:100]}...')
            print(f'  - Prompt: {prompt[:100]}...')
            print(f'  - Duration: {duration}s')
            
            # Request video generation
            request_id = None
            error_message = None
            begin = time.time()
            
            try:
                response = requests.post(url, headers=headers_api, json=payload, timeout=60)
                print(f'[AI Generate] Sora-2 image-to-video response: {response.status_code}')
                
                if response.status_code == 200:
                    result = response.json()
                    if "data" not in result:
                        error_message = 'Response API tidak valid: no data field'
                        raise Exception(error_message)
                    
                    result_data = result["data"]
                    if "id" not in result_data:
                        error_message = 'Response API tidak valid: no request id'
                        raise Exception(error_message)
                    
                    request_id = result_data["id"]
                    print(f'[AI Generate] Request ID: {request_id}')
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_msg = error_data['error']
                        elif 'message' in error_data:
                            error_msg = error_data['message']
                    except:
                        pass
                    error_message = f'Gagal request API: {error_msg}'
                    raise Exception(error_message)
            except requests.exceptions.Timeout:
                error_message = 'Request timeout. Coba lagi.'
                # Rollback credits on timeout
                try:
                    user.kredit += required_credits
                    db.session.commit()
                except:
                    db.session.rollback()
                return jsonify({'success': False, 'message': error_message}), 504
            except Exception as e:
                error_message = str(e) if not error_message else error_message
                print(f'[AI Generate] Error: {error_message}')
                # Rollback credits on error
                try:
                    user.kredit += required_credits
                    db.session.commit()
                except:
                    db.session.rollback()
                return jsonify({'success': False, 'message': error_message}), 500
            
            # Polling for results
            if request_id:
                poll_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
                poll_headers = {"Authorization": f"Bearer {API_KEY}"}
                
                max_attempts = 600  # 5 minutes with 0.5s interval (or 3000 with 0.1s for faster polling)
                attempt = 0
                video_url = None
                
                while attempt < max_attempts:
                    try:
                        poll_response = requests.get(poll_url, headers=poll_headers, timeout=30)
                        
                        if poll_response.status_code == 200:
                            poll_result = poll_response.json()
                            if "data" not in poll_result:
                                attempt += 1
                                time.sleep(0.5)
                                continue
                            
                            poll_data = poll_result["data"]
                            status = poll_data.get("status")
                            
                            if status == "completed":
                                outputs = poll_data.get("outputs", [])
                                if outputs and len(outputs) > 0:
                                    video_url = outputs[0] if isinstance(outputs[0], str) else outputs[0].get('url')
                                    if video_url:
                                        end = time.time()
                                        print(f'[AI Generate] Image-to-video completed in {end - begin:.2f} seconds: {video_url}')
                                        break
                                else:
                                    error_message = 'Tidak ada output video yang dihasilkan'
                                    raise Exception(error_message)
                            elif status == "failed":
                                error_msg = poll_data.get('error', 'Unknown error')
                                # Check for specific error types and provide user-friendly messages
                                error_msg_lower = error_msg.lower()
                                if 'content flagged' in error_msg_lower or 'potentially sensitive' in error_msg_lower:
                                    error_message = 'Konten dianggap tidak sesuai oleh sistem. Silakan coba dengan prompt yang berbeda atau lebih umum. Hindari konten yang mungkin dianggap sensitif.'
                                elif 'safety' in error_msg_lower or 'policy' in error_msg_lower:
                                    error_message = 'Prompt tidak memenuhi kebijakan konten. Silakan gunakan prompt yang lebih sesuai dengan pedoman konten.'
                                else:
                                    error_message = f'Task gagal: {error_msg}'
                                raise Exception(error_message)
                            elif status == "processing":
                                if attempt % 20 == 0:  # Log every 10 seconds
                                    print(f'[AI Generate] Still processing image-to-video... attempt {attempt + 1}')
                        else:
                            error_message = f'Gagal polling: HTTP {poll_response.status_code}'
                            raise Exception(error_message)
                    except Exception as e:
                        if 'error_message' not in locals() or not error_message:
                            error_message = str(e)
                        print(f'[AI Generate] Polling error: {error_message}')
                        if 'Task gagal' in error_message or 'Tidak ada output' in error_message:
                            break
                    
                    attempt += 1
                    time.sleep(0.5)  # Using 0.5s for efficiency, can be changed to 0.1s for faster polling
                
                # If failed, rollback credits and return error
                if not video_url:
                    try:
                        user.kredit += required_credits
                        db.session.commit()
                        print(f'[AI Generate] Credits rolled back due to failure')
                    except:
                        db.session.rollback()
                    
                    return jsonify({
                        'success': False,
                        'message': error_message or 'Timeout: Task took too long to complete'
                    }), 500
                
                # Success - save to database (credits already deducted)
                try:
                    video = Video(
                        user_id=user_id,
                        video_url=video_url,
                        caption=f"{prompt} (Image to Video)"
                    )
                    db.session.add(video)
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'type': 'video',
                        'url': video_url,
                        'data': {
                            'video_url': video_url,
                            'url': video_url,
                            'message': f'Video berhasil dibuat dari gambar menggunakan Sora-2 (durasi {duration}s)',
                            'duration': duration,
                            'credits_used': required_credits
                        }
                    })
                except Exception as e:
                    db.session.rollback()
                    # Even if DB save fails, return success with URL
                    return jsonify({
                        'success': True,
                        'type': 'video',
                        'url': video_url,
                        'data': {
                            'video_url': video_url,
                            'url': video_url,
                            'message': f'Video berhasil dibuat dari gambar (gagal menyimpan ke database)',
                            'duration': duration,
                            'credits_used': required_credits
                        }
                    })

        if intent == 'video_generate':
            print(f"[AI Generate] Handling video_generate intent")
            # Direct video generation using Sora-2 API
            duration = data.get('duration', 4)
            size = data.get('size', '720*1280')  # Default vertical video
            
            # Map aspect_ratio to size if provided
            aspect_ratio = data.get('aspect_ratio', '9:16')
            if aspect_ratio:
                size_map = {
                    '9:16': '720*1280',  # Vertical
                    '16:9': '1280*720',  # Horizontal
                    '1:1': '1024*1024',  # Square
                    '4:3': '1024*768',
                    '3:4': '768*1024'
                }
                size = size_map.get(aspect_ratio, '720*1280')
            
            # Check API key
            API_KEY = current_app.config.get('WAVESPEED_API_KEY')
            if not API_KEY:
                return jsonify({'success': False, 'message': 'API key tidak ditemukan'}), 500
            
            # Get user from database
            user = db.session.get(User, user_id)
            if not user:
                return jsonify({'success': False, 'message': 'User tidak ditemukan'}), 404
            
            # Check credits (Sora-2 costs more, let's use 30 credits as default)
            required_credits = 30
            if user.kredit < required_credits:
                return jsonify({
                    'success': False,
                    'message': f'Kredit Anda tidak cukup untuk generate video (minimal {required_credits} kredit)'
                }), 403
            
            # Sora-2 API endpoint
            url = "https://api.wavespeed.ai/api/v3/openai/sora-2/text-to-video"
            headers_api = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            }
            payload = {
                "duration": duration,
                "prompt": prompt,
                "size": size
            }
            
            print(f'[AI Generate] Sora-2 video request')
            print(f'  - Prompt: {prompt[:100]}...')
            print(f'  - Duration: {duration}s')
            print(f'  - Size: {size}')
            
            # Request video generation
            video_url = None
            error_message = None
            request_id = None
            begin = time.time()
            
            try:
                response = requests.post(url, headers=headers_api, json=payload, timeout=60)
                print(f'[AI Generate] Sora-2 response: {response.status_code}')
                
                if response.status_code == 200:
                    result = response.json()
                    if "data" not in result:
                        error_message = 'Response API tidak valid: no data field'
                        raise Exception(error_message)
                    
                    result_data = result["data"]
                    if "id" not in result_data:
                        error_message = 'Response API tidak valid: no request id'
                        raise Exception(error_message)
                    
                    request_id = result_data["id"]
                    print(f'[AI Generate] Request ID: {request_id}')
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_msg = error_data['error']
                        elif 'message' in error_data:
                            error_msg = error_data['message']
                    except:
                        pass
                    error_message = f'Gagal request API: {error_msg}'
                    raise Exception(error_message)
            except requests.exceptions.Timeout:
                error_message = 'Request timeout. Coba lagi.'
                return jsonify({'success': False, 'message': error_message}), 504
            except Exception as e:
                error_message = str(e) if not error_message else error_message
                print(f'[AI Generate] Error: {error_message}')
                return jsonify({'success': False, 'message': error_message}), 500
            
            # Polling for results
            if request_id:
                poll_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
                poll_headers = {"Authorization": f"Bearer {API_KEY}"}
                
                max_attempts = 600  # 5 minutes with 0.5s interval (video takes longer)
                attempt = 0
                
                while attempt < max_attempts:
                    try:
                        poll_response = requests.get(poll_url, headers=poll_headers, timeout=30)
                        
                        if poll_response.status_code == 200:
                            poll_result = poll_response.json()
                            if "data" not in poll_result:
                                attempt += 1
                                time.sleep(0.5)
                                continue
                            
                            poll_data = poll_result["data"]
                            status = poll_data.get("status")
                            
                            if status == "completed":
                                outputs = poll_data.get("outputs", [])
                                if outputs and len(outputs) > 0:
                                    video_url = outputs[0] if isinstance(outputs[0], str) else outputs[0].get('url')
                                    if video_url:
                                        end = time.time()
                                        print(f'[AI Generate] Video completed in {end - begin:.2f} seconds: {video_url}')
                                        break
                                else:
                                    error_message = 'Tidak ada output video yang dihasilkan'
                                    raise Exception(error_message)
                            elif status == "failed":
                                error_msg = poll_data.get('error', 'Unknown error')
                                # Check for specific error types and provide user-friendly messages
                                error_msg_lower = error_msg.lower()
                                if 'content flagged' in error_msg_lower or 'potentially sensitive' in error_msg_lower:
                                    error_message = 'Konten dianggap tidak sesuai oleh sistem. Silakan coba dengan prompt yang berbeda atau lebih umum. Hindari konten yang mungkin dianggap sensitif.'
                                elif 'safety' in error_msg_lower or 'policy' in error_msg_lower:
                                    error_message = 'Prompt tidak memenuhi kebijakan konten. Silakan gunakan prompt yang lebih sesuai dengan pedoman konten.'
                                else:
                                    error_message = f'Task gagal: {error_msg}'
                                raise Exception(error_message)
                            elif status == "processing":
                                if attempt % 20 == 0:  # Log every 10 seconds
                                    print(f'[AI Generate] Still processing... attempt {attempt + 1}')
                        else:
                            error_message = f'Gagal polling: HTTP {poll_response.status_code}'
                            raise Exception(error_message)
                    except Exception as e:
                        if 'error_message' not in locals() or not error_message:
                            error_message = str(e)
                        print(f'[AI Generate] Polling error: {error_message}')
                        if 'Task gagal' in error_message or 'Tidak ada output' in error_message:
                            break
                    
                    attempt += 1
                    time.sleep(0.5)
                
                # If failed, rollback credits and return error
                if not video_url:
                    try:
                        user.kredit += required_credits
                        db.session.commit()
                        print(f'[AI Generate] Credits rolled back due to failure')
                    except:
                        db.session.rollback()
                    
                    return jsonify({
                        'success': False,
                        'message': error_message or 'Timeout: Task took too long to complete'
                    }), 500
                
                # Success - deduct credits and save to database
                try:
                    user.kredit -= required_credits
                    video = Video(
                        user_id=user_id,
                        video_url=video_url,
                        caption=prompt
                    )
                    db.session.add(video)
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'type': 'video',
                        'url': video_url,
                        'data': {
                            'video_url': video_url,
                            'url': video_url,
                            'message': f'Video berhasil dibuat menggunakan Sora-2 (durasi {duration}s)',
                            'duration': duration,
                            'size': size,
                            'credits_used': required_credits
                        }
                    })
                except Exception as e:
                    db.session.rollback()
                    # Even if DB save fails, return success with URL
                    return jsonify({
                        'success': True,
                        'type': 'video',
                        'url': video_url,
                        'data': {
                            'video_url': video_url,
                            'url': video_url,
                            'message': f'Video berhasil dibuat (gagal menyimpan ke database)',
                            'duration': duration,
                            'size': size,
                            'credits_used': required_credits
                        }
                    })

        if intent == 'music_generate':
            print(f"[AI Generate] Handling music_generate intent")
            # Direct music generation using Suno API with model v5 (V4_5PLUS) - same logic as musik.py
            import glob
            import uuid
            from datetime import datetime
            from config import Config
            
            # Get API keys from config
            SUNO_API_KEY = Config.SUNO_API_KEY
            SUNO_BASE_URL = Config.SUNO_BASE_URL
            CALLBACK_DOMAIN = Config.CALLBACK_DOMAIN
            
            if not SUNO_API_KEY:
                return jsonify({'success': False, 'message': 'Suno API key tidak ditemukan'}), 500
            
            # Get user from database
            user = db.session.get(User, user_id)
            if not user:
                return jsonify({'success': False, 'message': 'User tidak ditemukan'}), 404
            
            # Check credits (15 credits for music generation)
            required_credits = 15
            if user.kredit < required_credits:
                return jsonify({
                    'success': False,
                    'message': f'Kredit Anda tidak cukup untuk generate musik (minimal {required_credits} kredit)'
                }), 403
            
            # Deduct credits before starting generation
            try:
                user.kredit -= required_credits
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Gagal mengurangi kredit: {str(e)}'}), 500
            
            # Clean up old callback files
            for f in glob.glob('suno_callback_result_*.json'):
                try:
                    os.remove(f)
                except Exception as e:
                    print(f"Gagal menghapus file lama: {f}, error: {e}")
            
            # Use model v5 (V4_5PLUS) for prompt mode
            model = 'V4_5PLUS'
            customMode = False  # Simple mode for prompt
            instrumental = False
            
            # Validate prompt length (V4_5PLUS simple mode: 3000 characters)
            prompt_limit = 3000
            if len(prompt) > prompt_limit:
                return jsonify({
                    'success': False,
                    'message': f'Prompt terlalu panjang. Maksimal {prompt_limit} karakter untuk simple mode dengan model {model}'
                }), 400
            
            # Extract title from prompt (same logic as musik.py)
            def extract_title_from_analysis(description, lyrics):
                try:
                    description_lower = description.lower()
                    words = description_lower.split()
                    skip_words = ['buat', 'create', 'generate', 'musik', 'music', 'lagu', 'song', 'yang', 'untuk', 'for', 'dengan', 'with', 'adalah', 'is', 'a', 'an', 'the']
                    meaningful_words = []
                    for word in words[:5]:
                        if word not in skip_words and len(word) > 2:
                            meaningful_words.append(word.capitalize())
                            if len(meaningful_words) >= 2:
                                break
                    if meaningful_words:
                        return " ".join(meaningful_words)
                    return "Karya Musik Baru"
                except:
                    return "Karya Musik Baru"
            
            # Clean lyrics to avoid artist name detection (same logic as musik.py)
            def clean_lyrics_for_suno(lyrics):
                if not lyrics:
                    return lyrics
                replacements = {
                    'irama': 'nada', 'rhythm': 'tempo', 'beat': 'ketukan',
                    'musik': 'suara', 'music': 'sound', 'lagu': 'nyanyian',
                    'song': 'tune', 'artis': 'pencipta', 'artist': 'creator'
                }
                cleaned = lyrics
                for word, replacement in replacements.items():
                    pattern = re.compile(re.escape(word), re.IGNORECASE)
                    cleaned = pattern.sub(replacement, cleaned)
                return cleaned
            
            title = extract_title_from_analysis(prompt, "")
            cleaned_prompt = clean_lyrics_for_suno(prompt)
            
            # Build callback URL
            callback_url = f"{CALLBACK_DOMAIN}/musik/callback"
            print(f'[AI Generate] Callback URL: {callback_url}')
            
            # Build payload for simple mode (prompt mode)
            payload = {
                "prompt": cleaned_prompt,
                "customMode": customMode,
                "instrumental": instrumental,
                "model": model,
                "callBackUrl": callback_url,
                "title": title[:100] if title else "Karya Musik Baru"
            }
            
            headers_suno = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {SUNO_API_KEY}'
            }
            
            print(f'[AI Generate] Suno music request (model: {model})')
            print(f'  - Prompt: {cleaned_prompt[:100]}...')
            print(f'  - Title: {title}')
            print(f'  - Callback URL: {callback_url}')
            
            # Request music generation
            task_id = None
            error_message = None
            try:
                response = requests.post(f"{SUNO_BASE_URL}/api/v1/generate", headers=headers_suno, json=payload, timeout=60)
                res_json = response.json()
                
                print(f'[AI Generate] Suno response: {response.status_code}')
                print(f'[AI Generate] Suno response body: {res_json}')
                
                if res_json.get("code") != 200:
                    error_msg = res_json.get("msg", "Unknown error from Suno API")
                    error_message = error_msg
                    raise Exception(error_message)
                
                task_id = res_json["data"]["taskId"]
                print(f'[AI Generate] Task ID: {task_id}')
                
                # Store task_id -> user_id mapping with timestamp for callback handling
                from datetime import datetime
                task_user_mapping[task_id] = {
                    'user_id': user_id,
                    'created_at': datetime.now()
                }
                print(f'[AI Generate] Stored task mapping: {task_id} -> user {user_id} at {datetime.now()}')
                
                # Return task_id immediately and let frontend poll for result
                # This prevents timeout issues
                return jsonify({
                    'success': True,
                    'type': 'music',
                    'status': 'processing',
                    'task_id': task_id,
                    'message': 'Musik sedang diproses. Silakan tunggu...',
                    'poll_url': f'/api/ai_generate/music-status/{task_id}'
                })
                
            except Exception as e:
                error_message = str(e) if not error_message else error_message
                print(f'[AI Generate] Error: {error_message}')
                # Rollback credits if request failed
                try:
                    user.kredit += required_credits
                    db.session.commit()
                    print(f'[AI Generate] Credits rolled back due to API error')
                except:
                    db.session.rollback()
                return jsonify({'success': False, 'message': error_message}), 500

        if intent == 'image_generate':
            print(f"[AI Generate] Handling image_generate intent")
            # Direct image generation using logic from foto.py
            from web.utils import get_width_height
            
            aspect_ratio = data.get('aspect_ratio', '1:1')
            width, height = get_width_height(aspect_ratio)
            negative_prompt = data.get('negative_prompt', '')
            model = data.get('model', 'imagen4-ultra')
            
            # Check API key
            API_KEY = current_app.config.get('WAVESPEED_API_KEY')
            if not API_KEY:
                return jsonify({'success': False, 'message': 'API key tidak ditemukan'}), 500
            
            # Get user from database
            user = db.session.get(User, user_id)
            if not user:
                return jsonify({'success': False, 'message': 'User tidak ditemukan'}), 404
            
            # Model configurations (same as foto.py)
            model_configs = {
                'imagen4-ultra': {
                    'url': "https://api.wavespeed.ai/api/v3/google/imagen4-ultra",
                    'payload': {
                        "aspect_ratio": aspect_ratio,
                        "negative_prompt": negative_prompt,
                        "num_images": 1,
                        "prompt": prompt,
                        "model_id": "wavespeed-ai/imagen4"
                    },
                    'credits': 15
                },
                'gpt-image-1': {
                    'url': "https://api.wavespeed.ai/api/v3/openai/gpt-image-1/text-to-image",
                    'payload': {
                        "enable_base64_output": False,
                        "enable_sync_mode": False,
                        "prompt": prompt,
                        "quality": "medium",
                        "size": f"{width}x{height}"
                    },
                    'credits': 12
                },
                'nano-banana': {
                    'url': "https://api.wavespeed.ai/api/v3/google/nano-banana/text-to-image",
                    'payload': {
                        "enable_base64_output": False,
                        "enable_sync_mode": False,
                        "output_format": "png",
                        "prompt": prompt
                    },
                    'credits': 10
                }
            }
            
            # Validate model
            if model not in model_configs:
                return jsonify({'success': False, 'message': f'Model tidak valid: {model}'}), 400
            
            # Check credits
            required_credits = model_configs[model]['credits']
            if user.kredit < required_credits:
                return jsonify({
                    'success': False,
                    'message': f'Kredit Anda tidak cukup untuk generate gambar dengan model {model} (minimal {required_credits} kredit)'
                }), 403
            
            # Get model configuration
            model_config = model_configs[model]
            url = model_config['url']
            payload = model_config['payload']
            
            headers_api = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            }
            
            # Request image generation
            image_url = None
            error_message = None
            try:
                response = requests.post(url, headers=headers_api, json=payload, timeout=30)
                print('WAVESPEED API RESPONSE:', response.text)
                if response.status_code != 200:
                    error_message = f'Gagal request API: {response.text}'
                    raise Exception(error_message)
                result = response.json()
                if 'data' not in result or 'id' not in result['data']:
                    error_message = 'Response API tidak valid'
                    raise Exception(error_message)
                request_id = result['data']['id']
            except Exception as e:
                print('ERROR saat request API:', str(e))
                error_message = str(e)
                request_id = None
            
            # Polling status
            if request_id:
                result_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
                headers_result = {"Authorization": f"Bearer {API_KEY}"}
                for _ in range(20):
                    try:
                        resp = requests.get(result_url, headers=headers_result, timeout=10)
                        print('WAVESPEED POLL RESPONSE:', resp.text)
                        if resp.status_code == 200:
                            res = resp.json()
                            if 'data' not in res:
                                error_message = 'Response polling tidak valid'
                                raise Exception(error_message)
                            data_poll = res['data']
                            status = data_poll.get("status", "unknown")
                            outputs = data_poll.get("outputs", None)
                            if status == "completed":
                                if outputs and isinstance(outputs, list) and len(outputs) > 0:
                                    image_url = outputs[0] if isinstance(outputs[0], str) else outputs[0].get('url')
                                    if image_url:
                                        break
                                else:
                                    error_message = 'Tidak ada output gambar yang dihasilkan'
                                    raise Exception(error_message)
                            elif status == "failed":
                                error_msg = data_poll.get('error', 'Unknown error')
                                error_message = f'Task gagal: {error_msg}'
                                raise Exception(error_message)
                    except Exception as e:
                        print('ERROR saat polling:', str(e))
                        error_message = str(e)
                    time.sleep(0.5)
            
            # If failed, return error
            if not image_url:
                return jsonify({
                    'success': False,
                    'message': f'Gagal generate gambar: {error_message}',
                    'error': error_message
                }), 500
            
            # Save to database and deduct credits
            try:
                user.kredit -= required_credits
                image = Image(user_id=user_id, image_url=image_url, caption=prompt)
                db.session.add(image)
                db.session.commit()
                return jsonify({
                    'success': True,
                    'type': 'image',
                    'data': {
                        'photo_url': image_url,
                        'message': f'Foto berhasil dibuat dengan model {model}',
                        'model_used': model,
                        'credits_used': required_credits
                    }
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Gagal menyimpan ke database: {str(e)}'}), 500

        return jsonify({'success': False, 'message': 'Intent tidak dikenali'}), 400
    except requests.exceptions.Timeout:
        import traceback
        print(f"[AI Generate] Timeout error:")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': 'Permintaan timeout. Coba lagi.'}), 504
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[AI Generate] Unexpected error:")
        print(error_trace)
        print(f"[AI Generate] Error type: {type(e).__name__}")
        print(f"[AI Generate] Error message: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Kesalahan: {str(e)}',
            'error_type': type(e).__name__,
            'error_details': str(e)
        }), 500


@ai_generate_bp.route('/api/ai_generate/music-status/<task_id>', methods=['GET'])
def get_music_status(task_id):
    """Check status of music generation task (polling endpoint)"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    print(f'[AI Generate] Checking music status for task_id: {task_id}')
    
    # Check in current working directory (where Flask app is running)
    import os
    current_dir = os.getcwd()
    print(f'[AI Generate] Current working directory: {current_dir}')
    
    # Check in multiple locations
    callback_file = f'suno_callback_result_{task_id}.json'
    callback_file_cwd = os.path.join(current_dir, callback_file)
    callback_file_backend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), callback_file)
    callback_file_script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), callback_file)
    
    # Check multiple locations for callback file
    import glob
    callback_files = []
    
    # Check all possible locations
    locations_to_check = [
        callback_file,  # Current directory
        callback_file_cwd,  # Current working directory
        callback_file_backend,  # Backend directory
        callback_file_script_dir,  # Script directory
    ]
    
    # Also do recursive search
    try:
        callback_files.extend(glob.glob(f'**/suno_callback_result_{task_id}.json', recursive=True))
        callback_files.extend(glob.glob(f'../suno_callback_result_{task_id}.json', recursive=False))
        callback_files.extend(glob.glob(f'../../suno_callback_result_{task_id}.json', recursive=False))
    except:
        pass
    
    callback_file_path = None
    for loc in locations_to_check:
        if loc and os.path.exists(loc):
            callback_file_path = loc
            print(f'[AI Generate] ✅ Found callback file: {os.path.abspath(callback_file_path)}')
            break
    
    if not callback_file_path and callback_files:
        callback_file_path = callback_files[0]
        print(f'[AI Generate] ✅ Found callback file in alternative location: {callback_file_path}')
    
    if not callback_file_path:
        print(f'[AI Generate] Callback file not found: {callback_file}')
        print(f'[AI Generate] Searched locations: {locations_to_check}')
        print(f'[AI Generate] Found files from glob: {callback_files}')
        
        # Database check - check music created since task was initiated
        try:
            from datetime import datetime, timedelta
            
            # Check if this task_id is in our mapping (means it's a valid request from this session)
            task_info = task_user_mapping.get(task_id)
            is_valid_task = task_info is not None
            task_created_at = task_info.get('created_at') if task_info else None
            
            print(f'[AI Generate] Task {task_id} in mapping: {is_valid_task}')
            if task_created_at:
                print(f'[AI Generate] Task created at: {task_created_at}')
            
            # Check music created AFTER task was created (or within last 30 minutes if no timestamp)
            if task_created_at:
                # Only check music created after this task was initiated
                music_cutoff = task_created_at
                print(f'[AI Generate] Checking music created after: {music_cutoff}')
            else:
                # Fallback: check last 30 minutes
                music_cutoff = datetime.now() - timedelta(minutes=30)
                print(f'[AI Generate] No task timestamp, checking last 30 minutes')
            
            # Query for music created after task initiation
            recent_music_list = Song.query.filter(
                Song.user_id == user_id,
                Song.mode == 'prompt',
                Song.created_at >= music_cutoff,
                Song.audio_url.isnot(None),
                Song.audio_url != ''
            ).order_by(Song.created_at.desc()).limit(5).all()
            
            print(f'[AI Generate] Found {len(recent_music_list)} music created after task initiation for user {user_id}')
            
            # Debug: Log all found music
            if recent_music_list:
                for m in recent_music_list:
                    time_since = (datetime.now() - m.created_at).total_seconds() / 60
                    print(f'  - Music: {m.id} - {m.title} (created {time_since:.1f} min ago)')
            
            # If we have valid task and recent music, return the most recent one
            if is_valid_task and recent_music_list:
                latest_music = recent_music_list[0]
                time_diff = (datetime.now() - latest_music.created_at).total_seconds() / 60
                print(f'[AI Generate] ✅ Latest music: {latest_music.id} - {latest_music.title} (created {time_diff:.1f} min ago)')
                
                # Return the music (it was created after task initiation)
                print(f'[AI Generate] ✅ Returning music from database: {latest_music.id} - {latest_music.title}')
                # Remove from mapping after returning
                task_user_mapping.pop(task_id, None)
                return jsonify({
                    'success': True,
                    'status': 'completed',
                    'type': 'music',
                    'url': latest_music.audio_url,
                    'task_id': task_id,
                    'data': {
                        'audio_url': latest_music.audio_url,
                        'url': latest_music.audio_url,
                        'image_url': latest_music.image_url or '',
                        'cover_url': latest_music.image_url or '',
                        'title': latest_music.title or 'Untitled',
                        'duration': latest_music.duration or 0,
                        'model_name': latest_music.model_name or 'V4_5PLUS',
                        'message': f'Musik berhasil dibuat menggunakan Suno {latest_music.model_name or "V4_5PLUS"}',
                        'music_id': str(latest_music.id)
                    }
                })
            elif recent_music_list and not is_valid_task:
                print(f'[AI Generate] ⏳ Found music but task_id not in mapping (server restart?), checking if music is very recent...')
                # Even if not in mapping, if music is very recent (< 5 minutes), return it
                latest_music = recent_music_list[0]
                time_diff = (datetime.now() - latest_music.created_at).total_seconds() / 60
                if time_diff <= 5:
                    print(f'[AI Generate] ✅ Music is very recent ({time_diff:.1f} min), returning it')
                    return jsonify({
                        'success': True,
                        'status': 'completed',
                        'type': 'music',
                        'url': latest_music.audio_url,
                        'task_id': task_id,
                        'data': {
                            'audio_url': latest_music.audio_url,
                            'url': latest_music.audio_url,
                            'image_url': latest_music.image_url or '',
                            'cover_url': latest_music.image_url or '',
                            'title': latest_music.title or 'Untitled',
                            'duration': latest_music.duration or 0,
                            'model_name': latest_music.model_name or 'V4_5PLUS',
                            'message': f'Musik berhasil dibuat menggunakan Suno {latest_music.model_name or "V4_5PLUS"}',
                            'music_id': str(latest_music.id)
                        }
                    })
            else:
                print(f'[AI Generate] ⏳ No recent music found, continuing to wait for callback...')
        except Exception as e:
            import traceback
            print(f'[AI Generate] ⚠️ Error checking database: {e}')
            print(traceback.format_exc())
        
        return jsonify({
            'status': 'processing',
            'message': 'Musik sedang diproses...',
            'task_id': task_id
        }), 200
    
    # Use the file that exists (already set above)
    if not callback_file_path:
        # Try one more time with the first location
        for loc in locations_to_check:
            if loc and os.path.exists(loc):
                callback_file_path = loc
                break
    
    if callback_file_path:
        print(f'[AI Generate] ✅ Using callback file: {os.path.abspath(callback_file_path)}')
    else:
        print(f'[AI Generate] ❌ Callback file not found after all searches')
    
    try:
        with open(callback_file_path, 'r', encoding='utf-8') as f:
            callback_data = json.load(f)
        
        # Validate callback data
        if not callback_data or not isinstance(callback_data, dict) or 'data' not in callback_data:
            try:
                os.remove(callback_file_path)
            except:
                pass
            return jsonify({
                'status': 'processing',
                'message': 'Data callback tidak valid, melanjutkan proses...',
                'task_id': task_id
            }), 200
        
        cb_data = callback_data.get('data', {})
        cb_task_id = cb_data.get('task_id')
        
        if not cb_task_id or cb_task_id != task_id:
            return jsonify({
                'status': 'processing',
                'message': 'Menunggu hasil...',
                'task_id': task_id
            }), 200
        
        if not isinstance(cb_data.get('data', []), list):
            return jsonify({
                'status': 'processing',
                'message': 'Data belum lengkap...',
                'task_id': task_id
            }), 200
        
        songs_data = cb_data.get('data', [])
        if not songs_data:
            return jsonify({
                'status': 'processing',
                'message': 'Menunggu hasil...',
                'task_id': task_id
            }), 200
        
        # Process the first song result
        song_data = songs_data[0]
        audio_url = song_data.get('audio_url', '')
        title_result = song_data.get('title', 'Untitled')
        duration = song_data.get('duration', 0)
        model_name = song_data.get('model_name', 'V4_5PLUS')
        image_url = song_data.get('image_url', '')
        
        if not audio_url:
            return jsonify({
                'status': 'processing',
                'message': 'Menunggu audio URL...',
                'task_id': task_id
            }), 200
        
        # Save to database
        try:
            from datetime import datetime
            # Get original prompt from callback data if available
            original_prompt = ''
            if cb_data:
                # Try to get prompt from songs_data
                if songs_data and len(songs_data) > 0:
                    original_prompt = songs_data[0].get('prompt', '') or cb_data.get('prompt', '')
            
            # Generate UUID for ID (database uses char(36) for ID, not auto-increment)
            import uuid
            music_id = str(uuid.uuid4())
            
            music = Song(
                id=music_id,
                user_id=user_id,
                title=title_result,
                lyrics="",  # No lyrics for prompt mode
                genre='AI Generated',
                mode='prompt',
                prompt=original_prompt or title_result,  # Use prompt from callback or title as fallback
                audio_url=audio_url,
                image_url=image_url,
                duration=duration,
                model_name=model_name,
                created_at=datetime.now()
            )
            db.session.add(music)
            db.session.commit()
            
            # Remove from task mapping after successful save
            task_user_mapping.pop(task_id, None)
            print(f'[AI Generate] ✅ Music saved to database: {music.id} - {music.title}')
            
            # Clean up callback file
            try:
                os.remove(callback_file_path)
            except:
                pass
            
            return jsonify({
                'success': True,
                'status': 'completed',
                'type': 'music',
                'url': audio_url,
                'task_id': task_id,
                'data': {
                    'audio_url': audio_url,
                    'url': audio_url,
                    'image_url': image_url,
                    'cover_url': image_url,
                    'title': title_result,
                    'duration': duration,
                    'model_name': model_name,
                    'message': f'Musik berhasil dibuat menggunakan Suno {model_name}',
                    'music_id': str(music.id)
                }
            })
        except Exception as e:
            db.session.rollback()
            print(f'[AI Generate] DB error in status check: {e}')
            # Even if DB save fails, return success with URL
            try:
                os.remove(callback_file_path)
            except:
                pass
            return jsonify({
                'success': True,
                'status': 'completed',
                'type': 'music',
                'url': audio_url,
                'task_id': task_id,
                'data': {
                    'audio_url': audio_url,
                    'url': audio_url,
                    'image_url': image_url,
                    'cover_url': image_url,
                    'title': title_result,
                    'duration': duration,
                    'model_name': model_name,
                    'message': f'Musik berhasil dibuat (gagal menyimpan ke database)'
                }
            })
        
    except Exception as e:
        print(f'[AI Generate] Error reading callback file: {e}')
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'status': 'processing',
            'message': 'Error membaca callback, melanjutkan proses...',
            'task_id': task_id,
            'error': str(e)
        }), 200


