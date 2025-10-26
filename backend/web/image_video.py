from flask import Blueprint, request, jsonify, current_app, session, url_for
import requests
import time
from models import db, Video, Image
import uuid
import os

image_video_bp = Blueprint('image_video', __name__)

def sanitize_text(text):
    import re
    return re.sub(r'<[^>]+>', '', text) if text else text

@image_video_bp.route('/api/generate_image_video', methods=['POST'])
def generate_image_video():
    data = request.json
    prompt = sanitize_text(data.get('prompt'))
    image_url = data.get('image')
    duration = data.get('duration', 5)
    seed = data.get('seed', -1)
    if not image_url:
        return jsonify({'success': False, 'error': 'Image URL kosong, upload gambar dulu!'}), 400

    api_key = current_app.config.get("WAVESPEED_API_KEY")
    if not api_key:
        return jsonify({'success': False, 'error': 'API key not configured'}), 500

    submit_url = "https://api.wavespeed.ai/api/v3/bytedance/seedance-v1-pro-i2v-720p"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "duration": duration,
        "image": image_url,
        "prompt": prompt,
        "seed": seed
    }

    # Submit job
    response = requests.post(submit_url, headers=headers, json=payload)
    if response.status_code != 200:
        return jsonify({'success': False, 'error': response.text}), 500

    result = response.json()["data"]
    request_id = result["id"]

    # Polling for result
    poll_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
    poll_headers = {"Authorization": f"Bearer {api_key}"}

    start_time = time.time()
    video_url = None
    while True:
        poll_response = requests.get(poll_url, headers=poll_headers)
        if poll_response.status_code == 200:
            poll_result = poll_response.json()["data"]
            status = poll_result["status"]

            if status == "completed":
                video_url = poll_result["outputs"][0]
                elapsed = time.time() - start_time
                break
            elif status == "failed":
                return jsonify({'success': False, 'error': poll_result.get('error', 'Task failed')}), 500
            # else: masih processing, lanjut polling
        else:
            return jsonify({'success': False, 'error': poll_response.text}), 500
        time.sleep(0.5)

    # Simpan ke database
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'User belum login', 'redirect': '/login'}), 401
    
    # Cek kredit user
    from models import User
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