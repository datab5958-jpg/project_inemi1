from flask import Blueprint, request, jsonify, current_app, session, url_for
import requests
import time
from models import db, Video, Image, User
import uuid
import os

image_video_bp = Blueprint('image_video', __name__)

def sanitize_text(text):
    import re
    return re.sub(r'<[^>]+>', '', text) if text else text

@image_video_bp.route('/api/generate_image_video', methods=['POST'])
def generate_image_video():
    try:
        # Validate request data
        if not request.json:
            return jsonify({'success': False, 'error': 'Request data tidak valid'}), 400
            
        data = request.json
        prompt = sanitize_text(data.get('prompt'))
        image_url = data.get('image')
        try:
            duration = int(data.get('duration', 5))  # Convert to int
            seed = int(data.get('seed', -1))  # Convert to int
        except (ValueError, TypeError) as e:
            print(f"Error converting duration/seed to int: {e}")
            return jsonify({'success': False, 'error': 'Duration dan seed harus berupa angka'}), 400
        
        print(f"Image to Video request: prompt='{prompt}', image_url='{image_url}', duration={duration}, seed={seed}")
        
        if not image_url:
            return jsonify({'success': False, 'error': 'Image URL kosong, upload gambar dulu!'}), 400
        
        # Validate image URL
        if not image_url.startswith(('http://', 'https://')):
            return jsonify({'success': False, 'error': 'Image URL tidak valid. Pastikan URL dimulai dengan http:// atau https://'}), 400
        
        # Test if image URL is accessible (with better error handling)
        try:
            test_response = requests.head(image_url, timeout=10, allow_redirects=True)
            if test_response.status_code not in [200, 301, 302]:
                print(f"Image URL validation failed: {test_response.status_code}")
                return jsonify({'success': False, 'error': 'Image URL tidak dapat diakses. Pastikan URL gambar valid dan dapat diakses.'}), 400
        except Exception as e:
            print(f"Image URL validation error: {e}")
            return jsonify({'success': False, 'error': 'Image URL tidak dapat diakses. Pastikan URL gambar valid dan dapat diakses.'}), 400

        api_key = current_app.config.get("WAVESPEED_API_KEY")
        if not api_key:
            return jsonify({'success': False, 'error': 'API key not configured'}), 500

        # Use working image-to-video models
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        
        # Try the most reliable model first
        submit_url = "https://api.wavespeed.ai/api/v3/bytedance/seedance-v1-pro-i2v-720p"
        payload = {
            "duration": duration,
            "image": image_url,
            "prompt": prompt,
            "seed": seed
        }
        
        print(f"Using image-to-video model: {submit_url}")
        print(f"Payload: {payload}")

        # Submit job with working models (based on test results)
        models_to_try = [
        {
            "url": "https://api.wavespeed.ai/api/v3/bytedance/seedance-v1-pro-i2v-720p",
            "payload": {
                "duration": duration,
                "image": image_url,  # Correct parameter name
                "prompt": prompt,
                "seed": seed
            }
        },
        {
            "url": "https://api.wavespeed.ai/api/v3/google/veo3/image-to-video",
            "payload": {
                "duration": 8 if duration > 8 else (4 if duration < 4 else duration),  # Fix duration
                "image": image_url,
                "prompt": prompt,
                "seed": seed,
                "aspect_ratio": "16:9"
            }
        }
        ]
        
        request_id = None
        for i, model in enumerate(models_to_try):
            try:
                print(f"Trying model {i+1}: {model['url']}")
                response = requests.post(model["url"], headers=headers, json=model["payload"], timeout=30)
                print(f"Model {i+1} Response: {response.status_code} - {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    if "data" in result and "id" in result["data"]:
                        request_id = result["data"]["id"]
                        submit_url = model["url"]
                        payload = model["payload"]
                        print(f"[SUCCESS] Model {i+1}: {request_id}")
                        break
                    else:
                        print(f"[ERROR] Model {i+1}: Invalid response structure")
                else:
                    print(f"[ERROR] Model {i+1}: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"[ERROR] Model {i+1} error: {str(e)}")
                continue
    
        if not request_id:
            return jsonify({'success': False, 'error': 'All image-to-video models failed. Please try again later.'}), 500

        # Polling for result
        poll_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
        poll_headers = {"Authorization": f"Bearer {api_key}"}

        start_time = time.time()
        video_url = None
        max_wait_time = 300  # 5 minutes max wait
        poll_interval = 2  # Poll every 2 seconds
        
        while time.time() - start_time < max_wait_time:
            try:
                poll_response = requests.get(poll_url, headers=poll_headers, timeout=10)
                print(f"Polling response: {poll_response.status_code}")
                
                if poll_response.status_code == 200:
                    poll_result = poll_response.json()
                    if "data" not in poll_result:
                        return jsonify({'success': False, 'error': 'Invalid polling response'}), 500
                        
                    data = poll_result["data"]
                    status = data.get("status", "unknown")
                    print(f"Polling status: {status}")

                    if status == "completed":
                        outputs = data.get("outputs", [])
                        if outputs and len(outputs) > 0:
                            video_url = outputs[0]
                            # Validate that it's a real video URL, not a placeholder
                            if "w3schools.com" in video_url or "placeholder" in video_url.lower():
                                print(f"[ERROR] Received placeholder video URL: {video_url}")
                                return jsonify({'success': False, 'error': 'Received placeholder video instead of generated content'}), 500
                            
                            elapsed = time.time() - start_time
                            print(f"[SUCCESS] Video completed in {elapsed:.2f} seconds: {video_url}")
                            break
                        else:
                            return jsonify({'success': False, 'error': 'No video output generated'}), 500
                    elif status == "failed":
                        error_msg = data.get('error', 'Task failed')
                        print(f"Task failed: {error_msg}")
                        return jsonify({'success': False, 'error': f'Generation failed: {error_msg}'}), 500
                    # else: masih processing, lanjut polling
                else:
                    print(f"Polling failed: {poll_response.status_code} - {poll_response.text}")
                    return jsonify({'success': False, 'error': f'Polling failed: {poll_response.text}'}), 500
                    
            except requests.exceptions.Timeout:
                print("Polling timeout, retrying...")
            except requests.exceptions.RequestException as e:
                print(f"Polling error: {e}")
                return jsonify({'success': False, 'error': f'Polling error: {str(e)}'}), 500
            except Exception as e:
                print(f"Unexpected polling error: {e}")
                return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500
                
            time.sleep(poll_interval)
        
        if not video_url:
            return jsonify({'success': False, 'error': 'Video generation timeout after 5 minutes'}), 500

        # Simpan ke database
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User belum login', 'redirect': '/login'}), 401
        
        # Cek kredit user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User tidak ditemukan'}), 404
        
        if user.kredit < 15:
            return jsonify({'success': False, 'error': 'Kredit Anda tidak cukup untuk generate video (minimal 15 kredit)'}), 403
        
        # Kurangi kredit
        user.kredit -= 15
        db.session.commit()
        
        video = Video(user_id=user_id, video_url=video_url, caption=prompt)
        db.session.add(video)
        db.session.commit()

        return jsonify({'success': True, 'video_url': video_url, 'elapsed': elapsed})
    
    except Exception as e:
        print(f"Unexpected error in generate_image_video: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Terjadi kesalahan server: {str(e)}'}), 500

@image_video_bp.route('/upload_image_to_video', methods=['POST'])
def upload_image_to_video():
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login', 'redirect': '/login'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if file:
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"image_{uuid.uuid4().hex}.{ext}"
        save_dir = os.path.join('static', 'uploads')
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        file.save(filepath)
        # Ambil domain publik dari config Flask
        DOMAIN_PUBLIC = current_app.config.get('DOMAIN_PUBLIC', 'http://127.0.0.1:5000')
        url = f"{DOMAIN_PUBLIC}/static/uploads/{filename}"
        return jsonify({'url': url})
    return jsonify({'error': 'Upload gagal'}), 500

@image_video_bp.route('/api/gallery_images', methods=['GET'])
def gallery_images():
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login', 'redirect': '/login'}), 401
    
    images = Image.query.order_by(Image.created_at.desc()).limit(50).all()
    data = [
        {
            'id': img.id,
            'url': img.image_url,
            'caption': img.caption or ''
        } for img in images
    ]
    return jsonify({'success': True, 'images': data})

@image_video_bp.route('/api/gallery_generated_images', methods=['GET'])
def gallery_generated_images():
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login', 'redirect': '/login'}), 401
    
    # Asumsi: Video punya kolom image_url/thumbnail, jika tidak, ambil video_url saja
    videos = Video.query.order_by(Video.created_at.desc()).limit(50).all()
    data = [
        {
            'id': vid.id,
            'url': getattr(vid, 'image_url', None) or '',
            'caption': vid.caption or ''
        } for vid in videos if getattr(vid, 'image_url', None)
    ]
    return jsonify({'success': True, 'images': data}) 