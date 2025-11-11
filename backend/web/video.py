from flask import Blueprint, render_template, request, jsonify, send_from_directory, session, current_app
import os, uuid, requests, time
from .utils import get_width_height
from models import db, Video
import json
import base64

video_bp = Blueprint('video', __name__)

def parse_veo_error(error_msg):
    """
    Parse error message dari Google Veo API dan ubah menjadi pesan yang user-friendly
    """
    error_msg_lower = error_msg.lower()
    
    # Cek untuk Responsible AI practices violation
    if "responsible ai practices" in error_msg_lower or "violates google" in error_msg_lower:
        return ("Gambar yang Anda upload tidak memenuhi standar keamanan AI Google. "
                "Silakan coba dengan gambar lain yang tidak mengandung konten sensitif, "
                "kekerasan, atau konten yang tidak pantas.")
    
    # Cek untuk error kredensial atau API
    elif "api key" in error_msg_lower or "authentication" in error_msg_lower:
        return "Terjadi kesalahan autentikasi dengan layanan AI. Silakan coba lagi nanti."
    
    # Cek untuk error rate limit
    elif "rate limit" in error_msg_lower or "quota" in error_msg_lower:
        return "Layanan sedang sibuk. Silakan coba lagi dalam beberapa menit."
    
    # Cek untuk error format gambar
    elif "image" in error_msg_lower and ("format" in error_msg_lower or "invalid" in error_msg_lower):
        return "Format gambar tidak didukung atau gambar rusak. Silakan coba dengan gambar lain."
    
    # Cek untuk error ukuran gambar
    elif "size" in error_msg_lower and ("too large" in error_msg_lower or "exceed" in error_msg_lower):
        return "Ukuran gambar terlalu besar. Silakan gunakan gambar dengan ukuran lebih kecil."
    
    # Cek untuk error umum
    elif "internal" in error_msg_lower or "server" in error_msg_lower:
        return "Terjadi kesalahan pada server AI. Silakan coba lagi nanti."
    
    # Default error message
    else:
        return f"Gagal generate video: {error_msg}"

@video_bp.route('/video')
def video_page():
    return render_template('generate_video.html')

@video_bp.route('/generate', methods=['POST'])
def generate_video():
    user_id = session.get('user_id')
    if not user_id:
        response = jsonify({'error': 'User belum login', 'redirect': '/login'})
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, 401
    from models import User
    user = User.query.get(user_id)
    if not user:
        response = jsonify({'error': 'User tidak ditemukan'})
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, 404
    
    data = request.json
    # Tentukan kredit berdasarkan model
    model = data.get('model', 'veo3')
    if model == 'wavespeed-dreamina':
        required_credit = 100
    else:  # veo3
        required_credit = 300
    
    if user.kredit < required_credit:
        response = jsonify({'error': f'Kredit Anda tidak cukup untuk generate video dengan model {model} (minimal {required_credit} kredit)'})
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, 403
    user.kredit -= required_credit
    db.session.commit()
    prompt = data.get('prompt')
    duration = int(data.get('duration', 8))
    aspect_ratio = data.get('aspect_ratio', '16:9')
    width, height = get_width_height(aspect_ratio)
    negative_prompt = data.get('negative_prompt', '')
    generate_audio = bool(data.get('generate_audio', False))
    image_url = data.get('image', '')  # Tambahan untuk image-to-video
    resolution = data.get('resolution', '720p')  # Tambahan untuk resolusi
    seed = data.get('seed', -1)  # Tambahan untuk seed
    
    # Validasi prompt
    if not prompt or not prompt.strip():
        response = jsonify({'error': 'Prompt tidak boleh kosong. Silakan masukkan deskripsi video yang ingin dibuat.'})
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, 400
    
    API_KEY = current_app.config.get('WAVESPEED_API_KEY')
    if not API_KEY:
        response = jsonify({'error': 'API key tidak ditemukan'})
        response.headers['Content-Type'] = 'application/json'
        return response, 500
    
    # Tentukan endpoint berdasarkan model dan ada tidaknya image
    if model == 'wavespeed-dreamina':
        # WaveSpeed Dreamina v3.0 model - hanya support text-to-video
        url = "https://api.wavespeed.ai/api/v3/bytedance/dreamina-v3.0/text-to-video-1080p"
        payload = {
            "seed": int(seed),  # Seed dari frontend
            "prompt": prompt,
            "duration": 5,  # WaveSpeed Dreamina hanya support 5 detik
            "aspect_ratio": aspect_ratio
        }
    else:
        # Veo 3 model (default)
        if image_url and image_url.strip():
            # Image-to-video mode
            url = "htt://api.wavespeed.ai/api/v3/google/veo3-fast/image-to-video"
            payload = {
                "aspect_ratio": aspect_ratio,
                "duration": duration,
                "generate_audio": generate_audio,
                "image": image_url,
                "prompt": prompt,
                "resolution": resolution
            }
        else:
            # Text-to-video mode
            url = "htt://api.wavespeed.ai/api/v3/google/veo3-fast"
            payload = {
                "aspect_ratio": aspect_ratio,
                "duration": duration,
                "enable_prompt_expansion": True,
                "generate_audio": generate_audio,
                "prompt": prompt,
                "negative_prompt": negative_prompt
            }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    
    # Retry mechanism for initial request
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"Making request to: {url} (attempt {attempt + 1}/{max_retries})")
            print(f"Payload: {payload}")
            # Add timeout untuk initial request - increased to 60 seconds for better reliability
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text[:500]}...")  # Log first 500 chars
            
            if response.status_code != 200:
                error_response = jsonify({'error': f'Gagal request API: {response.text}'})
                error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
                return error_response, 500
            
            # Success - break out of retry loop
            break
            
        except requests.exceptions.Timeout as e:
            print(f"Timeout in API request attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Exponential backoff
                continue
            else:
                error_response = jsonify({'error': 'Server API tidak merespons setelah beberapa percobaan. Silakan coba lagi dalam 5-10 menit.'})
                error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
                return error_response, 500
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error in API request attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Exponential backoff
                continue
            else:
                error_response = jsonify({'error': 'Tidak dapat terhubung ke server API setelah beberapa percobaan. Silakan periksa koneksi internet dan coba lagi.'})
                error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
                return error_response, 500
    
    # Parse response after successful request (outside the retry loop)
    try:
        result = response.json()["data"]
        request_id = result["id"]
        print(f"Request ID: {request_id}")
    except (KeyError, ValueError, json.JSONDecodeError) as parse_error:
        print(f"Error parsing API response: {parse_error}")
        print(f"Response content: {response.text}")
        error_response = jsonify({'error': 'Response dari API tidak valid'})
        error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return error_response, 500
    except Exception as e:
        print(f"Exception in API request: {str(e)}")
        error_response = jsonify({'error': f'Gagal request API: {str(e)}'})
        error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return error_response, 500

    # Polling status
    result_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
    headers_result = {"Authorization": f"Bearer {API_KEY}"}
    print(f"Starting polling for request ID: {request_id}")
    
    for i in range(120):
        try:
            # Add timeout untuk polling request
            resp = requests.get(result_url, headers=headers_result, timeout=30)
            print(f"Polling attempt {i+1}: Status {resp.status_code}")
            
            if resp.status_code == 200:
                try:
                    res = resp.json()["data"]
                    status = res["status"]
                    print(f"Current status: {status}")
                    
                    if status == "completed":
                        video_url = res["outputs"][0]
                        print(f"Video completed! URL: {video_url}")
                        break
                    elif status == "failed":
                        error_msg = res.get("error", "Unknown error")
                        print(f"Task failed: {error_msg}")
                        
                        # Parse error message untuk memberikan pesan yang lebih user-friendly
                        user_friendly_error = parse_veo_error(error_msg)
                        
                        error_response = jsonify({'error': user_friendly_error})
                        error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
                        return error_response, 500
                except (KeyError, ValueError, json.JSONDecodeError) as parse_error:
                    print(f"Error parsing polling response: {parse_error}")
                    print(f"Polling response content: {resp.text}")
                    error_response = jsonify({'error': 'Response polling tidak valid'})
                    error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
                    return error_response, 500
            else:
                print(f"Polling failed with status {resp.status_code}: {resp.text}")
                error_response = jsonify({'error': f'Gagal polling: {resp.text}'})
                error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
                return error_response, 500
        except requests.exceptions.Timeout as e:
            print(f"Timeout during polling attempt {i+1}: {str(e)}")
            if i >= 5:  # Jika sudah timeout 5 kali berturut-turut, return error
                error_response = jsonify({'error': 'Server API tidak merespons. Silakan coba lagi dalam beberapa menit.'})
                error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
                return error_response, 500
            # Exponential backoff untuk timeout
            time.sleep(min(2 ** (i // 10), 10))  # Max 10 seconds
            continue
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error during polling attempt {i+1}: {str(e)}")
            if i >= 3:  # Jika sudah connection error 3 kali berturut-turut, return error
                error_response = jsonify({'error': 'Tidak dapat terhubung ke server API. Silakan periksa koneksi internet dan coba lagi.'})
                error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
                return error_response, 500
            # Exponential backoff untuk connection error
            time.sleep(min(2 ** (i // 5), 5))  # Max 5 seconds
            continue
        except Exception as e:
            print(f"Exception during polling: {str(e)}")
            error_response = jsonify({'error': f'Gagal polling: {str(e)}'})
            error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return error_response, 500
            
        time.sleep(1)
    else:
        print("Polling timeout after 120 attempts")
        error_response = jsonify({'error': 'Timeout menunggu hasil generate video (2 menit). Server API sedang overload, silakan coba lagi dalam 5-10 menit.'})
        error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return error_response, 500

    # Simpan ke database (hanya link, tidak download)
    video = Video(user_id=user_id, video_url=video_url, caption=prompt, generation_type='generate_video')
    db.session.add(video)
    db.session.commit()

    try:
        response_data = {"video_url": video_url, "message": "Video berhasil dibuat, disimpan (link), dan dicatat di database"}
        print(f"Sending response: {response_data}")
        
        # Validasi data sebelum dikirim
        if not video_url or not isinstance(video_url, str):
            raise ValueError("Video URL tidak valid")
        
        # Gunakan pendekatan yang lebih sederhana
        from flask import make_response
        response = make_response(json.dumps(response_data, ensure_ascii=False))
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        
        print(f"Response content: {response.get_data(as_text=True)}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response status: {response.status_code}")
        
        return response
    except Exception as e:
        print(f"Error creating response: {str(e)}")
        error_response = make_response(json.dumps({'error': f'Gagal membuat response: {str(e)}'}, ensure_ascii=False))
        error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return error_response, 500

@video_bp.route('/upload_image_to_video', methods=['POST'])
def upload_image_to_video():
    user_id = session.get('user_id')
    if not user_id:
        response = jsonify({'error': 'User belum login'})
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, 401
    
    if 'file' not in request.files:
        response = jsonify({'error': 'Tidak ada file yang diupload'})
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, 400
    
    file = request.files['file']
    if file.filename == '':
        response = jsonify({'error': 'Tidak ada file yang dipilih'})
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, 400
    
    if file:
        import base64
        import uuid
        from werkzeug.utils import secure_filename
        # Validasi ekstensi file
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in allowed_extensions:
            response = jsonify({'error': 'Tipe file tidak didukung. Gunakan PNG, JPG, JPEG, GIF, atau WEBP'})
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response, 400
        # Validasi MIME type
        allowed_mimes = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
        mime_type = file.content_type or 'image/jpeg'
        if mime_type not in allowed_mimes:
            response = jsonify({'error': 'Tipe MIME file tidak valid'})
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response, 400
        # Batasi ukuran file (misal 5MB)
        file.seek(0, 2)  # move to end
        file_length = file.tell()
        file.seek(0)
        if file_length > 5 * 1024 * 1024:
            response = jsonify({'error': 'Ukuran file terlalu besar (maksimal 5MB)'})
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response, 400
        # Gunakan nama file acak (tidak disimpan ke disk, hanya base64)
        file_content = file.read()
        file_base64 = base64.b64encode(file_content).decode('utf-8')
        data_url = f"data:{mime_type};base64,{file_base64}"
        response = jsonify({'url': data_url, 'message': 'Gambar berhasil diupload'})
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response
    response = jsonify({'error': 'Gagal upload file'})
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response, 500

@video_bp.route('/video_results/<filename>')
def serve_video_result(filename):
    return send_from_directory('video_results', filename)

@video_bp.route('/video/<filename>')
def serve_video(filename):
    return send_from_directory('.', filename)

@video_bp.route('/output.png')
def serve_output_png():
    return send_from_directory('.', 'output.png') 