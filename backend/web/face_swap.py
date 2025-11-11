import os
import requests
import json
import time
import base64
from flask import Blueprint, request, jsonify, current_app, session
from dotenv import load_dotenv
from models import db, Image, User

load_dotenv()

face_swap_bp = Blueprint('face_swap', __name__)

@face_swap_bp.route('/api/face_swap_test', methods=['GET'])
def face_swap_test():
    print('DEBUG: Face swap test endpoint called')
    return jsonify({'success': True, 'message': 'Face Swap blueprint is working!'})

@face_swap_bp.route('/api/face_swap_status', methods=['GET'])
def face_swap_status():
    print('DEBUG: Face swap status endpoint called')
    return jsonify({
        'success': True, 
        'message': 'Face Swap endpoint is accessible',
        'endpoints': ['/api/face_swap', '/api/face_swap_test', '/upload_image_to_face_swap']
    })

@face_swap_bp.route('/api/face_swap', methods=['POST'])
def face_swap():
    print('DEBUG: Face swap endpoint called')
    print('DEBUG: Request method:', request.method)
    print('DEBUG: Request headers:', dict(request.headers))
    print('DEBUG: Request data:', request.get_data())
    
    try:
        data = request.json
        print('DEBUG: Parsed JSON data:', data)
    except Exception as e:
        print('DEBUG: Error parsing JSON:', str(e))
        return jsonify({'success': False, 'error': f'Invalid JSON: {str(e)}'}), 400
    
    face_image = data.get('face_image')
    image = data.get('image')
    target_index = data.get('target_index', 0)
    output_format = data.get('output_format', 'jpeg')
    enable_base64_output = data.get('enable_base64_output', False)
    enable_safety_checker = data.get('enable_safety_checker', True)
    enable_sync_mode = data.get('enable_sync_mode', False)
    
    print('DEBUG: Extracted data:')
    print('  - face_image:', face_image)
    print('  - image:', image)
    print('  - target_index:', target_index)
    print('  - output_format:', output_format)
    print('  - enable_base64_output:', enable_base64_output)
    print('  - enable_safety_checker:', enable_safety_checker)
    print('  - enable_sync_mode:', enable_sync_mode)
    
    # Validasi data yang diperlukan
    if not image:
        return jsonify({'success': False, 'error': 'Image is required'}), 400
    if not face_image:
        return jsonify({'success': False, 'error': 'Face image is required'}), 400

    # Clean base64 data if it's a data URL
    def clean_base64_data(data):
        if isinstance(data, str) and data.startswith('data:'):
            # Extract base64 part from data URL
            try:
                # Split by comma and take the base64 part
                base64_part = data.split(',', 1)[1]
                # Ensure proper padding
                padding = 4 - (len(base64_part) % 4)
                if padding != 4:
                    base64_part += '=' * padding
                return base64_part
            except Exception as e:
                print(f'DEBUG: Error cleaning base64 data: {e}')
                return data
        elif isinstance(data, str) and (data.startswith('http://') or data.startswith('https://')):
            # If it's a regular URL, return as is
            return data
        elif isinstance(data, str) and len(data) > 100:
            # If it's a long string, might be base64 data without data: prefix
            try:
                # Test if it's valid base64
                base64.b64decode(data)
                return data
            except:
                # If not valid base64, return as is
                return data
        return data

    # Clean the image data
    cleaned_image = clean_base64_data(image)
    cleaned_face_image = clean_base64_data(face_image)
    
    print('DEBUG: Cleaned data:')
    print('  - cleaned_image type:', type(cleaned_image))
    print('  - cleaned_face_image type:', type(cleaned_face_image))
    print('  - cleaned_image length:', len(str(cleaned_image)) if cleaned_image else 0)
    print('  - cleaned_face_image length:', len(str(cleaned_face_image)) if cleaned_face_image else 0)
    
    # Validasi data setelah cleaning
    if not cleaned_image or len(str(cleaned_image).strip()) == 0:
        return jsonify({'success': False, 'error': 'Invalid image data after cleaning'}), 400
    if not cleaned_face_image or len(str(cleaned_face_image).strip()) == 0:
        return jsonify({'success': False, 'error': 'Invalid face image data after cleaning'}), 400

    # Ambil API key langsung dari environment variable seperti di script test
    api_key = os.getenv('WAVESPEED_API_KEY')
    print(f'DEBUG API KEY: {api_key[:10]}...' if api_key else 'API KEY NOT FOUND')
    if not api_key:
        return jsonify({'success': False, 'error': 'API key not configured'}), 500

    # Use the correct URL from your test script
    url = "https://api.wavespeed.ai/api/v3/wavespeed-ai/image-face-swap"
    print(f'DEBUG FACE SWAP URL: {url}')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    print(f'DEBUG FACE SWAP HEADERS: {headers}')
    payload = {
        "enable_base64_output": enable_base64_output,
        "enable_safety_checker": enable_safety_checker,
        "enable_sync_mode": enable_sync_mode,
        "face_image": cleaned_face_image,
        "image": cleaned_image,
        "output_format": output_format,
        "target_index": target_index
    }

    print('DEBUG FACE SWAP PAYLOAD:', json.dumps(payload, indent=2))
    begin = time.time()
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        print('DEBUG FACE SWAP RESPONSE:', response.status_code, response.text)
        
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
                return jsonify({'success': False, 'error': f'Failed to parse response: {str(e)}'}), 500
        else:
            return jsonify({'success': False, 'error': f'API request failed: {response.text}'}), 500
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'Request timeout - Face swap API took too long to respond. Please try again.'}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'error': f'Request failed: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500

    poll_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
    poll_headers = {"Authorization": f"Bearer {api_key}"}

    max_attempts = 120  # 60 detik dengan interval 0.5 detik (face swap butuh waktu lebih lama)
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
                    time.sleep(0.5)
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
                    
                    # Simpan ke database jika user login
                    try:
                        user_id = session.get('user_id')
                        if user_id:
                            user = User.query.get(user_id)
                            if user and user.kredit >= 15:
                                user.kredit -= 15
                                image = Image(user_id=user_id, image_url=output_url, caption="Face Swap Result", generation_type='face_swap')
                                db.session.add(image)
                                db.session.commit()
                    except Exception as e:
                        print(f'DEBUG DB ERROR: {e}')
                        pass  # Jangan errorkan user jika gagal simpan DB
                    
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
            time.sleep(0.5)
            continue
        except requests.exceptions.RequestException as e:
            print(f'DEBUG REQUEST ERROR: {e}')
            return jsonify({'success': False, 'error': f'Request error: {str(e)}'}), 500
        except Exception as e:
            print(f'DEBUG UNEXPECTED ERROR: {e}')
            return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500
            
        attempt += 1
        time.sleep(0.5)
    
    return jsonify({'success': False, 'error': 'Timeout: Task took too long to complete'}), 500

@face_swap_bp.route('/upload_image_to_face_swap', methods=['POST'])
def upload_image_to_face_swap():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if file:
        # Read file and convert to base64
        # Read file content
        file_content = file.read()
        
        # Get MIME type
        mime_type = file.content_type or 'image/jpeg'
        
        # Convert to base64
        base64_data = base64.b64encode(file_content).decode('utf-8')
            
        data_url = f"data:{mime_type};base64,{base64_data}"
        
        print(f'DEBUG: File converted to base64')
        print(f'DEBUG: MIME type: {mime_type}')
        print(f'DEBUG: Base64 length: {len(base64_data)} characters')
        
        return jsonify({'url': data_url})
    return jsonify({'error': 'Upload gagal'}), 500 