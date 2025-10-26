from flask import Blueprint, request, jsonify, current_app, session, send_file, send_from_directory, abort, redirect
import google.generativeai as genai
import os, base64, io
from PIL import Image
from models import Comment, User, Prompt, db, Song
from ai_utils import AIUtils
from config import Config
from dotenv import load_dotenv
import requests
import google.generativeai as google_genai
from google.generativeai import types as genai_types
from PIL import Image as PILImage
from io import BytesIO
import json
import uuid
from datetime import datetime, timedelta
import pathlib
import openai
from flask import Response
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chat import get_prompt_service

load_dotenv()

api_routes = Blueprint('api_routes', __name__)

# Configure Gemini API with proper API key
GEMINI_API_KEY = Config.GEMINI_API_KEY
genai.configure(api_key=GEMINI_API_KEY)
text_model = genai.GenerativeModel('gemini-2.0-flash')
# Note: Vision model deprecated, use REST API approach instead
chat_history = {}

# Initialize AI Utils
ai_utils = AIUtils(GEMINI_API_KEY)

@api_routes.route('/generate-prompt', methods=['POST'])
def generate_prompt():
    """Generate AI prompt from form data"""
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'User belum login'}), 401
    
    try:
        data = request.get_json()
        
        # Extract form data
        form_data = {
            'subject': data.get('subject', ''),
            'action': data.get('action', ''),
            'expression': data.get('expression', ''),
            'location': data.get('location', ''),
            'time': data.get('time', ''),
            'camera_angle': data.get('camera_angle', ''),
            'camera_movement': data.get('camera_movement', ''),
            'lighting': data.get('lighting', '')
        }
        
        # Generate prompt using AI
        result = ai_utils.generate_prompt_from_form(form_data)
        
        if result['success']:
            # Save to database
            if user_id:
                try:
                    prompt = Prompt(
                        subject=form_data['subject'],
                        action=form_data['action'],
                        expression=form_data['expression'],
                        location=form_data['location'],
                        time=form_data['time'],
                        camera_angle=form_data['camera_angle'],
                        camera_movement=form_data['camera_movement'],
                        lighting=form_data['lighting'],
                        generated_prompt=result['generated_prompt'],
                        user_id=user_id
                    )
                    db.session.add(prompt)
                    db.session.commit()
                    result['prompt_id'] = prompt.id
                except Exception as e:
                    # Continue even if database save fails
                    print(f"Database save error: {e}")
                    pass
            
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"Error in generate_prompt: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_routes.route('/prompts', methods=['GET'])
def get_prompts():
    """Get user's saved prompts"""
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    try:
        
        prompts = Prompt.query.filter_by(user_id=user_id).order_by(Prompt.created_at.desc()).all()
        
        result = []
        for prompt in prompts:
            result.append({
                'id': prompt.id,
                'subject': prompt.subject,
                'action': prompt.action,
                'expression': prompt.expression,
                'location': prompt.location,
                'time': prompt.time,
                'camera_angle': prompt.camera_angle,
                'camera_movement': prompt.camera_movement,
                'lighting': prompt.lighting,
                'generated_prompt': prompt.generated_prompt,
                'created_at': prompt.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return jsonify({'success': True, 'prompts': result})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_routes.route('/prompts/<int:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Delete a saved prompt"""
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    try:
        prompt = Prompt.query.get_or_404(prompt_id)
        # Pastikan user hanya bisa hapus prompt miliknya sendiri
        if prompt.user_id != user_id:
            return jsonify({'error': 'Tidak memiliki akses untuk menghapus prompt ini'}), 403
        
        db.session.delete(prompt)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Prompt deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_routes.route('/generate-text', methods=['POST'])
def generate_text():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        response = text_model.generate_content(prompt)
        return jsonify({'success': True, 'response': response.text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_routes.route('/generate-image-description', methods=['POST'])
def generate_image_description():
    try:
        data = request.get_json()
        image_data = data.get('image')
        prompt = data.get('prompt', 'Describe this image in detail')
        if not image_data:
            return jsonify({'error': 'Image is required'}), 400
        try:
            # Use REST API approach (same as chat.py)
            headers = {
                'Content-Type': 'application/json',
            }
            
            # Clean base64 data
            clean_image_data = image_data.split(',')[1] if ',' in image_data else image_data
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": clean_image_data
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 10000,
                }
            }
            
            # Use same URL as chat.py
            api_url = f"{Config.GEMINI_API_URL}?key={Config.GEMINI_API_KEY}"
            resp = requests.post(api_url, headers=headers, json=payload)
            if resp.status_code == 200:
                result = resp.json()
                desc = result['candidates'][0]['content']['parts'][0]['text'] if result.get('candidates') else 'No description.'
                return jsonify({'success': True, 'description': desc})
            else:
                return jsonify({'success': False, 'error': f'Gemini API error: {resp.text}'})
                
        except Exception as e:
            return jsonify({'success': False, 'error': f'Vision API error: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_routes.route('/chat', methods=['POST'])
def chat_api():
    # Cek session user
    session_user_id = session.get('user_id')
    if not session_user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    try:
        data = request.get_json()
        message = data.get('message', '')
        user_id = str(session_user_id)  # Gunakan session user_id
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        if user_id not in chat_history:
            chat_history[user_id] = []
        chat_history[user_id].append({'role': 'user', 'parts': [message]})
        history_for_gemini = chat_history[user_id][:-1]
        chat = text_model.start_chat(history=history_for_gemini)
        # Tambahkan instruksi bahasa Indonesia
        prompt_id = f"Jawab selalu dalam bahasa Indonesia. {message}"
        response = chat.send_message(prompt_id)
        # FILTER MARKDOWN DAN RAPIKAN TAMPILAN
        import re
        def bersihkan_markdown(teks):
            # Hilangkan **, *, _, `, heading #, [link](url), ![img](url)
            teks = re.sub(r'\*\*(.*?)\*\*', r'\1', teks)
            teks = re.sub(r'\*(.*?)\*', r'\1', teks)
            teks = re.sub(r'_(.*?)_', r'\1', teks)
            teks = re.sub(r'`(.*?)`', r'\1', teks)
            teks = re.sub(r'#+\s*', '', teks)
            teks = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', teks)
            teks = re.sub(r'!\[.*?\]\(.*?\)', '', teks)
            # List markdown (1. 2. - * >) jadi bullet/indent
            # Numbered list
            teks = re.sub(r'(?m)^\s*\d+\.\s+', '\n• ', teks)
            # Bullet list
            teks = re.sub(r'(?m)^\s*[-*+]\s+', '\n• ', teks)
            # Blockquote/quote
            teks = re.sub(r'(?m)^\s*>\s*', '\n  ', teks)
            # Hapus spasi berlebih di awal baris
            teks = re.sub(r'(?m)^\s+', '', teks)
            # Maksimal 2 baris baru berturut-turut
            teks = re.sub(r'\n{3,}', '\n\n', teks)
            # Bersihkan spasi berlebih
            teks = re.sub(r'[ \t]+$', '', teks, flags=re.MULTILINE)
            return teks.strip()
        clean_response = bersihkan_markdown(response.text)
        chat_history[user_id].append({'role': 'model', 'parts': [clean_response]})
        if len(chat_history[user_id]) > 10:
            chat_history[user_id] = chat_history[user_id][-10:]
        return jsonify({'success': True, 'response': clean_response, 'history': chat_history[user_id]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_routes.route('/generate-creative-content', methods=['POST'])
def generate_creative_content():
    try:
        data = request.get_json()
        content_type = data.get('type', 'story')
        topic = data.get('topic', '')
        style = data.get('style', 'creative')
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        prompt = f"Write a {style} {content_type} about {topic}."
        response = text_model.generate_content(prompt)
        return jsonify({'success': True, 'content': response.text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_routes.route('/analyze-sentiment', methods=['POST'])
def analyze_sentiment():
    try:
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        prompt = f"Analyze the sentiment of this text and give a summary: {text}"
        response = text_model.generate_content(prompt)
        return jsonify({'success': True, 'analysis': response.text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_routes.route('/translate', methods=['POST'])
def translate_text():
    try:
        data = request.get_json()
        text = data.get('text', '')
        target_language = data.get('target_language', 'English')
        source_language = data.get('source_language', 'auto')
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        prompt = f"Translate from {source_language} to {target_language}: {text}"
        response = text_model.generate_content(prompt)
        return jsonify({'success': True, 'translation': response.text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@api_routes.route('/generate-image-and-prompt', methods=['POST'])
def generate_image_and_prompt():
    try:
        data = request.get_json()
        contents = data.get('contents')
        if not contents:
            return jsonify({'success': False, 'error': 'Contents is required'}), 400
        client = google_genai.Client()
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=contents,
            config=genai_types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        result_text = None
        result_image_base64 = None
        for part in response.candidates[0].content.parts:
            if getattr(part, 'text', None) is not None:
                result_text = part.text
            elif getattr(part, 'inline_data', None) is not None:
                image = PILImage.open(BytesIO(part.inline_data.data))
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                result_image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return jsonify({'success': True, 'text': result_text, 'image_base64': result_image_base64})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@api_routes.route('/api/generate-prompt-auto', methods=['POST'])
def generate_prompt_auto():
    try:
        data = request.get_json()
        base = data.get('base')
        if not base:
            return jsonify({'success': False, 'error': 'Base description is required'}), 400
        client = google_genai.Client()
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=base,
            config=genai_types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        result_text = None
        result_image_base64 = None
        for part in response.candidates[0].content.parts:
            if getattr(part, 'text', None) is not None:
                result_text = part.text
            elif getattr(part, 'inline_data', None) is not None:
                image = PILImage.open(BytesIO(part.inline_data.data))
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                result_image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return jsonify({'success': True, 'generated_prompt': result_text, 'image_base64': result_image_base64})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@api_routes.route('/generate-image-imagen', methods=['POST'])
def generate_image_imagen():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400
        api_key = Config.GEMINI_API_KEY
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1}
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        if result and result.get("predictions") and len(result["predictions"]) > 0:
            base64_image_data = result["predictions"][0].get("bytesBase64Encoded")
            if base64_image_data:
                return jsonify({"success": True, "image_url": f"data:image/png;base64,{base64_image_data}"})
            else:
                return jsonify({"success": False, "error": "No image data found in response."})
        else:
            return jsonify({"success": False, "error": "Unexpected API response or empty predictions."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@api_routes.route('/auto-fill-form', methods=['POST'])
def auto_fill_form():
    """Auto-fill form fields using AI based on user input"""
    try:
        data = request.get_json()
        user_input = data.get('user_input', '').strip()
        
        if not user_input:
            return jsonify({'success': False, 'error': 'User input is required'}), 400
        
        # Create AI prompt to analyze user input and fill form fields
        ai_prompt = f"""
        Analisis input pengguna berikut dan isi form fields untuk AI image generator:
        
        Input pengguna: "{user_input}"
        
        Isi form fields berikut berdasarkan input di atas:
        1. subject (Subjek/Siapa/Apa) - karakter atau objek utama
        2. action (Aksi/Apa yang terjadi) - aktivitas atau gerakan
        3. expression (Ekspresi/Emosi) - perasaan atau ekspresi wajah
        4. location (Tempat/Latar belakang) - setting atau lokasi
        5. time (Waktu) - waktu hari atau suasana waktu
        6. camera_angle (Sudut kamera) - angle pengambilan gambar
        7. camera_movement (Pergerakan kamera) - gerakan kamera
        8. lighting (Pencahayaan) - jenis pencahayaan
        9. negative_prompt (Negatif Prompt) - hal yang harus dihindari
        
        Berikan jawaban dalam format JSON seperti ini:
        {{
            "subject": "deskripsi subjek",
            "action": "deskripsi aksi",
            "expression": "deskripsi ekspresi",
            "location": "deskripsi lokasi",
            "time": "deskripsi waktu",
            "camera_angle": "deskripsi sudut kamera",
            "camera_movement": "deskripsi pergerakan kamera",
            "lighting": "deskripsi pencahayaan",
            "negative_prompt": "deskripsi negatif prompt"
        }}
        
        Pastikan setiap field diisi dengan deskripsi yang detail dan kreatif untuk menghasilkan gambar yang bagus.
        """
        
        # Generate AI response
        response = text_model.generate_content(ai_prompt)
        ai_response = response.text
        
        # Try to parse JSON from AI response
        try:
            # Extract JSON from response if it's wrapped in markdown
            if '```json' in ai_response:
                json_start = ai_response.find('```json') + 7
                json_end = ai_response.find('```', json_start)
                json_str = ai_response[json_start:json_end].strip()
            elif '```' in ai_response:
                json_start = ai_response.find('```') + 3
                json_end = ai_response.find('```', json_start)
                json_str = ai_response[json_start:json_end].strip()
            else:
                json_str = ai_response.strip()
            
            form_data = json.loads(json_str)
            
            # Generate enhanced prompt for image generation
            enhanced_prompt = f"""
            Buat prompt yang sangat detail dan kreatif untuk AI image generator berdasarkan informasi berikut:
            
            Subjek: {form_data.get('subject', '')}
            Aksi: {form_data.get('action', '')}
            Ekspresi: {form_data.get('expression', '')}
            Lokasi: {form_data.get('location', '')}
            Waktu: {form_data.get('time', '')}
            Sudut Kamera: {form_data.get('camera_angle', '')}
            Pergerakan Kamera: {form_data.get('camera_movement', '')}
            Pencahayaan: {form_data.get('lighting', '')}
            
            Buat prompt yang:
            1. Menggabungkan semua elemen dengan harmonis
            2. Menambahkan detail visual yang menarik
            3. Menggunakan bahasa yang deskriptif dan artistik
            4. Cocok untuk AI image generator
            5. Maksimal 150 kata
            
            Berikan hanya prompt final tanpa penjelasan tambahan.
            """
            
            enhanced_response = text_model.generate_content(enhanced_prompt)
            enhanced_prompt_text = enhanced_response.text.strip()
            
            return jsonify({
                'success': True,
                'form_data': form_data,
                'enhanced_prompt': enhanced_prompt_text,
                'ai_analysis': ai_response
            })
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return the raw AI response
            return jsonify({
                'success': True,
                'form_data': {
                    'subject': '',
                    'action': '',
                    'expression': '',
                    'location': '',
                    'time': '',
                    'camera_angle': '',
                    'camera_movement': '',
                    'lighting': '',
                    'negative_prompt': ''
                },
                'enhanced_prompt': user_input,
                'ai_analysis': ai_response,
                'parse_error': str(e)
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_routes.route('/generate-complete-image', methods=['POST'])
def generate_complete_image():
    """Generate image with auto-filled form data and enhanced prompt"""
    try:
        data = request.get_json()
        user_input = data.get('user_input', '').strip()
        
        if not user_input:
            return jsonify({'success': False, 'error': 'User input is required'}), 400
        
        # Create AI prompt to analyze user input and fill form fields
        ai_prompt = f"""
        Analisis input pengguna berikut dan isi form fields untuk AI image generator:
        
        Input pengguna: "{user_input}"
        
        Isi form fields berikut berdasarkan input di atas:
        1. subject (Subjek/Siapa/Apa) - karakter atau objek utama
        2. action (Aksi/Apa yang terjadi) - aktivitas atau gerakan
        3. expression (Ekspresi/Emosi) - perasaan atau ekspresi wajah
        4. location (Tempat/Latar belakang) - setting atau lokasi
        5. time (Waktu) - waktu hari atau suasana waktu
        6. camera_angle (Sudut kamera) - angle pengambilan gambar
        7. camera_movement (Pergerakan kamera) - gerakan kamera
        8. lighting (Pencahayaan) - jenis pencahayaan
        9. negative_prompt (Negatif Prompt) - hal yang harus dihindari
        
        Berikan jawaban dalam format JSON seperti ini:
        {{
            "subject": "deskripsi subjek",
            "action": "deskripsi aksi",
            "expression": "deskripsi ekspresi",
            "location": "deskripsi lokasi",
            "time": "deskripsi waktu",
            "camera_angle": "deskripsi sudut kamera",
            "camera_movement": "deskripsi pergerakan kamera",
            "lighting": "deskripsi pencahayaan",
            "negative_prompt": "deskripsi negatif prompt"
        }}
        
        Pastikan setiap field diisi dengan deskripsi yang detail dan kreatif untuk menghasilkan gambar yang bagus.
        """
        
        # Generate AI response
        response = text_model.generate_content(ai_prompt)
        ai_response = response.text
        
        # Try to parse JSON from AI response
        try:
            # Extract JSON from response if it's wrapped in markdown
            if '```json' in ai_response:
                json_start = ai_response.find('```json') + 7
                json_end = ai_response.find('```', json_start)
                json_str = ai_response[json_start:json_end].strip()
            elif '```' in ai_response:
                json_start = ai_response.find('```') + 3
                json_end = ai_response.find('```', json_start)
                json_str = ai_response[json_start:json_end].strip()
            else:
                json_str = ai_response.strip()
            
            form_data = json.loads(json_str)
            
            # Generate enhanced prompt for image generation
            enhanced_prompt = f"""
            Buat prompt yang sangat detail dan kreatif untuk AI image generator berdasarkan informasi berikut:
            
            Subjek: {form_data.get('subject', '')}
            Aksi: {form_data.get('action', '')}
            Ekspresi: {form_data.get('expression', '')}
            Lokasi: {form_data.get('location', '')}
            Waktu: {form_data.get('time', '')}
            Sudut Kamera: {form_data.get('camera_angle', '')}
            Pergerakan Kamera: {form_data.get('camera_movement', '')}
            Pencahayaan: {form_data.get('lighting', '')}
            
            Buat prompt yang:
            1. Menggabungkan semua elemen dengan harmonis
            2. Menambahkan detail visual yang menarik
            3. Menggunakan bahasa yang deskriptif dan artistik
            4. Cocok untuk AI image generator
            5. Maksimal 150 kata
            
            Berikan hanya prompt final tanpa penjelasan tambahan.
            """
            
            enhanced_response = text_model.generate_content(enhanced_prompt)
            enhanced_prompt_text = enhanced_response.text.strip()
            
            # Generate image using the enhanced prompt
            try:
                client = google_genai.Client()
                image_response = client.models.generate_content(
                    model="gemini-2.0-flash-preview-image-generation",
                    contents=enhanced_prompt_text,
                    config=genai_types.GenerateContentConfig(
                        response_modalities=['TEXT', 'IMAGE']
                    )
                )
                
                result_image_base64 = None
                
                for part in image_response.candidates[0].content.parts:
                    if getattr(part, 'inline_data', None) is not None:
                        image = PILImage.open(BytesIO(part.inline_data.data))
                        buffered = BytesIO()
                        image.save(buffered, format="PNG")
                        result_image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        break
                
                return jsonify({
                    'success': True,
                    'form_data': form_data,
                    'enhanced_prompt': enhanced_prompt_text,
                    'image_base64': result_image_base64,
                    'ai_analysis': ai_response
                })
                
            except Exception as image_error:
                # Fallback to text-only response if image generation fails
                return jsonify({
                    'success': True,
                    'form_data': form_data,
                    'enhanced_prompt': enhanced_prompt_text,
                    'image_base64': None,
                    'ai_analysis': ai_response,
                    'image_error': str(image_error)
                })
                
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return the raw AI response
            return jsonify({
                'success': True,
                'form_data': {
                    'subject': '',
                    'action': '',
                    'expression': '',
                    'location': '',
                    'time': '',
                    'camera_angle': '',
                    'camera_movement': '',
                    'lighting': '',
                    'negative_prompt': ''
                },
                'enhanced_prompt': user_input,
                'image_base64': None,
                'ai_analysis': ai_response,
                'parse_error': str(e)
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_routes.route('/generate-complete-prompt-and-image', methods=['POST'])
def generate_complete_prompt_and_image():
    try:
        data = request.get_json()
        user_input = data.get('user_input', '').strip()
        if not user_input:
            return jsonify({'success': False, 'error': 'User input is required'}), 400

        openai_api_key = current_app.config.get('OPENAI_API_KEY')
        if not openai_api_key:
            return jsonify({'success': False, 'error': 'OpenAI API key not configured'}), 500

        # 1. Generate prompt (Indonesia) via OpenAI ChatGPT
        def chatgpt_generate(prompt, lang='id'):
            if lang == 'id':
                sys_msg = "Buat prompt AI image generator yang sangat detail, kreatif, dan artistik dalam bahasa Indonesia."
                user_msg = prompt
            else:
                sys_msg = "You are an expert prompt engineer. No matter what the user input language is, always reply ONLY with a very detailed, creative, and artistic prompt for an AI image generator in ENGLISH. Do NOT translate, do NOT explain, do NOT use any other language except English."

                user_msg = prompt + " (Please reply in English only.)"
            messages = [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg}
            ]
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": messages,
                    "max_tokens": 300
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                print('ChatGPT error:', response.text)
                return None

        prompt_id = chatgpt_generate(user_input, lang='id')
        if not prompt_id or not prompt_id.strip():
            prompt_id = user_input

        prompt_en = chatgpt_generate(user_input, lang='en')
        if not prompt_en or not prompt_en.strip():
            prompt_en = user_input  

        # 2. Generate image via OpenAI DALL-E
        prompt_for_dalle = prompt_id[:300]
        dalle_payload = {
            "model": "dall-e-3",
            "prompt": prompt_for_dalle,
            "n": 1,
            "size": "1024x1024"
        }
        dalle_response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json=dalle_payload,
            timeout=60
        )
        if dalle_response.status_code == 200:
            dalle_result = dalle_response.json()
            if dalle_result.get('data') and len(dalle_result['data']) > 0:
                image_url = dalle_result['data'][0]['url']
            else:
                image_url = None
        else:
            error_msg = dalle_response.json().get('error', {}).get('message', 'Gagal generate gambar dari OpenAI.')
            print(f"OpenAI DALL-E error: {error_msg}")
            return jsonify({
                'success': False,
                'form_data': {},
                'generated_prompt_id': prompt_id,
                'generated_prompt_en': prompt_en,
                'image_url': None,
                'ai_analysis': '',
                'image_error': error_msg
            })

        response_data = {
            'success': True,
            'form_data': {},
            'generated_prompt_id': prompt_id,
            'generated_prompt_en': prompt_en,
            'image_url': image_url,
            'ai_analysis': ''
        }
        print(f"Response data keys: {list(response_data.keys())}")
        print(f"Image url in response: {response_data['image_url']}")
        return jsonify(response_data)
    except Exception as e:
        import traceback
        print("=== ERROR TRACEBACK ===")
        traceback.print_exc()
        print("=======================")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_routes.route('/generate-image-alternative', methods=['POST'])
def generate_image_alternative():
    """Alternative image generation using OpenAI DALL-E"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400
        
        # Use OpenAI DALL-E API for image generation
        openai_api_key = current_app.config.get('OPENAI_API_KEY')
        if not openai_api_key:
            return jsonify({'success': False, 'error': 'OpenAI API key not configured'}), 500
        
        openai_api_url = "https://api.openai.com/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024"
        }
        
        print(f"Trying OpenAI DALL-E with prompt: {prompt[:100]}...")
        response = requests.post(openai_api_url, headers=headers, json=payload, timeout=60)
        
        print(f"OpenAI DALL-E response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"OpenAI DALL-E response: {result}")
            if result.get('data') and len(result['data']) > 0:
                image_url = result['data'][0]['url']
                # Download the image and convert to base64
                img_response = requests.get(image_url)
                if img_response.status_code == 200:
                    image_base64 = base64.b64encode(img_response.content).decode('utf-8')
                    print("Image generated successfully with OpenAI DALL-E")
                    return jsonify({
                        'success': True,
                        'image_base64': image_base64,
                        'method': 'openai_dalle'
                    })
                else:
                    print("Failed to download image from OpenAI")
                    return jsonify({
                        'success': False,
                        'error': 'Failed to download generated image'
                    })
            else:
                print("No image data in OpenAI response")
                return jsonify({
                    'success': False,
                    'error': 'No image data in response'
                })
        else:
            print(f"OpenAI DALL-E error: {response.text}")
            return jsonify({
                'success': False,
                'error': f'OpenAI API error: {response.text}'
            })
            
    except Exception as e:
        print(f"Image generation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_routes.route('/songs', methods=['GET'])
def get_songs():
    """Return all songs for the logged-in user as JSON (user_id from session)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401
        songs = Song.query.filter_by(user_id=user_id).order_by(Song.created_at.desc()).all()
        result = []
        for song in songs:
            result.append({
                'id': song.id,
                'user_id': song.user_id,
                'title': song.title,
                'prompt': song.prompt,
                'model_name': song.model_name,
                'duration': song.duration,
                'image_url': song.image_url,
                'audio_url': song.audio_url,
                'stream_audio_url': song.stream_audio_url,
                'source_audio_url': song.source_audio_url,
                'source_image_url': song.source_image_url,
                'source_stream_audio_url': song.source_stream_audio_url,
                'created_at': song.created_at.strftime('%Y-%m-%d %H:%M') if song.created_at else None
            })
        return jsonify({'success': True, 'songs': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_routes.route('/songs/all', methods=['GET'])
def get_all_songs():
    """Return all songs in the database as JSON (tanpa filter user)"""
    try:
        songs = Song.query.order_by(Song.created_at.desc()).all()
        result = []
        for song in songs:
            result.append({
                'id': song.id,
                'user_id': song.user_id,
                'title': song.title,
                'prompt': song.prompt,
                'model_name': song.model_name,
                'duration': song.duration,
                'image_url': song.image_url,
                'audio_url': song.audio_url,
                'stream_audio_url': song.stream_audio_url,
                'source_audio_url': song.source_audio_url,
                'source_image_url': song.source_image_url,
                'source_stream_audio_url': song.source_stream_audio_url,
                'created_at': song.created_at.strftime('%Y-%m-%d %H:%M') if song.created_at else None
            })
        return jsonify({'success': True, 'songs': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_routes.route('/download_music/<song_id>')
def download_music(song_id):
    song = Song.query.get(song_id)
    if not song:
        return abort(404)
    audio_url = song.audio_url or song.source_audio_url
    if not audio_url:
        return abort(404)
    # Jika audio_url adalah URL eksternal (http/https), proxy download
    if audio_url.startswith('http://') or audio_url.startswith('https://'):
        try:
            r = requests.get(audio_url, stream=True, timeout=20)
            r.raise_for_status()
            headers = {
                'Content-Disposition': f'attachment; filename="{song.title or song.id}.mp3"',
                'Content-Type': r.headers.get('Content-Type', 'audio/mpeg')
            }
            return Response(r.iter_content(chunk_size=8192), headers=headers)
        except Exception as e:
            return abort(404)
    # Jika audio_url adalah path lokal (misal: /static/audio_results/xxx.mp3)
    if audio_url.startswith('/static/'):
        audio_url = audio_url[len('/static/'):]
    file_path = os.path.join(current_app.root_path, 'static', audio_url.replace('/', os.sep))
    if not os.path.isfile(file_path):
        return abort(404)
    return send_file(file_path, as_attachment=True)

# Chat Service Routes
@api_routes.route('/chat/generate-prompt', methods=['POST'])
def chat_generate_prompt():
    """Generate prompt menggunakan Gemini Flash untuk musik, video, atau foto"""
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    try:
        data = request.get_json()
        user_input = data.get('input', '').strip()
        prompt_type = data.get('type', 'music').lower()  # music, video, photo
        
        if not user_input:
            return jsonify({
                'success': False,
                'error': 'Input tidak boleh kosong'
            }), 400
        
        # Validasi tipe prompt
        if prompt_type not in ['music', 'video', 'photo']:
            return jsonify({
                'success': False,
                'error': 'Tipe prompt harus music, video, atau photo'
            }), 400
        
        # Dapatkan service instance
        prompt_service = get_prompt_service()
        
        # Generate prompt berdasarkan tipe
        result = prompt_service.generate_general_prompt(user_input, prompt_type)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"Error in chat_generate_prompt: {e}")
        return jsonify({
            'success': False,
            'error': f'Terjadi kesalahan: {str(e)}'
        }), 500

@api_routes.route('/chat/generate-music-prompt', methods=['POST'])
def chat_generate_music_prompt():
    """Generate prompt musik Suno yang akurat, support lampiran file"""
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    try:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            user_input = request.form.get('input', '').strip()
            files = request.files.getlist('attachments')
            file_urls = []
            for file in files:
                if file and file.filename:
                    save_dir = os.path.join('static', 'uploads')
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, file.filename)
                    file.save(save_path)
                    file_urls.append('/static/uploads/' + file.filename)
        else:
            data = request.get_json()
            user_input = data.get('input', '').strip()
            file_urls = []
        if not user_input and not file_urls:
            return jsonify({
                'success': False,
                'error': 'Input tidak boleh kosong'
            }), 400
        prompt_service = get_prompt_service()
        # Jika ingin, file_urls bisa diteruskan ke service
        result = prompt_service.generate_music_prompt(user_input, file_urls=file_urls) if file_urls else prompt_service.generate_music_prompt(user_input)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        print(f"Error in chat_generate_music_prompt: {e}")
        return jsonify({
            'success': False,
            'error': f'Terjadi kesalahan: {str(e)}'
        }), 500

@api_routes.route('/chat/generate-video-prompt', methods=['POST'])
def chat_generate_video_prompt():
    """Generate prompt video yang akurat, support lampiran file"""
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    try:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            user_input = request.form.get('input', '').strip()
            files = request.files.getlist('attachments')
            file_urls = []
            for file in files:
                if file and file.filename:
                    save_dir = os.path.join('static', 'uploads')
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, file.filename)
                    file.save(save_path)
                    file_urls.append('/static/uploads/' + file.filename)
        else:
            data = request.get_json()
            user_input = data.get('input', '').strip()
            file_urls = []
        if not user_input and not file_urls:
            return jsonify({
                'success': False,
                'error': 'Input tidak boleh kosong'
            }), 400
        prompt_service = get_prompt_service()
        result = prompt_service.generate_video_prompt(user_input, file_urls=file_urls) if file_urls else prompt_service.generate_video_prompt(user_input)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        print(f"Error in chat_generate_video_prompt: {e}")
        return jsonify({
            'success': False,
            'error': f'Terjadi kesalahan: {str(e)}'
        }), 500

@api_routes.route('/api/chat/generate-photo-prompt', methods=['POST'])
def chat_generate_photo_prompt():
    """Generate prompt foto yang akurat, support lampiran file dan judul gambar"""
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    try:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            user_input = request.form.get('input', '').strip()
            title = request.form.get('title', '').strip()
            prompt_type = request.form.get('type', 'image')
            files = request.files.getlist('attachments')
            file_urls = []
            for file in files:
                if file and file.filename:
                    save_dir = os.path.join('static', 'uploads')
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, file.filename)
                    file.save(save_path)
                    file_urls.append('/static/uploads/' + file.filename)
        else:
            data = request.get_json()
            user_input = data.get('input', '').strip()
            title = data.get('title', '').strip()
            prompt_type = data.get('type', 'image')
            # Support attachments dari JSON untuk fusigaya
            file_urls = data.get('attachments', []) if data.get('attachments') else []
        
        # Jika ada title, gunakan title sebagai input utama
        if title:
            user_input = title
        
        if not user_input and not file_urls:
            return jsonify({
                'success': False,
                'error': 'Input tidak boleh kosong'
            }), 400
        
        prompt_service = get_prompt_service()
        
        # Generate prompt berdasarkan type
        if prompt_type == 'fusigaya':
            # Untuk fusigaya, selalu kirim file_urls jika ada untuk analisis gambar
            result = prompt_service.generate_fusigaya_prompt(user_input, file_urls=file_urls)
        else:
            result = prompt_service.generate_photo_prompt(user_input, file_urls=file_urls) if file_urls else prompt_service.generate_photo_prompt(user_input)
        
        if result['success']:
            # Untuk fusigaya, tidak perlu negative prompt
            if prompt_type == 'fusigaya':
                combined_result = {
                    "success": True,
                    "prompt": result['prompt'],
                    "type": result['type'],
                    "original_input": user_input
                }
            else:
                # Generate negative prompt untuk image generation
                negative_result = prompt_service.generate_negative_prompt(user_input, prompt_type)
                combined_result = {
                    "success": True,
                    "prompt": result['prompt'],
                    "negative_prompt": negative_result.get('negative_prompt', '') if negative_result['success'] else '',
                    "type": result['type'],
                    "original_input": user_input
                }
            return jsonify(combined_result)
        else:
            return jsonify(result), 500
    except Exception as e:
        print(f"Error in chat_generate_photo_prompt: {e}")
        return jsonify({
            'success': False,
            'error': f'Terjadi kesalahan: {str(e)}'
        }), 500

@api_routes.route('/tts-elevenlabs', methods=['POST'])
def tts_elevenlabs():
    """Text-to-Speech menggunakan ElevenLabs API"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'Text tidak boleh kosong'
            }), 400
        
        # Bersihkan text dari karakter khusus yang tidak perlu dibaca
        import re
        # Hapus markdown formatting seperti **, *, _, #, dll
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Hapus **text**
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Hapus *text*
        text = re.sub(r'_(.*?)_', r'\1', text)        # Hapus _text_
        text = re.sub(r'#+\s*', '', text)             # Hapus heading #
        text = re.sub(r'`(.*?)`', r'\1', text)        # Hapus `code`
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # Hapus [link](url)
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)   # Hapus gambar
        text = re.sub(r'^\s*[-*+]\s*', '', text, flags=re.MULTILINE)  # Hapus list markers
        text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)  # Hapus numbered list
        
        # Hapus karakter khusus yang tidak perlu dibaca
        text = re.sub(r'[^\w\s\.,!?;:()\-]', '', text)
        
        # Bersihkan spasi berlebih
        text = re.sub(r'\s+', ' ', text).strip()
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'Text kosong setelah pembersihan'
            }), 400
        
        # Ambil API key dari config
        api_key = Config.ELEVENLABS_API_KEY
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'ElevenLabs API key tidak dikonfigurasi'
            }), 500
        
        # ElevenLabs API endpoint - menggunakan voice yang lebih cocok untuk bahasa Indonesia
        # Voice ID untuk bahasa Indonesia yang lebih natural - Rachel voice
        url = "https://api.elevenlabs.io/v1/text-to-speech/v70fYBHUOrHA3AKIBjPq"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",  # Model multilingual untuk bahasa Indonesia
            "voice_settings": {
                "stability": 0.7,        # Lebih stabil untuk bahasa Indonesia
                "similarity_boost": 0.75, # Boost similarity untuk suara yang lebih natural
                "style": 0.0,            # Style default
                "use_speaker_boost": True # Boost speaker untuk kejelasan
            }
        }
        
        # Kirim request ke ElevenLabs
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            # Return audio file sebagai response
            return Response(
                response.content,
                mimetype='audio/mpeg',
                headers={
                    'Content-Disposition': 'attachment; filename=tts_output.mp3'
                }
            )
        else:
            error_msg = f"ElevenLabs API error: {response.status_code}"
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', error_msg)
            except:
                pass
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
            
    except Exception as e:
        print(f"Error in tts_elevenlabs: {e}")
        return jsonify({
            'success': False,
            'error': f'Terjadi kesalahan: {str(e)}'
        }), 500

@api_routes.route('/chat/analyze-image-fusigaya', methods=['POST'])
def chat_analyze_image_fusigaya():
    """Analisis gambar untuk fusigaya dengan AI vision"""
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    try:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            user_input = request.form.get('input', '').strip()
            files = request.files.getlist('attachments')
            if not files or len(files) == 0:
                return jsonify({
                    'success': False,
                    'error': 'Gambar wajib diupload untuk analisis fusigaya'
                }), 400
            
            # Ambil gambar pertama
            file = files[0]
            if not file or not file.filename:
                return jsonify({
                    'success': False,
                    'error': 'File gambar tidak valid'
                }), 400
            
            # Convert gambar ke base64
            import base64
            file_content = file.read()
            base64_data = base64.b64encode(file_content).decode('utf-8')
            
        else:
            data = request.get_json()
            user_input = data.get('input', '').strip()
            image_base64 = data.get('image_base64', '')
            
            if not image_base64:
                return jsonify({
                    'success': False,
                    'error': 'Data gambar tidak valid'
                }), 400
            
            base64_data = image_base64
        
        if not user_input:
            return jsonify({
                'success': False,
                'error': 'Input tidak boleh kosong'
            }), 400
        
        prompt_service = get_prompt_service()
        result = prompt_service.analyze_image_for_fusigaya(base64_data, user_input)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"Error in chat_analyze_image_fusigaya: {e}")
        return jsonify({
            'success': False,
            'error': f'Terjadi kesalahan: {str(e)}'
        }), 500

@api_routes.route('/gallery/public', methods=['GET'])
def api_gallery_public():
    """Return latest images, videos, and music for public landing page (no login required)."""
    try:
        from models import Image, Video, Song, User
        
        # Get latest images (limit 10)
        images = Image.query.order_by(Image.created_at.desc()).limit(10).all()
        # Get latest videos (limit 5) 
        videos = Video.query.order_by(Video.created_at.desc()).limit(5).all()
        # Get latest songs (limit 20)
        songs = Song.query.order_by(Song.created_at.desc()).limit(20).all()

        items = []
        
        # Process images
        for img in images:
            user = User.query.get(img.user_id) if img.user_id else None
            items.append({
                'id': img.id,
                'type': 'image',
                'url': img.image_url,
                'image_url': img.image_url,
                'caption': img.caption,
                'title': img.caption,
                'user': user.username if user else 'Anonymous',
                'created_at': img.created_at.isoformat() if img.created_at else ''
            })
        
        # Process videos
        for vid in videos:
            user = User.query.get(vid.user_id) if vid.user_id else None
            items.append({
                'id': vid.id,
                'type': 'video',
                'url': vid.video_url,
                'image_url': '',
                'caption': vid.caption,
                'title': vid.caption,
                'user': user.username if user else 'Anonymous',
                'created_at': vid.created_at.isoformat() if vid.created_at else ''
            })
        
        # Process songs
        for song in songs:
            user = User.query.get(song.user_id) if song.user_id else None
            items.append({
                'id': song.id,
                'type': 'music',
                'url': song.audio_url,
                'image_url': song.image_url,
                'caption': song.prompt,
                'title': song.title,
                'user': user.username if user else 'Anonymous',
                'created_at': song.created_at.isoformat() if song.created_at else ''
            })
        
        # Sort all items by created_at desc
        items.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({'success': True, 'items': items})
        
    except Exception as e:
        print(f"Error in api_gallery_public: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@api_routes.route('/gallery/latest', methods=['GET'])
def api_gallery_latest():
    """Return at least 10 latest images and 5 latest videos (no music), sorted by created_at desc."""
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    from models import Image, Video, User
    images = Image.query.order_by(Image.created_at.desc()).limit(10).all()
    videos = Video.query.order_by(Video.created_at.desc()).limit(5).all()

    items = []
    for img in images:
        items.append({
            'id': img.id,
            'type': 'image',
            'url': img.image_url,
            'image_url': img.image_url,
            'caption': img.caption,
            'title': img.caption,
            'user': User.query.get(img.user_id).username if img.user_id else '',
            'created_at': img.created_at.isoformat() if img.created_at else ''
        })
    for vid in videos:
        items.append({
            'id': vid.id,
            'type': 'video',
            'url': vid.video_url,
            'image_url': '',
            'caption': vid.caption,
            'title': vid.caption,
            'user': User.query.get(vid.user_id).username if vid.user_id else '',
            'created_at': vid.created_at.isoformat() if vid.created_at else ''
        })
    # Sort all items by created_at desc
    items.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify({'success': True, 'items': items})

@api_routes.route('/gallery/infinite', methods=['GET'])
def api_gallery_infinite():
    """Return paginated gallery items for infinite scroll, sorted by created_at desc."""
    # Cek session user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    content_type = request.args.get('type', 'all')  # all, image, video, music, video_iklan
    

    
    from models import Image, Video, Song, User, Like, Comment, VideoIklan
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    all_media = []
    
    try:
        if content_type == 'all':
            # For 'all' type, we need to get items from all types and then sort
            # Get items from each type with larger limit to ensure we have enough after sorting
            items_per_type = per_page // 2  # Get more items per type to ensure variety
            
            # Get images
            images = Image.query.order_by(Image.created_at.desc()).offset(offset).limit(items_per_type).all()
            for img in images:
                likes_count = Like.query.filter_by(content_type='image', content_id=str(img.id)).count()
                comments_count = Comment.query.filter_by(content_type='image', content_id=str(img.id)).count()
                user = User.query.get(img.user_id)
                all_media.append({
                    'id': img.id,
                    'type': 'image',
                    'url': str(img.image_url) if img.image_url else '',
                    'caption': str(img.caption) if img.caption else '',
                    'created_at': img.created_at.isoformat() if img.created_at else '',
                    'user': {
                        'id': user.id,
                        'username': str(user.username) if user.username else '',
                        'avatar_url': str(user.avatar_url) if user.avatar_url else ''
                    } if user else None,
                    'likes_count': likes_count,
                    'comments_count': comments_count
                })
            
            # Get videos
            videos = Video.query.order_by(Video.created_at.desc()).offset(offset).limit(items_per_type).all()
            for vid in videos:
                likes_count = Like.query.filter_by(content_type='video', content_id=str(vid.id)).count()
                comments_count = Comment.query.filter_by(content_type='video', content_id=str(vid.id)).count()
                user = User.query.get(vid.user_id)
                all_media.append({
                    'id': vid.id,
                    'type': 'video',
                    'url': str(vid.video_url) if vid.video_url else '',
                    'caption': str(vid.caption) if vid.caption else '',
                    'created_at': vid.created_at.isoformat() if vid.created_at else '',
                    'user': {
                        'id': user.id,
                        'username': str(user.username) if user.username else '',
                        'avatar_url': str(user.avatar_url) if user.avatar_url else ''
                    } if user else None,
                    'likes_count': likes_count,
                    'comments_count': comments_count
                })
            
            # Get video_iklan
            videos_iklan = VideoIklan.query.order_by(VideoIklan.created_at.desc()).offset(offset).limit(items_per_type).all()
            for vid in videos_iklan:
                likes_count = Like.query.filter_by(content_type='video_iklan', content_id=str(vid.id)).count()
                comments_count = Comment.query.filter_by(content_type='video_iklan', content_id=str(vid.id)).count()
                user = User.query.get(vid.user_id)
                all_media.append({
                    'id': vid.id,
                    'type': 'video_iklan',
                    'url': str(vid.video_url) if vid.video_url else '',
                    'caption': str(vid.caption) if vid.caption else '',
                    'created_at': vid.created_at.isoformat() if vid.created_at else '',
                    'user': {
                        'id': user.id,
                        'username': str(user.username) if user.username else '',
                        'avatar_url': str(user.avatar_url) if user.avatar_url else ''
                    } if user else None,
                    'likes_count': likes_count,
                    'comments_count': comments_count
                })
            
            # Get songs
            songs = Song.query.order_by(Song.created_at.desc()).offset(offset).limit(items_per_type).all()
            for song in songs:
                likes_count = Like.query.filter_by(content_type='song', content_id=song.id).count()
                comments_count = Comment.query.filter_by(content_type='song', content_id=song.id).count()
                user = User.query.get(song.user_id)
                all_media.append({
                    'id': song.id,
                    'type': 'music',
                    'url': str(song.audio_url) if song.audio_url else '',
                    'image_url': str(song.image_url) if song.image_url else '',
                    'title': str(song.title) if song.title else '',
                    'caption': str(song.prompt) if song.prompt else '',
                    'created_at': song.created_at.isoformat() if song.created_at else '',
                    'user': {
                        'id': user.id,
                        'username': str(user.username) if user.username else '',
                        'avatar_url': str(user.avatar_url) if user.avatar_url else ''
                    } if user else None,
                    'likes_count': likes_count,
                    'comments_count': comments_count
                })
        else:
            # For specific content types, use normal pagination
            if content_type == 'image':
                images = Image.query.order_by(Image.created_at.desc()).offset(offset).limit(per_page).all()
                for img in images:
                    likes_count = Like.query.filter_by(content_type='image', content_id=str(img.id)).count()
                    comments_count = Comment.query.filter_by(content_type='image', content_id=str(img.id)).count()
                    user = User.query.get(img.user_id)
                    all_media.append({
                        'id': img.id,
                        'type': 'image',
                        'url': str(img.image_url) if img.image_url else '',
                        'caption': str(img.caption) if img.caption else '',
                        'created_at': img.created_at.isoformat() if img.created_at else '',
                        'user': {
                            'id': user.id,
                            'username': str(user.username) if user.username else '',
                            'avatar_url': str(user.avatar_url) if user.avatar_url else ''
                        } if user else None,
                        'likes_count': likes_count,
                        'comments_count': comments_count
                    })
            
            elif content_type == 'video':
                videos = Video.query.order_by(Video.created_at.desc()).offset(offset).limit(per_page).all()
                for vid in videos:
                    likes_count = Like.query.filter_by(content_type='video', content_id=str(vid.id)).count()
                    comments_count = Comment.query.filter_by(content_type='video', content_id=str(vid.id)).count()
                    user = User.query.get(vid.user_id)
                    all_media.append({
                        'id': vid.id,
                        'type': 'video',
                        'url': str(vid.video_url) if vid.video_url else '',
                        'caption': str(vid.caption) if vid.caption else '',
                        'created_at': vid.created_at.isoformat() if vid.created_at else '',
                        'user': {
                            'id': user.id,
                            'username': str(user.username) if user.username else '',
                            'avatar_url': str(user.avatar_url) if user.avatar_url else ''
                        } if user else None,
                        'likes_count': likes_count,
                        'comments_count': comments_count
                    })
            
            elif content_type == 'video_iklan':
                videos_iklan = VideoIklan.query.order_by(VideoIklan.created_at.desc()).offset(offset).limit(per_page).all()
                for vid in videos_iklan:
                    likes_count = Like.query.filter_by(content_type='video_iklan', content_id=str(vid.id)).count()
                    comments_count = Comment.query.filter_by(content_type='video_iklan', content_id=str(vid.id)).count()
                    user = User.query.get(vid.user_id)
                    all_media.append({
                        'id': vid.id,
                        'type': 'video_iklan',
                        'url': str(vid.video_url) if vid.video_url else '',
                        'caption': str(vid.caption) if vid.caption else '',
                        'created_at': vid.created_at.isoformat() if vid.created_at else '',
                        'user': {
                            'id': user.id,
                            'username': str(user.username) if user.username else '',
                            'avatar_url': str(user.avatar_url) if user.avatar_url else ''
                        } if user else None,
                        'likes_count': likes_count,
                        'comments_count': comments_count
                    })
            
            elif content_type == 'music':
                songs = Song.query.order_by(Song.created_at.desc()).offset(offset).limit(per_page).all()
                for song in songs:
                    likes_count = Like.query.filter_by(content_type='song', content_id=song.id).count()
                    comments_count = Comment.query.filter_by(content_type='song', content_id=song.id).count()
                    user = User.query.get(song.user_id)
                    all_media.append({
                        'id': song.id,
                        'type': 'music',
                        'url': str(song.audio_url) if song.audio_url else '',
                        'image_url': str(song.image_url) if song.image_url else '',
                        'title': str(song.title) if song.title else '',
                        'caption': str(song.prompt) if song.prompt else '',
                        'created_at': song.created_at.isoformat() if song.created_at else '',
                        'user': {
                            'id': user.id,
                            'username': str(user.username) if user.username else '',
                            'avatar_url': str(user.avatar_url) if user.avatar_url else ''
                        } if user else None,
                        'likes_count': likes_count,
                        'comments_count': comments_count
                    })
    
    except Exception as e:
        print(f"Error in api_gallery_infinite: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    
    # Sort all items by created_at desc to ensure newest first
    all_media.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Check if there are more items by querying the next page
    next_offset = offset + per_page
    has_more = False
    
    if content_type == 'all':
        # For 'all' type, check if any type has more items
        next_images = Image.query.order_by(Image.created_at.desc()).offset(next_offset).limit(1).all()
        next_videos = Video.query.order_by(Video.created_at.desc()).offset(next_offset).limit(1).all()
        next_videos_iklan = VideoIklan.query.order_by(VideoIklan.created_at.desc()).offset(next_offset).limit(1).all()
        next_songs = Song.query.order_by(Song.created_at.desc()).offset(next_offset).limit(1).all()
        
        if next_images or next_videos or next_videos_iklan or next_songs:
            has_more = True
    else:
        # For specific content types
        if content_type == 'image':
            next_images = Image.query.order_by(Image.created_at.desc()).offset(next_offset).limit(1).all()
            if next_images:
                has_more = True
        elif content_type == 'video':
            next_videos = Video.query.order_by(Video.created_at.desc()).offset(next_offset).limit(1).all()
            if next_videos:
                has_more = True
        elif content_type == 'video_iklan':
            next_videos_iklan = VideoIklan.query.order_by(VideoIklan.created_at.desc()).offset(next_offset).limit(1).all()
            if next_videos_iklan:
                has_more = True
        elif content_type == 'music':
            next_songs = Song.query.order_by(Song.created_at.desc()).offset(next_offset).limit(1).all()
            if next_songs:
                has_more = True
    

    
    return jsonify({
        'success': True, 
        'items': all_media,
        'page': page,
        'per_page': per_page,
        'has_more': has_more,
        'total_items': len(all_media)
    })
