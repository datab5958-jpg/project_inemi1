from flask import Blueprint, render_template, request, jsonify, send_from_directory, session, current_app
import os, uuid, requests
from .utils import get_width_height
from models import db, Image, User

foto_bp = Blueprint('foto', __name__)


@foto_bp.route('/generate_photo', methods=['POST'])
def generate_photo():
    """
    Endpoint ini HANYA untuk generate gambar baru (insert baru ke database).
    Tidak untuk edit prompt atau regenerate gambar yang sudah ada.
    Untuk edit/regenerate, gunakan endpoint /regenerate_image/<id>.
    """
    # Validate input
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'Data tidak valid', 'error': 'Data tidak valid'}), 400

    prompt = data.get('prompt')
    if not prompt:
        return jsonify({'success': False, 'message': 'Prompt tidak boleh kosong', 'error': 'Prompt tidak boleh kosong'}), 400
    aspect_ratio = data.get('aspect_ratio', '1:1')
    width, height = get_width_height(aspect_ratio)
    negative_prompt = data.get('negative_prompt', '')

    # Check API key
    API_KEY = current_app.config.get('WAVESPEED_API_KEY')
    if not API_KEY:
        return jsonify({'success': False, 'message': 'API key tidak ditemukan', 'error': 'API key tidak ditemukan'}), 500
    # Check user session and credits
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User belum login', 'error': 'User belum login'}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User tidak ditemukan', 'error': 'User tidak ditemukan'}), 404

    if user.kredit < 15:
        return jsonify({'success': False, 'message': 'Kredit Anda tidak cukup untuk generate gambar (minimal 15 kredit)', 'error': 'Kredit Anda tidak cukup untuk generate gambar (minimal 15 kredit)'}), 403

    # Get model selection from request
    model = data.get('model', 'imagen4-ultra')  # Default to imagen4-ultra
    
    # Model selection logic
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
        return jsonify({'success': False, 'message': f'Model tidak valid: {model}', 'error': f'Model tidak valid: {model}'}), 400
    
    # Check credits based on model
    required_credits = model_configs[model]['credits']
    if user.kredit < required_credits:
        return jsonify({'success': False, 'message': f'Kredit Anda tidak cukup untuk generate gambar dengan model {model} (minimal {required_credits} kredit)', 'error': f'Kredit Anda tidak cukup untuk generate gambar dengan model {model} (minimal {required_credits} kredit)'}), 403
    
    # Get model configuration
    model_config = model_configs[model]
    url = model_config['url']
    payload = model_config['payload']
    
    # Debug logging
    print(f'DEBUG: Using model: {model}')
    print(f'DEBUG: API URL: {url}')
    print(f'DEBUG: Payload: {payload}')
    print(f'DEBUG: Required credits: {required_credits}')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    image_url = None
    error_message = None
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
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
        import time
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
                    elif status == "processing":
                        pass
                    else:
                        pass
                else:
                    error_message = f'Gagal polling: HTTP {resp.status_code}'
                    raise Exception(error_message)
            except Exception as e:
                print('ERROR saat polling:', str(e))
                error_message = str(e)
            time.sleep(0.5)

    # Jika gagal generate gambar, return error (jangan simpan placeholder, jangan potong kredit)
    if not image_url:
        print('GAGAL: tidak ada gambar valid, tidak simpan ke database, tidak potong kredit')
        return jsonify({
            'success': False,
            'message': f'Gagal generate gambar: {error_message}',
            'photo_url': None,
            'error': error_message
        }), 500

    # Save to database jika sukses
    try:
        user.kredit -= required_credits
        image = Image(user_id=user_id, image_url=image_url, caption=prompt)
        db.session.add(image)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Foto berhasil dibuat dengan model {model}, disimpan (link), dan dicatat di database',
            'photo_url': image_url,
            'error': None,
            'model_used': model,
            'credits_used': required_credits
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal menyimpan ke database: {str(e)}', 'error': f'Gagal menyimpan ke database: {str(e)}'}), 500
