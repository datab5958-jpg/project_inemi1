import os
import requests
import time
from flask import Blueprint, request, jsonify, current_app, url_for, session
from dotenv import load_dotenv
from models import db, Image

load_dotenv()

fusigaya_bp = Blueprint('fusigaya', __name__)

def sanitize_text(text):
    import re
    # Hapus tag HTML dasar
    return re.sub(r'<[^>]+>', '', text) if text else text

@fusigaya_bp.route('/api/fusigaya', methods=['POST'])
def fusigaya():
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'User belum login'}), 401
    
    # Cek kredit user
    from models import User
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User tidak ditemukan'}), 404
    
    # Get request data first to extract model
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400
    
    model = data.get('model', 'flux-kontext-dev')  # Default model
    
    # Validate model
    valid_models = ['flux-kontext-dev', 'flux-kontext-pro', 'nano-banana']
    if model not in valid_models:
        return jsonify({'success': False, 'error': f'Invalid model: {model}. Valid models: {", ".join(valid_models)}'}), 400
    
    # Credit cost based on model
    credit_costs = {
        'flux-kontext-dev': 15,
        'flux-kontext-pro': 20,
        'nano-banana': 15
    }
    
    required_credits = credit_costs.get(model, 15)
    
    if user.kredit < required_credits:
        return jsonify({'success': False, 'error': f'Kredit Anda tidak cukup untuk generate gambar dengan model {model} (minimal {required_credits} kredit)'}), 403
    
    # Kurangi kredit
    try:
        user.kredit -= required_credits
        db.session.commit()
        print(f'DEBUG CREDIT DEDUCTED: {required_credits}, Remaining: {user.kredit}')
    except Exception as e:
        print(f'DEBUG CREDIT DEDUCTION ERROR: {e}')
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to deduct credits'}), 500
    
    # Extract other data
    prompt = sanitize_text(data.get('prompt'))
    if not prompt or not prompt.strip():
        return jsonify({'success': False, 'error': 'Prompt is required'}), 400
    
    images = data.get('images', [])
    if not images or not isinstance(images, list):
        return jsonify({'success': False, 'error': 'Images must be a list'}), 400
    
    # Set default values for optional parameters
    seed = data.get('seed', -1)
    guidance_scale = data.get('guidance_scale', 2.5)
    num_images = data.get('num_images', 1)
    num_inference_steps = data.get('num_inference_steps', 28)
    enable_base64_output = data.get('enable_base64_output', False)
    enable_safety_checker = data.get('enable_safety_checker', True)
    
    # Validate parameter ranges for FLUX models
    if model in ['flux-kontext-dev', 'flux-kontext-pro']:
        if not isinstance(num_inference_steps, (int, float)) or num_inference_steps < 1 or num_inference_steps > 100:
            return jsonify({'success': False, 'error': 'num_inference_steps must be between 1 and 100'}), 400
        if not isinstance(guidance_scale, (int, float)) or guidance_scale < 0.1 or guidance_scale > 20:
            return jsonify({'success': False, 'error': 'guidance_scale must be between 0.1 and 20'}), 400
        if not isinstance(num_images, int) or num_images < 1 or num_images > 10:
            return jsonify({'success': False, 'error': 'num_images must be between 1 and 10'}), 400

    api_key = current_app.config.get('WAVESPEED_API_KEY')
    if not api_key:
        return jsonify({'success': False, 'error': 'API key not configured'}), 500

    # Model selection logic
    model_urls = {
        'flux-kontext-dev': "https://api.wavespeed.ai/api/v3/wavespeed-ai/flux-kontext-dev/multi-ultra-fast",
        'flux-kontext-pro': "https://api.wavespeed.ai/api/v3/wavespeed-ai/flux-kontext-pro/multi",
        'nano-banana': "https://api.wavespeed.ai/api/v3/google/nano-banana/edit"
    }
    
    url = model_urls.get(model, model_urls['flux-kontext-dev'])
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    # Gunakan gambar langsung tanpa validasi URL yang rumit
    print(f'DEBUG: Processing {len(images)} images')
    print(f'DEBUG: Image URLs: {images}')
    print(f'DEBUG: Using model: {model}')
    valid_images = images  # Gunakan semua gambar yang dikirim
    
    # Prepare payload based on model
    if model == 'nano-banana':
        # Validate image URLs or base64 data before sending
        validated_images = []
        for img_data in valid_images:
            if img_data and img_data.strip():
                # Check if it's a URL (http/https)
                if img_data.startswith(('http://', 'https://')):
                    try:
                        # Test if image URL is accessible
                        test_response = requests.head(img_data, timeout=5, allow_redirects=True)
                        if test_response.status_code in [200, 301, 302]:
                            validated_images.append(img_data)
                            print(f'DEBUG: Valid URL image: {img_data[:50]}...')
                        else:
                            print(f'DEBUG: Invalid image URL {img_data}: {test_response.status_code}')
                    except Exception as e:
                        print(f'DEBUG: Image URL validation failed {img_data}: {e}')
                # Check if it's base64 data
                elif img_data.startswith('data:image/'):
                    # Basic base64 validation
                    try:
                        # Check if it has proper base64 format
                        if 'base64,' in img_data and len(img_data.split('base64,')[1]) > 0:
                            validated_images.append(img_data)
                            print(f'DEBUG: Valid base64 image: {img_data[:50]}...')
                        else:
                            print(f'DEBUG: Invalid base64 format: {img_data[:50]}...')
                    except Exception as e:
                        print(f'DEBUG: Base64 validation failed: {e}')
                else:
                    print(f'DEBUG: Invalid image format (not URL or base64): {img_data[:50]}...')
        
        if not validated_images:
            return jsonify({'success': False, 'error': 'Tidak ada gambar valid yang dapat diproses. Gunakan URL (http/https) atau base64 data (data:image/...).'}), 400
        
        payload = {
            "enable_base64_output": enable_base64_output,
            "enable_sync_mode": False,
            "images": validated_images,
            "output_format": "jpeg",
            "prompt": prompt
        }
    else:
        payload = {
            "enable_base64_output": enable_base64_output,
            "enable_safety_checker": enable_safety_checker,
            "enable_sync_mode": False,
            "guidance_scale": guidance_scale,
            "images": valid_images,
            "num_images": num_images,
            "num_inference_steps": num_inference_steps,
            "prompt": prompt,
            "seed": seed
        }

    print('DEBUG FUSIGAYA PAYLOAD:', payload)
    print(f'DEBUG MODEL SELECTED: {model}')
    print(f'DEBUG API URL: {url}')
    print(f'DEBUG CREDIT COST: {required_credits}')
    print(f'DEBUG VALIDATED IMAGES COUNT: {len(validated_images) if model == "nano-banana" else len(valid_images)}')
    begin = time.time()
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        print('DEBUG FUSIGAYA RESPONSE:', response.status_code, response.text)
        
        if response.status_code == 200:
            try:
                result = response.json()
                if "data" not in result:
                    return jsonify({'success': False, 'error': 'Invalid response format: no data field'}), 500
                
                result_data = result["data"]
                if "id" not in result_data:
                    return jsonify({'success': False, 'error': 'Invalid response format: no request id'}), 500
                
                request_id = result_data["id"]
                print(f'DEBUG REQUEST ID: {request_id}')
            except Exception as e:
                print(f'DEBUG JSON PARSE ERROR: {e}')
                return jsonify({'success': False, 'error': f'Failed to parse response: {str(e)}'}), 500
        else:
            error_msg = f'API request failed with status {response.status_code}'
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg = error_data['error']
                elif 'message' in error_data:
                    error_msg = error_data['message']
                elif 'detail' in error_data:
                    error_msg = error_data['detail']
            except:
                error_msg = response.text or error_msg
            
            # Specific error handling for nano-banana
            if model == 'nano-banana':
                if response.status_code == 400:
                    error_msg = f'Nano-banana edit gagal: {error_msg}. Pastikan gambar valid dan prompt sesuai.'
                elif response.status_code == 422:
                    error_msg = f'Format data tidak valid untuk nano-banana: {error_msg}. Periksa URL gambar dan prompt.'
                elif response.status_code == 500:
                    error_msg = f'Server nano-banana error: {error_msg}. Coba lagi nanti.'
            
            print(f'DEBUG API ERROR: {error_msg}')
            return jsonify({'success': False, 'error': error_msg}), 500
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'Request timeout - API took too long to respond'}), 500
    except requests.exceptions.RequestException as e:
        print(f'DEBUG REQUEST ERROR: {e}')
        return jsonify({'success': False, 'error': f'Request failed: {str(e)}'}), 500
    except Exception as e:
        print(f'DEBUG UNEXPECTED ERROR: {e}')
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500

    poll_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
    poll_headers = {"Authorization": f"Bearer {api_key}"}

    max_attempts = 600  # 60 detik dengan interval 0.1 detik (Fusigaya butuh waktu lebih lama)
    attempt = 0
    
    while attempt < max_attempts:
        try:
            poll_response = requests.get(poll_url, headers=poll_headers, timeout=30)
            print(f'DEBUG POLL ATTEMPT {attempt + 1}: {poll_response.status_code}')
            
            if poll_response.status_code == 200:
                poll_result = poll_response.json()
                print(f'DEBUG POLL RESULT: {poll_result}')
                
                if "data" not in poll_result:
                    print(f'DEBUG: No data in poll result: {poll_result}')
                    attempt += 1
                    time.sleep(0.1)
                    continue
                    
                poll_data = poll_result["data"]
                status = poll_data.get("status")
                print(f'DEBUG STATUS: {status}')
                
                if status == "completed":
                    end = time.time()
                    outputs = poll_data.get("outputs", [])
                    if not outputs:
                        return jsonify({'success': False, 'error': 'No outputs in completed task'}), 500
                    
                    output_url = outputs[0]
                    print(f'DEBUG OUTPUT URL: {output_url}')
                    
                    # Simpan ke database
                    try:
                        image = Image(user_id=user_id, image_url=output_url, caption=prompt)
                        db.session.add(image)
                        db.session.commit()
                        print(f'DEBUG IMAGE SAVED TO DB: {image.id}')
                    except Exception as e:
                        print(f'DEBUG DB ERROR: {e}')
                        db.session.rollback()
                        # Jangan errorkan user jika gagal simpan DB, tapi log error
                        pass
                    
                    return jsonify({'success': True, 'output_url': output_url, 'elapsed': end-begin})
                elif status == "failed":
                    error_msg = poll_data.get('error', 'Task failed')
                    print(f'DEBUG TASK FAILED: {error_msg}')
                    return jsonify({'success': False, 'error': error_msg}), 500
                elif status == "processing":
                    print(f'DEBUG: Still processing... attempt {attempt + 1}')
                else:
                    print(f'DEBUG: Unknown status: {status}')
            else:
                print(f'DEBUG POLL ERROR: {poll_response.status_code} - {poll_response.text}')
                return jsonify({'success': False, 'error': f'Poll failed: {poll_response.text}'}), 500
                
        except requests.exceptions.Timeout:
            print(f'DEBUG POLLING TIMEOUT: Attempt {attempt + 1}')
            # Don't return error immediately, continue polling
            attempt += 1
            time.sleep(0.1)
            continue
        except requests.exceptions.RequestException as e:
            print(f'DEBUG REQUEST ERROR: {e}')
            return jsonify({'success': False, 'error': f'Request error: {str(e)}'}), 500
        except Exception as e:
            print(f'DEBUG UNEXPECTED ERROR: {e}')
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500
            
        attempt += 1
        time.sleep(0.1)
    
    return jsonify({'success': False, 'error': 'Timeout: Task took too long to complete'}), 500

@fusigaya_bp.route('/api/gallery_images', methods=['GET'])
def gallery_images():
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    images = Image.query.order_by(Image.created_at.desc()).limit(50).all()
    data = [
        {
            'id': img.id,
            'url': img.image_url,
            'caption': img.caption or ''
        } for img in images
    ]
    return jsonify({'success': True, 'images': data})

@fusigaya_bp.route('/upload_image_to_fusigaya', methods=['POST'])
def upload_image_to_fusigaya():
    # Cek session user
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
        import uuid
        from werkzeug.utils import secure_filename
        
        # Validasi ekstensi file
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in allowed_extensions:
            return jsonify({'error': 'Tipe file tidak didukung. Gunakan PNG, JPG, JPEG, GIF, atau WEBP'}), 400
        
        # Validasi MIME type
        allowed_mimes = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
        mime_type = file.content_type or 'image/jpeg'
        if mime_type not in allowed_mimes:
            return jsonify({'error': 'Tipe MIME file tidak valid'}), 400
        
        # Batasi ukuran file (misal 5MB)
        file.seek(0, 2)  # move to end
        file_length = file.tell()
        file.seek(0)
        if file_length > 5 * 1024 * 1024:
            return jsonify({'error': 'Ukuran file terlalu besar (maksimal 5MB)'}), 400
        
        # Gunakan nama file acak (tidak disimpan ke disk, hanya base64)
        file_content = file.read()
        base64_data = base64.b64encode(file_content).decode('utf-8')
        data_url = f"data:{mime_type};base64,{base64_data}"
        
        print(f'DEBUG: File converted to base64')
        print(f'DEBUG: MIME type: {mime_type}')
        print(f'DEBUG: Base64 length: {len(base64_data)} characters')
        
        return jsonify({'url': data_url})
    return jsonify({'error': 'Upload gagal'}), 500 