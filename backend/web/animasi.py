import os
import requests
import json
import time
import base64
import uuid
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from functools import wraps
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from models import db, Image, User, Video

load_dotenv()

animasi_bp = Blueprint('animasi', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'error': 'User belum login', 'redirect': '/login'}), 401
            return redirect(url_for('web_pages.login'))
        return f(*args, **kwargs)
    return decorated_function

@animasi_bp.route('/generate-miniatur', methods=['POST'])
@login_required
def generate_miniatur():
    try:
        # Get data from request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        image_url = data.get('image_url')
        prompt = data.get('prompt', 'Change background to Christmas tree before.')
        model = data.get('model', 'banana')  # Default to banana
        
        if not image_url:
            return jsonify({'error': 'Image URL is required'}), 400
        
        # Cek dan kurangi kredit user
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User tidak ditemukan'}), 404
        
        required_credits = 10  # Sesuai dengan info biaya di frontend
        if user.kredit < required_credits:
            return jsonify({'error': f'Kredit Anda tidak cukup untuk generate miniatur (minimal {required_credits} kredit)'}), 403
        
        # Kurangi kredit
        user.kredit -= required_credits
        db.session.commit()
        
        # Get API key
        API_KEY = os.getenv("WAVESPEED_API_KEY")
        if not API_KEY:
            return jsonify({'error': 'API key not configured'}), 500
        
        model_name = "ByteDance Seedream v4" if model == 'wavespeed' else "Banana AI"
        print(f"Making request to {model_name} for image animation")
        print(f"Image URL: {image_url}")
        print(f"Prompt: {prompt}")
        print(f"Model: {model}")
        
        # Choose API endpoint based on model
        if model == 'wavespeed':
            # ByteDance Seedream v4 via WaveSpeed AI - OPTIMIZED
            url = "https://api.wavespeed.ai/api/v3/bytedance/seedream-v4/edit"
            payload = {
                "enable_base64_output": False,
                "enable_sync_mode": False,
                "images": [image_url],
                "prompt": prompt,
                "size": "1024*1024"  # Optimized: Reduced from 2227*3183 to 1024*1024 for faster processing
            }
        else:
            # Default Banana AI (existing logic)
            url = "https://api.wavespeed.ai/api/v3/google/gemini-2.5-flash-image/edit"
            payload = {
                "enable_base64_output": False,
                "enable_sync_mode": False,
                "images": [image_url],
                "output_format": "jpeg",
                "prompt": prompt
            }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }
        
        # Retry mechanism for initial request - OPTIMIZED per model
        max_retries = 3
        retry_delay = 5
        
        # Different timeout based on model complexity
        request_timeout = 90 if model == 'wavespeed' else 60  # Wavespeed needs more time
        
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1}/{max_retries} - Making initial request (timeout: {request_timeout}s)")
                response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=request_timeout)
                
                if response.status_code == 200:
                    result = response.json()["data"]
                    request_id = result["id"]
                    print(f"Task submitted successfully. Request ID: {request_id}")
                    break
                else:
                    print(f"Error: {response.status_code}, {response.text}")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 1.5  # Exponential backoff
                        continue
                    else:
                        return jsonify({'error': f'Failed to submit task: {response.text}'}), 500
                        
            except requests.exceptions.Timeout:
                print(f"Timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                    continue
                else:
                    return jsonify({'error': 'Request timeout. Please try again.'}), 500
                    
            except requests.exceptions.ConnectionError as e:
                print(f"Connection error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                    continue
                else:
                    return jsonify({'error': 'Connection error. Please check your internet connection.'}), 500
        
        # Poll for results - OPTIMIZED per model
        result_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
        result_headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Different polling settings based on model complexity
        if model == 'wavespeed':
            max_polling_attempts = 40  # 20 minutes max (40 * 30 seconds) for heavier model
            polling_interval = 30  # 30 seconds for wavespeed
        else:
            max_polling_attempts = 60  # 10 minutes max (60 * 10 seconds) for banana
            polling_interval = 10  # 10 seconds for banana
            
        polling_attempt = 0
        print(f"Starting polling with {max_polling_attempts} attempts, {polling_interval}s interval")
        
        while polling_attempt < max_polling_attempts:
            try:
                print(f"Polling attempt {polling_attempt + 1}/{max_polling_attempts}")
                response = requests.get(result_url, headers=result_headers, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()["data"]
                    status = result["status"]
                    
                    if status == "completed":
                        output_url = result["outputs"][0]
                        print(f"Task completed. URL: {output_url}")
                        
                        # Simpan hasil ke database untuk galeri
                        try:
                            user_id = session.get('user_id')
                            if user_id:
                                # Ambil prompt dari request data untuk caption
                                caption = prompt if prompt else "Generate Miniatur - Figurine 1/7 Scale"
                                image = Image(
                                    user_id=user_id, 
                                    image_url=output_url, 
                                    caption=caption
                                )
                                db.session.add(image)
                                db.session.commit()
                                print(f'DEBUG: Miniatur result saved to database with ID: {image.id}')
                        except Exception as e:
                            print(f'DEBUG: Error saving miniatur to database: {e}')
                            db.session.rollback()
                            # Jangan error ke user jika gagal simpan DB, tapi log error
                            pass
                        
                        return jsonify({
                            'success': True,
                            'result_url': output_url,
                            'request_id': request_id
                        })
                    elif status == "failed":
                        error_msg = result.get('error', 'Unknown error')
                        print(f"Task failed: {error_msg}")
                        
                        # Rollback kredit karena task failed
                        try:
                            user.kredit += required_credits
                            db.session.commit()
                            print(f'DEBUG: Credit rolled back due to task failure')
                        except:
                            pass
                            
                        return jsonify({'error': f'Task failed: {error_msg}'}), 500
                    else:
                        print(f"Task still processing. Status: {status}")
                        polling_attempt += 1
                        time.sleep(polling_interval)  # Use dynamic polling interval
                else:
                    print(f"Polling error: {response.status_code}, {response.text}")
                    polling_attempt += 1
                    time.sleep(polling_interval)
                    
            except requests.exceptions.Timeout:
                print(f"Polling timeout on attempt {polling_attempt + 1}")
                polling_attempt += 1
                time.sleep(polling_interval)
                continue
                
            except requests.exceptions.ConnectionError as e:
                print(f"Polling connection error on attempt {polling_attempt + 1}: {e}")
                polling_attempt += 1
                time.sleep(polling_interval)
                continue
        
        # If we get here, polling timed out
        # Rollback kredit karena gagal
        try:
            user.kredit += required_credits
            db.session.commit()
            print(f'DEBUG: Credit rolled back due to timeout')
        except:
            pass
            
        return jsonify({
            'error': 'Task is taking too long to complete. Please try again later.',
            'request_id': request_id
        }), 500
        
    except Exception as e:
        print(f"Unexpected error in generate_miniatur: {str(e)}")
        
        # Rollback kredit karena error
        try:
            user_id = session.get('user_id')
            if user_id:
                user = User.query.get(user_id)
                if user:
                    user.kredit += required_credits
                    db.session.commit()
                    print(f'DEBUG: Credit rolled back due to error')
        except:
            pass
            
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@animasi_bp.route('/check-miniatur-status/<request_id>', methods=['GET'])
@login_required
def check_miniatur_status(request_id):
    try:
        API_KEY = os.getenv("WAVESPEED_API_KEY")
        if not API_KEY:
            return jsonify({'error': 'API key not configured'}), 500
        
        url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()["data"]
            status = result["status"]
            
            if status == "completed":
                output_url = result["outputs"][0]
                return jsonify({
                    'status': 'completed',
                    'result_url': output_url
                })
            elif status == "failed":
                error_msg = result.get('error', 'Unknown error')
                return jsonify({
                    'status': 'failed',
                    'error': error_msg
                })
            else:
                return jsonify({
                    'status': 'processing'
                })
        else:
            return jsonify({'error': f'Failed to check status: {response.text}'}), 500
            
    except Exception as e:
        print(f"Error checking miniatur status: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@animasi_bp.route('/upload_image_to_miniatur', methods=['POST'])
@login_required
def upload_image_to_miniatur():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
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
        
        # Batasi ukuran file (10MB untuk miniatur)
        file.seek(0, 2)  # move to end
        file_length = file.tell()
        file.seek(0)
        if file_length > 10 * 1024 * 1024:
            return jsonify({'error': 'Ukuran file terlalu besar (maksimal 10MB)'}), 400
        
        # Gunakan nama file acak (tidak disimpan ke disk, hanya base64)
        file_content = file.read()
        base64_data = base64.b64encode(file_content).decode('utf-8')
        data_url = f"data:{mime_type};base64,{base64_data}"
        
        print(f'DEBUG: File converted to base64 for miniatur')
        print(f'DEBUG: MIME type: {mime_type}')
        print(f'DEBUG: Base64 length: {len(base64_data)} characters')
        
        return jsonify({'url': data_url})
    
    return jsonify({'error': 'Upload gagal'}), 500

@animasi_bp.route('/upload_image_to_video', methods=['POST'])
@login_required
def upload_image_to_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
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
        
        # Batasi ukuran file (10MB untuk video)
        file.seek(0, 2)  # move to end
        file_length = file.tell()
        file.seek(0)
        if file_length > 10 * 1024 * 1024:
            return jsonify({'error': 'Ukuran file terlalu besar (maksimal 10MB)'}), 400
        
        # Gunakan nama file acak (tidak disimpan ke disk, hanya base64)
        file_content = file.read()
        base64_data = base64.b64encode(file_content).decode('utf-8')
        data_url = f"data:{mime_type};base64,{base64_data}"
        
        print(f'DEBUG: File converted to base64 for video')
        print(f'DEBUG: MIME type: {mime_type}')
        print(f'DEBUG: Base64 length: {len(base64_data)} characters')
        
        return jsonify({'url': data_url})
    
    return jsonify({'error': 'Upload gagal'}), 500

@animasi_bp.route('/api/generate_image_video', methods=['POST'])
@login_required
def generate_image_video():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        image_url = data.get('image')
        prompt = data.get('prompt', '')
        duration = data.get('duration', 5)
        seed = data.get('seed', -1)
        
        if not image_url:
            return jsonify({'error': 'Image URL is required'}), 400
        
        # Cek dan kurangi kredit user
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User tidak ditemukan'}), 404
        
        required_credits = 25  # Sesuai dengan info biaya di frontend
        if user.kredit < required_credits:
            return jsonify({'error': f'Kredit Anda tidak cukup untuk generate video (minimal {required_credits} kredit)'}), 403
        
        # Kurangi kredit user
        user.kredit -= required_credits
        db.session.commit()
        
        # TODO: Implement actual video generation API call
        # For now, return a placeholder video URL that can be displayed
        video_url = "https://www.w3schools.com/html/mov_bbb.mp4"
        
        # Simpan hasil ke database
        try:
            caption = f"Image to Video: {prompt}" if prompt else "Image to Video Generation"
            video = Video(
                user_id=user_id, 
                video_url=video_url, 
                caption=caption
            )
            db.session.add(video)
            db.session.commit()
            print(f'DEBUG: Video result saved to database with ID: {video.id}, URL: {video_url}, Caption: {caption}')
        except Exception as e:
            print(f'DEBUG: Error saving video to database: {e}')
            db.session.rollback()
        
        return jsonify({
            'success': True,
            'video_url': video_url,
            'message': 'Video berhasil digenerate!'
        })
        
    except Exception as e:
        print(f"Error generating video: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@animasi_bp.route('/api/get-miniatur-results', methods=['GET'])
@login_required
def get_miniatur_results():
    try:
        user_id = session.get('user_id')
        print(f'DEBUG: Getting miniatur results for user {user_id}')
        
        if not user_id:
            return jsonify({
                'success': True,
                'results': []
            })
        
        try:
            # Get miniatur results from database - ONLY for current user
            # Exclude video results (those with caption starting with "Image to Video")
            results = Image.query.filter(
                Image.user_id == user_id,
                Image.image_url.isnot(None),
                Image.image_url != '',
                ~Image.caption.ilike('Image to Video%')
            ).order_by(Image.created_at.desc()).limit(20).all()
            
            print(f'DEBUG: Found {len(results)} results for user {user_id}')
            
            results_data = []
            for result in results:
                # Validate image URL
                image_url = result.image_url
                if not image_url or image_url.strip() == '':
                    print(f'DEBUG: Skipping result {result.id} - no image URL')
                    continue
                    
                # Check if it's a valid URL or data URL
                if not (image_url.startswith('http') or image_url.startswith('data:')):
                    print(f'DEBUG: Skipping result {result.id} - invalid URL: {image_url}')
                    continue
                
                results_data.append({
                    'id': result.id,
                    'url': image_url,
                    'thumbnail': image_url,  # Use same URL as thumbnail
                    'prompt': result.caption or 'Generate Miniatur',
                    'filename': f'miniatur_{result.id}.jpg',
                    'created_at': result.created_at.isoformat(),
                    'type': 'image'
                })
            
            return jsonify({
                'success': True,
                'results': results_data
            })
            
        except Exception as db_error:
            print(f"Database error in get_miniatur_results: {str(db_error)}")
            return jsonify({
                'success': True,
                'results': [],
                'error': f'Database error: {str(db_error)}'
            })
        
    except Exception as e:
        print(f"Error getting miniatur results: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500

@animasi_bp.route('/api/test', methods=['GET'])
def test_endpoint():
    """Test endpoint untuk cek apakah server berjalan"""
    return jsonify({'success': True, 'message': 'Server is running'})

@animasi_bp.route('/api/get-video-results', methods=['GET'])
@login_required
def get_video_results():
    try:
        user_id = session.get('user_id')
        print(f'DEBUG: User ID from session: {user_id}')
        
        if not user_id:
            print('DEBUG: No user_id in session, returning empty results')
            return jsonify({
                'success': True,
                'results': []
            })
        
        # Get video results from database - FIXED: Use Video table instead of Image table
        print(f'DEBUG: Getting video results from Video table for user {user_id}')
        
        try:
            # Query videos from the correct Video table
            results = Video.query.filter(
                Video.user_id == user_id,
                Video.video_url.isnot(None),
                Video.video_url != ''
            ).order_by(Video.created_at.desc()).limit(20).all()
            
            print(f'DEBUG: Found {len(results)} video results for user {user_id}')
            
            # Debug: Check all video records for this user
            all_video_records = Video.query.filter(Video.user_id == user_id).all()
            print(f'DEBUG: Total video records for user {user_id}: {len(all_video_records)}')
            for record in all_video_records:
                print(f'DEBUG: Video Record ID: {record.id}, Caption: "{record.caption}", URL: {record.video_url}')
            
            results_data = []
            for result in results:
                print(f'DEBUG: Processing result - ID: {result.id}, URL: {result.video_url}, Caption: {result.caption}')
                # Validate URL before adding
                if result.video_url and result.video_url.strip():
                    results_data.append({
                        'id': result.id,
                        'url': result.video_url,
                        'thumbnail': result.video_url,
                        'prompt': result.caption or 'Generate Video',
                        'filename': f'video_{result.id}.mp4',
                        'created_at': result.created_at.isoformat(),
                        'type': 'video'
                    })
                    print(f'DEBUG: Added video result - ID: {result.id}, URL: {result.video_url}, Caption: {result.caption}')
                else:
                    print(f'DEBUG: Skipped result - ID: {result.id}, Invalid URL: {result.video_url}')
            
            print(f'DEBUG: Final results_data length: {len(results_data)}')
            
            return jsonify({
                'success': True,
                'results': results_data
            })
            
        except Exception as db_error:
            print(f"Database error in get_video_results: {str(db_error)}")
            return jsonify({
                'success': True,
                'results': [],
                'error': f'Database error: {str(db_error)}'
            })
        
    except Exception as e:
        print(f"Error getting video results: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500

@animasi_bp.route('/api/debug-video-data', methods=['GET'])
@login_required
def debug_video_data():
    """Debug endpoint untuk mengecek data video"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'No user_id in session'}), 401
        
        # Cek data di tabel images dengan caption "Image to Video"
        image_videos = Image.query.filter(
            Image.user_id == user_id,
            Image.caption.like('Image to Video%')
        ).all()
        
        # Cek data di tabel videos
        videos = Video.query.filter(Video.user_id == user_id).all()
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'image_videos_count': len(image_videos),
            'videos_count': len(videos),
            'image_videos': [{
                'id': img.id,
                'caption': img.caption,
                'url': img.image_url,
                'created_at': img.created_at.isoformat()
            } for img in image_videos],
            'videos': [{
                'id': vid.id,
                'caption': vid.caption,
                'url': vid.video_url,
                'created_at': vid.created_at.isoformat()
            } for vid in videos]
        })
        
    except Exception as e:
        return jsonify({'error': f'Debug error: {str(e)}'}), 500

@animasi_bp.route('/api/migrate-image-to-video', methods=['POST'])
@login_required
def migrate_image_to_video():
    """Migrate Image to Video data from images table to videos table"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'No user_id in session'}), 401
        
        # Cari semua image dengan caption "Image to Video"
        image_videos = Image.query.filter(
            Image.user_id == user_id,
            Image.caption.like('Image to Video%')
        ).all()
        
        migrated_count = 0
        for img in image_videos:
            try:
                # Buat record video baru
                video = Video(
                    user_id=img.user_id,
                    video_url=img.image_url,  # URL video disimpan di image_url
                    caption=img.caption,
                    is_favorite=img.is_favorite,
                    whitelist_reason=img.whitelist_reason,
                    view_count=img.view_count,
                    created_at=img.created_at,
                    updated_at=img.updated_at
                )
                
                # Simpan video
                db.session.add(video)
                db.session.flush()  # Flush untuk mendapatkan ID
                
                # Hapus image yang salah
                db.session.delete(img)
                
                migrated_count += 1
                print(f"Migrated: {img.caption} (ID: {img.id} -> Video ID: {video.id})")
                
            except Exception as e:
                print(f"Error migrating image ID {img.id}: {e}")
                db.session.rollback()
                continue
        
        # Commit semua perubahan
        db.session.commit()
        
        return jsonify({
            'success': True,
            'migrated_count': migrated_count,
            'message': f'Successfully migrated {migrated_count} Image to Video records'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Migration error: {str(e)}'}), 500

@animasi_bp.route('/api/delete-result/<int:result_id>', methods=['DELETE'])
@login_required
def delete_result(result_id):
    try:
        user_id = session.get('user_id')
        
        # Find the result
        result = Image.query.filter_by(
            id=result_id,
            user_id=user_id
        ).first()
        
        if not result:
            return jsonify({'error': 'Result not found'}), 404
        
        # Delete from database
        db.session.delete(result)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Result deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting result: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@animasi_bp.route('/api/generate-miniatur-prompt', methods=['POST'])
@login_required
def generate_miniatur_prompt():
    try:
        data = request.get_json()
        if not data or not data.get('image_url'):
            return jsonify({'error': 'Image URL is required'}), 400
        
        # Template prompt yang akurat untuk figurine seperti yang Anda minta
        figurine_prompt = """Create a 1/7 scale figurine of the character from the uploaded photo, in a realistic style within a real-life environment. The figurine is placed on an aesthetic computer desk, with a transparent round acrylic base without any text. On the computer screen, display the process of modeling this figurine in ZBrush. Next to the computer screen, place a toy package box in BANDAI style, printed with original illustrations, showcasing flat two-dimensional artwork. Use soft studio lighting to make the figurine appear lifelike.

The figurine should be highly detailed and professionally crafted, capturing the essence and characteristics of the character from the original image. The scene should feel like a collector's dream setup with perfect lighting and composition."""
        
        return jsonify({
            'success': True,
            'prompt': figurine_prompt
        })
        
    except Exception as e:
        print(f"Error generating miniatur prompt: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@animasi_bp.route('/generate_miniatur', methods=['GET'])
@login_required
def generate_miniatur_page():
    """Route untuk halaman Generate Miniatur AI"""
    return render_template('generate_miniatur.html')

@animasi_bp.route('/api/gallery_images', methods=['GET'])
@login_required
def get_gallery_images():
    try:
        user_id = session.get('user_id')
        
        # Get uploaded images from database
        images = Image.query.filter_by(user_id=user_id).order_by(Image.created_at.desc()).limit(50).all()
        
        images_data = []
        for img in images:
            if img.image_url and img.image_url.strip():
                images_data.append({
                    'id': img.id,
                    'url': img.image_url,
                    'caption': img.caption or 'Gambar Upload'
                })
        
        return jsonify({
            'success': True,
            'images': images_data
        })
        
    except Exception as e:
        print(f'DEBUG: Error loading gallery images: {e}')
        return jsonify({'error': 'Gagal memuat galeri gambar'}), 500

@animasi_bp.route('/api/gallery_generated_images', methods=['GET'])
@login_required
def get_gallery_generated_images():
    try:
        user_id = session.get('user_id')
        
        # Get generated images from database
        images = Image.query.filter_by(user_id=user_id).order_by(Image.created_at.desc()).limit(50).all()
        
        images_data = []
        for img in images:
            if img.image_url and img.image_url.strip():
                images_data.append({
                    'id': img.id,
                    'url': img.image_url,
                    'caption': img.caption or 'Hasil Generate AI'
                })
        
        return jsonify({
            'success': True,
            'images': images_data
        })
        
    except Exception as e:
        print(f'DEBUG: Error loading gallery generated images: {e}')
        return jsonify({'error': 'Gagal memuat galeri gambar hasil generate'}), 500
