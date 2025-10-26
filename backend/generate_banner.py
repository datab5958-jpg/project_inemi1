import os
import requests
import json
import time
import uuid
from flask import Blueprint, render_template, request, jsonify, session, current_app, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from models import db, User, Image
import base64
from io import BytesIO

# Banner Type Definitions - Smart Banner Generation System
BANNER_TYPES = {
    "banner": {
        "name": "Banner",
        "description": "Banner standar untuk indoor/outdoor",
        "default_size": {"width": 2.0, "height": 1.0},
        "aspect_ratios": [2.0, 2.5, 3.0],
        "use_cases": ["indoor", "outdoor", "events"],
        "quality_level": "high",
        "model_preference": "nano-banana",
        "dpi": 300,
        "style_keywords": ["professional", "clean", "business", "modern"]
    },
    "spanduk": {
        "name": "Spanduk",
        "description": "Spanduk panjang untuk jalan raya",
        "default_size": {"width": 3.0, "height": 1.0},
        "aspect_ratios": [3.0, 4.0, 5.0],
        "use_cases": ["highway", "street", "promotion"],
        "quality_level": "ultra",
        "model_preference": "nano-banana",
        "dpi": 300,
        "style_keywords": ["bold", "eye-catching", "highway", "promotional"]
    },
    "baliho": {
        "name": "Baliho",
        "description": "Baliho besar untuk billboard",
        "default_size": {"width": 4.0, "height": 3.0},
        "aspect_ratios": [1.33, 1.5, 1.77],
        "use_cases": ["billboard", "highway", "city"],
        "quality_level": "premium",
        "model_preference": "nano-banana",
        "dpi": 300,
        "style_keywords": ["large", "impactful", "billboard", "city"]
    }
}

# Try to import optional dependencies
try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL not available, some features will be limited")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("OpenCV not available, color detection will be limited")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Tesseract not available, text detection will be limited")

try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Scikit-learn not available, color clustering will be limited")

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ReportLab not available, PDF generation will be limited")

load_dotenv()

# Create blueprint
generate_banner_bp = Blueprint('generate_banner', __name__)

# Allowed file extensions for banner images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_banner_credits(title_length, has_example_banner=False, extra_files_count=0):
    """Calculate credits needed for banner generation"""
    # Base credits for banner generation
    base_credits = 20
    
    # Additional credits based on title length
    title_credits = min(title_length // 20, 10)  # Max 10 credits for title
    
    # Additional credits for example banner analysis
    analysis_credits = 15 if has_example_banner else 0
    
    # Additional credits for extra files processing
    extra_credits = extra_files_count * 5  # 5 credits per extra file
    
    total_credits = base_credits + title_credits + analysis_credits + extra_credits
    return total_credits

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

def generate_smart_prompt(title, banner_type="banner", detected_info=None):
    """Generate smart prompt based on banner type and detected information"""
    try:
        # Get banner type configuration
        banner_config = BANNER_TYPES.get(banner_type, BANNER_TYPES["banner"])
        
        # Extract information
        if detected_info:
            width_m = detected_info.get('width_m', banner_config["default_size"]["width"])
            height_m = detected_info.get('height_m', banner_config["default_size"]["height"])
            colors = detected_info.get('dominant_colors', ['#007BFF', '#FFFFFF'])
            detected_text = detected_info.get('detected_text', '')
        else:
            width_m = banner_config["default_size"]["width"]
            height_m = banner_config["default_size"]["height"]
            colors = ['#007BFF', '#FFFFFF']
            detected_text = ''
        
        # Generate type-specific prompt
        if banner_type == "spanduk":
            prompt = f"""Create a clean, print-ready spanduk design with main text: '{title}'.
            Dimensions: {width_m} x {height_m} meters (highway spanduk size).
            Style: Bold, eye-catching promotional design for highway visibility.
            Color scheme: {', '.join(colors)}.
            {f'Reference text from example: {detected_text}' if detected_text else ''}
            Layout: 
            - Company logo positioned at top-left corner
            - Main title text centered, EXTRA LARGE and bold for highway visibility
            - QR code positioned at bottom-right corner
            - Bold, high-contrast design with maximum readability
            Typography: Extra bold sans-serif fonts, maximum readability from distance
            Background: High-contrast solid color or gradient, NO decorative patterns
            Quality: Ultra-high resolution, print-ready, {banner_config['dpi']}+ DPI quality
            Format: Clean spanduk design suitable for direct printing on vinyl or fabric
            IMPORTANT: This is a SPANDUK DESIGN, NOT a billboard simulation. Do NOT include:
            - Billboard structure or frame
            - Poles or mounting hardware
            - Urban background or environment
            - Lighting fixtures or spotlights
            - Any 3D elements or perspective
            The design should be a flat, clean spanduk ready for printing, not a billboard display."""
            
        elif banner_type == "baliho":
            prompt = f"""Create a clean, print-ready baliho design with main text: '{title}'.
            Dimensions: {width_m} x {height_m} meters (large billboard size).
            Style: Premium, impactful design for city advertising.
            Color scheme: {', '.join(colors)}.
            {f'Reference text from example: {detected_text}' if detected_text else ''}
            Layout: 
            - Company logo positioned at top-left corner
            - Main title text centered, LARGE and impactful for billboard visibility
            - QR code positioned at bottom-right corner
            - Premium design with sophisticated layout
            Typography: Bold, professional fonts with excellent readability
            Background: Clean solid color or premium gradient, NO decorative patterns
            Quality: Premium resolution, print-ready, {banner_config['dpi']}+ DPI quality
            Format: Clean baliho design suitable for direct printing on vinyl or fabric
            IMPORTANT: This is a BALIHO DESIGN, NOT a billboard simulation. Do NOT include:
            - Billboard structure or frame
            - Poles or mounting hardware
            - Urban background or environment
            - Lighting fixtures or spotlights
            - Any 3D elements or perspective
            The design should be a flat, clean baliho ready for printing, not a billboard display."""
            
        else:  # banner
            prompt = f"""Create a clean, print-ready banner design with main text: '{title}'.
            Dimensions: {width_m} x {height_m} meters (standard banner size).
            Style: Clean, professional banner design for direct printing.
            Color scheme: {', '.join(colors)}.
            {f'Reference text from example: {detected_text}' if detected_text else ''}
            Layout: 
            - Company logo positioned at top-left corner
            - Main title text centered, large and bold
            - QR code positioned at bottom-right corner
            - Clean, minimal design with plenty of white space
            Typography: Professional sans-serif fonts, excellent readability
            Background: Solid color background or subtle gradient, NO decorative patterns
            Quality: High resolution, print-ready, {banner_config['dpi']}+ DPI quality
            Format: Clean banner design suitable for direct printing on vinyl or fabric
            IMPORTANT: This is a BANNER DESIGN, NOT a billboard simulation. Do NOT include:
            - Billboard structure or frame
            - Poles or mounting hardware
            - Urban background or environment
            - Lighting fixtures or spotlights
            - Any 3D elements or perspective
            The design should be a flat, clean banner ready for printing, not a billboard display."""
        
        print(f"🎯 Generated smart prompt for {banner_type}: {banner_config['name']}")
        print(f"📐 Size: {width_m}x{height_m}m, Quality: {banner_config['quality_level']}")
        print(f"🖨️ Output: Clean print-ready design (NO billboard structure)")
        return prompt
        
    except Exception as e:
        print(f"Error generating smart prompt: {str(e)}")
        # Fallback to basic prompt
        return f"Create a professional banner design with main text: '{title}'."

def detect_banner_info(image_path):
    """Deteksi ukuran, warna, dan teks dari banner contoh"""
    try:
        if not PIL_AVAILABLE:
            print("PIL not available, using default banner info")
            return {
                "width_m": 2.0,
                "height_m": 1.0,
                "dominant_colors": ["#007BFF", "#FFFFFF", "#FFD700"],
                "detected_text": "",
                "aspect_ratio": "2:1",
                "original_size": "2048x1024"
            }
        
        # Load image
        img = PILImage.open(image_path)
        width, height = img.size
        aspect_ratio = round(width / height, 2)
        
        # Estimasi ukuran real berdasarkan aspect ratio (standar banner)
        if aspect_ratio >= 3.0:
            est_width_m = 3.0
            est_height_m = 1.0
        elif aspect_ratio >= 2.5:
            est_width_m = 2.5
            est_height_m = 1.0
        elif aspect_ratio >= 2.0:
            est_width_m = 2.0
            est_height_m = 1.0
        elif aspect_ratio >= 1.5:
            est_width_m = 1.5
            est_height_m = 1.0
        elif aspect_ratio >= 1.0:
            est_width_m = 1.0
            est_height_m = 1.0
        else:
            # Portrait banner
            est_width_m = 1.0
            est_height_m = 1.5
        
        # Deteksi warna dominan
        colors = ["#007BFF", "#FFFFFF", "#FFD700"]  # Default colors
        if CV2_AVAILABLE and SKLEARN_AVAILABLE:
            try:
                img_cv = cv2.imread(image_path)
                img_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
                pixels = img_cv.reshape((-1, 3))
                
                # K-means clustering untuk warna dominan
                kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
                kmeans.fit(pixels)
                colors = []
                for center in kmeans.cluster_centers_:
                    r, g, b = center.astype(int)
                    colors.append(f"#{r:02x}{g:02x}{b:02x}")
            except Exception as e:
                print(f"Error in color detection: {str(e)}")
        
        # OCR untuk deteksi teks
        detected_text = ""
        if TESSERACT_AVAILABLE:
            try:
                detected_text = pytesseract.image_to_string(image_path, lang="eng+ind").strip()
            except Exception as e:
                print(f"Error in text detection: {str(e)}")
        
        return {
            "width_m": est_width_m,
            "height_m": est_height_m,
            "dominant_colors": colors[:3],  # Ambil 3 warna dominan
            "detected_text": detected_text,
            "aspect_ratio": f"{aspect_ratio}:1",
            "original_size": f"{width}x{height}"
        }
    except Exception as e:
        print(f"Error detecting banner info: {str(e)}")
        return {
            "width_m": 2.0,
            "height_m": 1.0,
            "dominant_colors": ["#007BFF", "#FFFFFF", "#FFD700"],
            "detected_text": "",
            "aspect_ratio": "2:1",
            "original_size": "2048x1024"
        }

def generate_banner_with_banana_ai(prompt, model="nano-banana"):
    """Generate banner menggunakan Banana AI via WaveSpeed"""
    try:
        API_KEY = os.getenv("WAVESPEED_API_KEY")
        if not API_KEY:
            raise Exception("API key not configured")
        
        # Model URLs untuk Banana AI
        model_urls = {
            'nano-banana': "https://api.wavespeed.ai/api/v3/google/nano-banana/text-to-image",
            'flux-kontext-dev': "https://api.wavespeed.ai/api/v3/wavespeed-ai/flux-kontext-dev/multi-ultra-fast",
            'flux-kontext-pro': "https://api.wavespeed.ai/api/v3/wavespeed-ai/flux-kontext-pro/multi"
        }
        
        url = model_urls.get(model, model_urls['nano-banana'])
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }
        
        payload = {
            "enable_base64_output": False,
            "enable_sync_mode": False,
            "output_format": "png",
            "prompt": prompt
        }
        
        print(f"Making request to {model} for banner generation")
        print(f"Prompt: {prompt}")
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            if "data" in result and "id" in result["data"]:
                request_id = result["data"]["id"]
                print(f"Banner generation started. Request ID: {request_id}")
                return request_id
            else:
                raise Exception("Invalid response format")
        else:
            error_msg = f"API request failed with status {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg = error_data['error']
                elif 'message' in error_data:
                    error_msg = error_data['message']
            except:
                error_msg = response.text or error_msg
            raise Exception(error_msg)
            
    except Exception as e:
        print(f"Error generating banner: {str(e)}")
        raise e

def check_banner_status(request_id):
    """Check status of banner generation"""
    try:
        API_KEY = os.getenv("WAVESPEED_API_KEY")
        if not API_KEY:
            raise Exception("API key not configured")
        
        url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Status check response: {result}")
            
            if "data" in result:
                data = result["data"]
                status = data.get("status")
                
                if status == "completed" and "outputs" in data and len(data["outputs"]) > 0:
                    return data["outputs"][0]  # Return the first output URL
                elif status == "failed":
                    error_msg = data.get("error", "Generation failed")
                    # Handle specific NSFW error
                    if "sensitive" in error_msg.lower() or "nsfw" in error_msg.lower():
                        raise Exception("Konten dianggap tidak pantas oleh AI. Silakan gunakan judul yang lebih profesional dan sesuai bisnis.")
                    else:
                        raise Exception(f"Banner generation failed: {error_msg}")
                else:
                    # Still processing
                    return None
            else:
                return None
        else:
            print(f"Status check failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error checking banner status: {str(e)}")
        return None

def overlay_uploaded_images(base_image_url, overlay_files):
    """Gabungkan beberapa logo/gambar di atas banner hasil AI"""
    try:
        if not PIL_AVAILABLE:
            print("PIL not available, skipping overlay")
            return None
            
        # Download base image
        response = requests.get(base_image_url)
        base_img = PILImage.open(BytesIO(response.content)).convert("RGBA")
        
        for i, overlay_file in enumerate(overlay_files):
            try:
                # Save uploaded file temporarily
                filename = secure_filename(overlay_file.filename)
                temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"temp_{uuid.uuid4().hex}_{filename}")
                overlay_file.save(temp_path)
                
                # Open and resize overlay
                logo = PILImage.open(temp_path).convert("RGBA")
                logo.thumbnail((200, 200), PILImage.Resampling.LANCZOS)
                
                # Calculate position (distribute logos across the banner)
                x_offset = 50 + (i * 250)  # 50px margin, 250px spacing
                y_offset = base_img.height - logo.height - 50  # Bottom margin
                
                # Ensure logo doesn't go outside banner
                if x_offset + logo.width > base_img.width:
                    x_offset = base_img.width - logo.width - 50
                
                # Paste logo with transparency
                base_img.paste(logo, (x_offset, y_offset), logo)
                
                # Clean up temp file
                os.remove(temp_path)
                
            except Exception as e:
                print(f"Error processing overlay {i}: {str(e)}")
                continue
        
        # Save final image
        output_filename = f"banner_final_{uuid.uuid4().hex}.png"
        output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], output_filename)
        base_img.save(output_path, "PNG")
        
        return output_path
        
    except Exception as e:
        print(f"Error overlaying images: {str(e)}")
        return None

def convert_to_pdf(image_path, width_m, height_m, dpi=1000):
    """Konversi hasil banner ke PDF siap cetak dengan kualitas terbaik"""
    try:
        if not REPORTLAB_AVAILABLE:
            print("ReportLab not available, PDF generation disabled")
            return None
        
        # Use ultra high DPI for Canva-quality professional printing
        print(f"Creating Canva-quality PDF with {dpi} DPI for {width_m}x{height_m}m banner")
        print(f"Target: Professional print-ready output like Canva - FULL PAGE")
        
        # Calculate PDF dimensions in points (1 inch = 72 points)
        width_pt = width_m * 100 * dpi / 2.54  # Convert meters to points
        height_pt = height_m * 100 * dpi / 2.54
        
        print(f"PDF dimensions: {width_pt:.2f} x {height_pt:.2f} points")
        
        # Create PDF with high quality settings
        pdf_filename = f"banner_canva_quality_{uuid.uuid4().hex}.pdf"
        pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_filename)
        
        # Create canvas with custom page size
        c = canvas.Canvas(pdf_path, pagesize=(width_pt, height_pt))
        
        # Draw image with high quality settings - FULL PAGE
        c.drawImage(
            image_path, 
            0, 0, 
            width=width_pt, 
            height=height_pt,
            preserveAspectRatio=False,  # FALSE untuk full page
            mask='auto',
            anchor='sw'  # Anchor at bottom-left for consistent positioning
        )
        
        # Add professional metadata for high-quality printing
        c.setTitle(f"Professional Banner {width_m}x{height_m}m - {dpi}DPI")
        c.setSubject("High-Quality Print-Ready Banner Design")
        c.setAuthor("INEMI AI Banner Generator")
        c.setKeywords("banner, advertising, print-ready, high-quality, canva-quality")
        c.setCreator("INEMI AI Banner Generator v2.0")
        
        c.save()
        
        print(f"✅ Canva-quality PDF created successfully: {pdf_path}")
        print(f"📄 PDF ready for professional printing at {dpi} DPI - FULL PAGE")
        print(f"🎯 Quality level: Canva professional standard - FULL PAGE")
        return pdf_path
        
    except Exception as e:
        print(f"Error converting to PDF: {str(e)}")
        return None

def create_billboard_simulation_with_ai(banner_url, model="nano-banana"):
    """Buat simulasi billboard menggunakan AI edit mode"""
    try:
        API_KEY = os.getenv("WAVESPEED_API_KEY")
        if not API_KEY:
            raise Exception("API key not configured")
        
        # URL untuk edit mode
        url = "https://api.wavespeed.ai/api/v3/google/nano-banana/edit"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }
        
        # Prompt untuk membuat simulasi billboard yang realistis
        prompt = """Transform this banner into a realistic billboard simulation. Create a professional outdoor advertising display with:
        - Modern metal billboard frame structure
        - Urban city background (street, buildings, or highway)
        - Realistic perspective and depth of field
        - Natural lighting and shadows
        - Professional outdoor advertising appearance
        - The banner should be clearly visible, well-lit, and properly mounted
        - High quality, photorealistic rendering
        - Billboard should look like a real outdoor advertising installation"""
        
        payload = {
            "enable_base64_output": False,
            "enable_sync_mode": False,
            "images": [banner_url],
            "output_format": "jpeg",
            "prompt": prompt
        }
        
        print(f"Creating billboard simulation with AI")
        print(f"Banner URL: {banner_url}")
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            if "data" in result and "id" in result["data"]:
                request_id = result["data"]["id"]
                print(f"Billboard simulation started. Request ID: {request_id}")
                return request_id
            else:
                raise Exception("Invalid response format for billboard simulation")
        else:
            error_msg = f"API request failed with status {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg = error_data['error']
                elif 'message' in error_data:
                    error_msg = error_data['message']
            except:
                error_msg = response.text or error_msg
            raise Exception(error_msg)
            
    except Exception as e:
        print(f"Error creating billboard simulation with AI: {str(e)}")
        raise e

def create_billboard_simulation(banner_path, billboard_template_path=None):
    """Buat simulasi banner di billboard (fallback method)"""
    try:
        if not PIL_AVAILABLE:
            print("PIL not available, skipping billboard simulation")
            return None
            
        # Load banner
        banner = PILImage.open(banner_path).convert("RGBA")
        
        # Create billboard background (simple gradient)
        billboard_width = 800
        billboard_height = 600
        
        # Create gradient background
        billboard = PILImage.new('RGB', (billboard_width, billboard_height), color='#87CEEB')
        
        # Resize banner to fit billboard
        banner.thumbnail((billboard_width - 100, billboard_height - 100), PILImage.Resampling.LANCZOS)
        
        # Center banner on billboard
        x_offset = (billboard_width - banner.width) // 2
        y_offset = (billboard_height - banner.height) // 2
        
        # Paste banner
        billboard.paste(banner, (x_offset, y_offset), banner)
        
        # Save simulation
        sim_filename = f"billboard_sim_{uuid.uuid4().hex}.png"
        sim_path = os.path.join(current_app.config['UPLOAD_FOLDER'], sim_filename)
        billboard.save(sim_path, "PNG")
        
        return sim_path
        
    except Exception as e:
        print(f"Error creating billboard simulation: {str(e)}")
        return None

@generate_banner_bp.route('/generate_banner')
def generate_banner_page():
    """Halaman Generate Banner"""
    if 'user_id' not in session:
        return redirect(url_for('web_pages.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('web_pages.login'))
    
    return render_template('generate_banner.html', user=user)

@generate_banner_bp.route('/smart_banner', methods=['POST'])
def smart_banner():
    """Handle smart banner generation request"""
    try:
        # Check user authentication
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User belum login'}), 401
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User tidak ditemukan'}), 404
        
        # Get title from request (handle both JSON and form data)
        try:
            if request.is_json:
                title = request.json.get('title', 'Banner AI Otomatis').strip()
                print(f"📝 Received JSON request with title: {title}")
            else:
                title = request.form.get('title', 'Banner AI Otomatis').strip()
                print(f"📝 Received FormData request with title: {title}")
        except Exception as e:
            print(f"⚠️ Error parsing title: {str(e)}")
            return jsonify({'error': 'Error parsing request data'}), 400
        
        if not title:
            return jsonify({'error': 'Judul banner harus diisi'}), 400
        
        # Basic NSFW content validation
        nsfw_keywords = ['adult', 'explicit', 'nude', 'sexual', 'porn', 'xxx', 'nsfw', '18+', 'adult content']
        title_lower = title.lower()
        for keyword in nsfw_keywords:
            if keyword in title_lower:
                return jsonify({'error': 'Judul banner mengandung konten yang tidak pantas. Silakan gunakan judul yang lebih profesional.'}), 400
        
        # Get uploaded files
        uploaded_files = request.files.getlist('files')
        print(f"📁 Received {len(uploaded_files)} files")
        
        # Separate banner example and extra files
        banner_contoh = None
        extra_files = []
        
        for f in uploaded_files:
            if f.filename and allowed_file(f.filename):
                if 'contoh' in f.filename.lower() or 'example' in f.filename.lower():
                    banner_contoh = f
                else:
                    extra_files.append(f)
        
        # Calculate required credits
        required_credits = calculate_banner_credits(
            len(title), 
            has_example_banner=(banner_contoh is not None),
            extra_files_count=len(extra_files)
        )
        
        # Check and deduct credits
        if user.kredit < required_credits:
            return jsonify({
                'error': f'Kredit Anda tidak cukup untuk generate banner (minimal {required_credits} kredit)'
            }), 403
        
        if not deduct_credits(user_id, required_credits):
            return jsonify({'error': 'Gagal mengurangi kredit'}), 500
        
        # Process banner example if provided
        detected_info = None
        if banner_contoh:
            try:
                # Save banner example
                filename = secure_filename(banner_contoh.filename)
                banner_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"banner_example_{uuid.uuid4().hex}_{filename}")
                banner_contoh.save(banner_path)
                
                # Detect banner info
                detected_info = detect_banner_info(banner_path)
                print(f"Detected banner info: {detected_info}")
                
            except Exception as e:
                print(f"Error processing banner example: {str(e)}")
                detected_info = None
        
        # Get banner type from request (handle both JSON and form data)
        try:
            if request.is_json:
                banner_type = request.json.get('banner_type', 'banner')
                print(f"📝 Received JSON request with banner_type: {banner_type}")
            else:
                banner_type = request.form.get('banner_type', 'banner')
                print(f"📝 Received FormData request with banner_type: {banner_type}")
        except Exception as e:
            print(f"⚠️ Error parsing request data: {str(e)}")
            banner_type = 'banner'  # Default fallback
        
        # Validate banner type
        if banner_type not in BANNER_TYPES:
            banner_type = 'banner'
        
        # Generate smart prompt based on banner type
        prompt = generate_smart_prompt(title, banner_type, detected_info)
        
        # Get banner configuration for quality settings
        banner_config = BANNER_TYPES[banner_type]
        print(f"🎨 Using banner type: {banner_config['name']} ({banner_type})")
        print(f"⚡ Quality level: {banner_config['quality_level']}")
        print(f"🤖 Model preference: {banner_config['model_preference']}")
        
        # Generate banner with nano-banana for super realistic results
        print(f"Generating banner with nano-banana model for super realistic results")
        print(f"Prompt: {prompt}")
        try:
            request_id = generate_banner_with_banana_ai(prompt, model="nano-banana")
            print(f"✅ Using nano-banana model for superior quality banner generation")
        except Exception as e:
            print(f"❌ Error with nano-banana model: {str(e)}")
            # Fallback to default model
            request_id = generate_banner_with_banana_ai(prompt)
            print(f"⚠️ Fallback to default model")
        
        # Return processing status
        return jsonify({
            'success': True,
            'status': 'processing',
            'request_id': request_id,
            'message': 'Banner generation started. Please wait...',
            'detected_info': detected_info,
            'credits_used': required_credits
        })
        
    except Exception as e:
        print(f"Error in smart_banner: {str(e)}")
        return jsonify({'error': f'Terjadi kesalahan: {str(e)}'}), 500

@generate_banner_bp.route('/check_banner_status/<request_id>')
def check_banner_status_endpoint(request_id):
    """Check status of banner generation"""
    try:
        # Check user authentication
        if 'user_id' not in session:
            return jsonify({'error': 'User belum login'}), 401
        
        user_id = session.get('user_id')
        print(f"🔍 Checking banner status for user_id: {user_id}, request_id: {request_id}")
        
        # Get title from request parameters or use default
        title = request.args.get('title', 'Generated Banner')
        print(f"📝 Banner title: {title}")
        
        # Check banner status
        banner_url = check_banner_status(request_id)
        
        if banner_url:
            # Banner completed, process it
            try:
                # Download and save banner
                response = requests.get(banner_url)
                banner_filename = f"banner_{uuid.uuid4().hex}.png"
                banner_path = os.path.join(current_app.config['UPLOAD_FOLDER'], banner_filename)
                
                with open(banner_path, 'wb') as f:
                    f.write(response.content)
                
                # Get domain for URL generation
                domain_public = current_app.config.get('DOMAIN_PUBLIC', 'http://127.0.0.1:5000')
                banner_url_local = f"{domain_public}/static/uploads/{banner_filename}"
                
                # Create billboard simulation using AI
                sim_url = None
                sim_request_id = None
                try:
                    # Create AI billboard simulation
                    sim_request_id = create_billboard_simulation_with_ai(banner_url)
                    print(f"Billboard simulation request ID: {sim_request_id}")
                    
                    # Store simulation request ID for polling
                    # For now, return the request ID so frontend can poll for completion
                    
                except Exception as e:
                    print(f"Error creating AI billboard simulation: {str(e)}")
                    # Fallback to simple simulation
                    sim_path = create_billboard_simulation(banner_path)
                    if sim_path:
                        sim_filename = os.path.basename(sim_path)
                        sim_url = f"{domain_public}/static/uploads/{sim_filename}"
                
                # Save to database - FORCE SAVE EVERY TIME
                print(f"🔄 FORCE SAVING BANNER TO DATABASE...")
                print(f"📊 Data to save: user_id={user_id}, image_url={banner_url_local}, caption={title}")
                
                # Always try to save, even if there are errors
                try:
                    # Test database connection first
                    test_user = User.query.get(user_id)
                    print(f"✅ Database connection OK, user found: {test_user.username if test_user else 'None'}")
                    
                    # Test if we can query images
                    existing_images = Image.query.filter_by(user_id=user_id).count()
                    print(f"📊 Existing images for user: {existing_images}")
                    
                except Exception as db_test_error:
                    print(f"❌ Database connection test failed: {str(db_test_error)}")
                    import traceback
                    print(f"❌ Database test traceback: {traceback.format_exc()}")
                
                # FORCE CREATE Image record in database
                try:
                    new_image = Image(
                        user_id=user_id,
                        image_url=banner_url_local,
                        caption=title,
                        is_favorite=False,
                        view_count=0
                    )
                    
                    print(f"📝 Created Image object: {new_image}")
                    print(f"📝 Image fields: user_id={new_image.user_id}, image_url={new_image.image_url}, caption={new_image.caption}")
                    
                    db.session.add(new_image)
                    print(f"➕ Added to session")
                    
                    db.session.commit()
                    print(f"✅ FORCE COMMITTED to database")
                    
                    # Verify the image was saved
                    saved_image = Image.query.get(new_image.id)
                    if saved_image:
                        print(f"✅ VERIFICATION SUCCESS: Image saved with ID {saved_image.id}")
                        print(f"✅ VERIFICATION: URL = {saved_image.image_url}")
                        print(f"✅ VERIFICATION: Caption = {saved_image.caption}")
                        print(f"✅ VERIFICATION: Created at = {saved_image.created_at}")
                    else:
                        print(f"❌ VERIFICATION FAILED: Image not found after save")
                    
                    print(f"💾 BANNER FORCE SAVED to database with ID: {new_image.id}")
                    
                except Exception as save_error:
                    print(f"❌ FORCE SAVE ERROR: {str(save_error)}")
                    import traceback
                    print(f"❌ FORCE SAVE TRACEBACK: {traceback.format_exc()}")
                    db.session.rollback()
                    print(f"🔄 Rolled back database session")
                    
                    # Try alternative save method
                    try:
                        print(f"🔄 TRYING ALTERNATIVE SAVE METHOD...")
                        from sqlalchemy import text
                        
                        # Direct SQL insert
                        sql = text("""
                            INSERT INTO images (user_id, image_url, caption, is_favorite, view_count, created_at, updated_at)
                            VALUES (:user_id, :image_url, :caption, :is_favorite, :view_count, NOW(), NOW())
                        """)
                        
                        result = db.session.execute(sql, {
                            'user_id': user_id,
                            'image_url': banner_url_local,
                            'caption': title,
                            'is_favorite': False,
                            'view_count': 0
                        })
                        
                        db.session.commit()
                        print(f"✅ ALTERNATIVE SAVE SUCCESS: {result.rowcount} rows inserted")
                        
                    except Exception as alt_error:
                        print(f"❌ ALTERNATIVE SAVE FAILED: {str(alt_error)}")
                        db.session.rollback()
                
                # If simulation exists, save it too
                if sim_url and sim_path:
                    try:
                        print(f"🔄 FORCE SAVING SIMULATION TO DATABASE...")
                        sim_image = Image(
                            user_id=user_id,
                            image_url=sim_url,
                            caption=f"{title} - Simulation",
                            is_favorite=False,
                            view_count=0
                        )
                        
                        db.session.add(sim_image)
                        db.session.commit()
                        print(f"✅ SIMULATION FORCE SAVED with ID: {sim_image.id}")
                        
                    except Exception as sim_error:
                        print(f"❌ SIMULATION SAVE ERROR: {str(sim_error)}")
                        db.session.rollback()
                
                response_data = {
                    'success': True,
                    'status': 'completed',
                    'banner_url': banner_url_local,
                    'simulation_url': sim_url,
                    'simulation_request_id': sim_request_id,
                    'message': 'Banner berhasil dibuat!',
                    'image_id': new_image.id if 'new_image' in locals() else None,
                    'file_size': os.path.getsize(banner_path) if os.path.exists(banner_path) else 0
                }
                print(f"🎉 Returning banner completion response: {response_data}")
                return jsonify(response_data)
                
            except Exception as e:
                print(f"Error processing completed banner: {str(e)}")
                import traceback
                print(f"Error traceback: {traceback.format_exc()}")
                return jsonify({'error': f'Error processing banner: {str(e)}'}), 500
        else:
            # Still processing
            return jsonify({
                'success': True,
                'status': 'processing',
                'message': 'Banner masih dalam proses...'
            })
            
    except Exception as e:
        print(f"Error checking banner status: {str(e)}")
        return jsonify({'error': f'Error checking status: {str(e)}'}), 500

@generate_banner_bp.route('/check_simulation_status/<request_id>')
def check_simulation_status_endpoint(request_id):
    """Check status of billboard simulation generation"""
    try:
        # Check user authentication
        if 'user_id' not in session:
            return jsonify({'error': 'User belum login'}), 401
        
        # Check simulation status
        sim_url = check_banner_status(request_id)
        
        if sim_url:
            # Simulation completed, process it
            try:
                # Download and save simulation
                response = requests.get(sim_url)
                sim_filename = f"simulation_{uuid.uuid4().hex}.jpg"
                sim_path = os.path.join(current_app.config['UPLOAD_FOLDER'], sim_filename)
                
                with open(sim_path, 'wb') as f:
                    f.write(response.content)
                
                # Get domain for URL generation
                domain_public = current_app.config.get('DOMAIN_PUBLIC', 'http://127.0.0.1:5000')
                sim_url_local = f"{domain_public}/static/uploads/{sim_filename}"
                
                return jsonify({
                    'success': True,
                    'status': 'completed',
                    'simulation_url': sim_url_local,
                    'message': 'Billboard simulation berhasil dibuat!'
                })
                
            except Exception as e:
                print(f"Error processing completed simulation: {str(e)}")
                return jsonify({'error': f'Error processing simulation: {str(e)}'}), 500
        else:
            # Still processing
            return jsonify({
                'success': True,
                'status': 'processing',
                'message': 'Billboard simulation masih dalam proses...'
            })
            
    except Exception as e:
        print(f"Error checking simulation status: {str(e)}")
        return jsonify({'error': f'Error checking simulation status: {str(e)}'}), 500

@generate_banner_bp.route('/detect_banner', methods=['POST'])
def detect_banner():
    """Detect banner information using AI Gemini"""
    try:
        # Check user authentication
        if 'user_id' not in session:
            return jsonify({'error': 'User belum login'}), 401
        
        # Check if file is uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'Tidak ada file yang diupload'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Tidak ada file yang dipilih'}), 400
        
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            return jsonify({'error': 'Format file tidak didukung. Gunakan PNG, JPG, JPEG, atau WEBP'}), 400
        
        # Save uploaded file temporarily
        filename = f"temp_detect_{uuid.uuid4().hex}.{file.filename.split('.')[-1]}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Import GeminiChatService
            import sys
            import base64
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            if parent_dir not in sys.path:
                sys.path.append(parent_dir)
            
            from chat import gemini_service
            
            # Convert image to base64
            with open(filepath, 'rb') as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Create specific prompt for banner analysis
            banner_prompt = """Analyze this banner image and provide detailed information in JSON format. Focus on:

1. **Text Content**: Extract all visible text, including main titles, subtitles, and any other text elements
2. **Color Scheme**: Identify the dominant colors used in the banner (provide hex codes like #FF0000)
3. **Design Elements**: Describe the overall design style, layout, and visual elements
4. **Dimensions**: Estimate the banner dimensions based on aspect ratio (width x height in meters, standard sizes: 1x1m, 1.5x1m, 2x1m, 2.5x1m, 3x1m)
5. **Brand Elements**: Identify any logos, brand names, or company information
6. **Purpose**: Determine what type of business or service this banner represents
7. **Layout**: Describe the positioning of text, logo, and QR code areas

Please respond with a structured analysis that can be used to create similar banners. Focus on standard banner dimensions and professional business design elements."""
            
            # Analyze image using GeminiChatService
            print("🔍 Starting AI banner analysis...")
            analysis_result = gemini_service.analyze_image_for_music(image_data)
            print(f"🔍 AI Analysis Result: {analysis_result}")
            
            if analysis_result and analysis_result.get('success'):
                analysis_text = analysis_result.get('analysis', '')
                
                # Parse the analysis to extract structured information
                detected_info = parse_banner_analysis(analysis_text, filepath)
                
                return jsonify({
                    'success': True,
                    'detected_info': detected_info,
                    'raw_analysis': analysis_text,
                    'message': 'Banner berhasil dianalisis dengan AI Gemini!'
                })
            else:
                error_msg = analysis_result.get('error', 'Gagal menganalisis banner') if analysis_result else 'Tidak ada respons dari AI'
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 500
                
        except ImportError as ie:
            print(f"❌ Failed to import gemini_service: {ie}")
            return jsonify({
                'success': False,
                'error': 'AI service tidak tersedia'
            }), 500
        except Exception as e:
            print(f"❌ Error in AI analysis: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Error menganalisis banner: {str(e)}'
            }), 500
        finally:
            # Clean up temporary file
            if os.path.exists(filepath):
                os.remove(filepath)
                
    except Exception as e:
        print(f"Error in detect_banner: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500

def parse_banner_analysis(analysis_text, image_path):
    """Parse AI analysis text to extract structured banner information"""
    try:
        # Load image for basic info
        img = PILImage.open(image_path)
        width, height = img.size
        aspect_ratio = round(width / height, 2)
        
        # Estimate real dimensions based on aspect ratio (standard banner sizes)
        if aspect_ratio >= 3.0:
            est_width_m = 3.0
            est_height_m = 1.0
        elif aspect_ratio >= 2.5:
            est_width_m = 2.5
            est_height_m = 1.0
        elif aspect_ratio >= 2.0:
            est_width_m = 2.0
            est_height_m = 1.0
        elif aspect_ratio >= 1.5:
            est_width_m = 1.5
            est_height_m = 1.0
        elif aspect_ratio >= 1.0:
            est_width_m = 1.0
            est_height_m = 1.0
        else:
            # Portrait banner
            est_width_m = 1.0
            est_height_m = 1.5
        
        # Extract colors from analysis text (look for hex codes)
        import re
        color_pattern = r'#[0-9A-Fa-f]{6}'
        detected_colors = re.findall(color_pattern, analysis_text)
        
        # If no colors found, use default
        if not detected_colors:
            detected_colors = ["#007BFF", "#FFFFFF", "#FFD700"]
        
        # Extract text content (look for quoted text or specific patterns)
        text_patterns = [
            r'"([^"]+)"',  # Quoted text
            r'Text[:\s]+([^\n]+)',  # Text: content
            r'Title[:\s]+([^\n]+)',  # Title: content
            r'Main text[:\s]+([^\n]+)',  # Main text: content
        ]
        
        detected_text = ""
        for pattern in text_patterns:
            matches = re.findall(pattern, analysis_text, re.IGNORECASE)
            if matches:
                detected_text = matches[0].strip()
                break
        
        return {
            "width_m": est_width_m,
            "height_m": est_height_m,
            "dominant_colors": detected_colors[:3],  # Take first 3 colors
            "detected_text": detected_text,
            "aspect_ratio": f"{aspect_ratio}:1",
            "original_size": f"{width}x{height}",
            "ai_analysis": analysis_text
        }
        
    except Exception as e:
        print(f"Error parsing banner analysis: {str(e)}")
        return {
            "width_m": 2.0,
            "height_m": 1.0,
            "dominant_colors": ["#007BFF", "#FFFFFF", "#FFD700"],
            "detected_text": "",
            "aspect_ratio": "2:1",
            "original_size": "2048x1024",
            "ai_analysis": analysis_text
        }

@generate_banner_bp.route('/test_database')
def test_database():
    """Test database connection and check if banner is saved"""
    try:
        # Check user authentication
        if 'user_id' not in session:
            return jsonify({'error': 'User belum login'}), 401
        
        user_id = session.get('user_id')
        
        # Test database connection
        try:
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User tidak ditemukan'}), 404
            
            # Get all images for this user
            user_images = Image.query.filter_by(user_id=user_id).order_by(Image.created_at.desc()).limit(20).all()
            
            images_data = []
            for img in user_images:
                images_data.append({
                    'id': img.id,
                    'image_url': img.image_url,
                    'caption': img.caption,
                    'created_at': img.created_at.isoformat() if img.created_at else None,
                    'is_favorite': img.is_favorite,
                    'view_count': img.view_count
                })
            
            # Check database schema
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            columns = inspector.get_columns('images') if 'images' in tables else []
            
            return jsonify({
                'success': True,
                'user_id': user_id,
                'username': user.username,
                'total_images': len(images_data),
                'images': images_data,
                'database_status': 'OK',
                'database_info': {
                    'tables': tables,
                    'images_table_columns': [col['name'] for col in columns],
                    'total_images_in_db': Image.query.count()
                }
            })
            
        except Exception as db_error:
            return jsonify({
                'success': False,
                'error': f'Database error: {str(db_error)}',
                'database_status': 'ERROR'
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@generate_banner_bp.route('/force_save_banner', methods=['POST'])
def force_save_banner():
    """Force save a banner to database for testing"""
    try:
        # Check user authentication
        if 'user_id' not in session:
            return jsonify({'error': 'User belum login'}), 401
        
        user_id = session.get('user_id')
        data = request.get_json()
        
        banner_url = data.get('banner_url')
        title = data.get('title', 'Test Banner')
        
        if not banner_url:
            return jsonify({'error': 'banner_url is required'}), 400
        
        print(f"🔄 Force saving banner: user_id={user_id}, url={banner_url}, title={title}")
        
        # Create Image record in database
        new_image = Image(
            user_id=user_id,
            image_url=banner_url,
            caption=title,
            is_favorite=False,
            view_count=0
        )
        
        db.session.add(new_image)
        db.session.commit()
        
        print(f"✅ Force saved banner with ID: {new_image.id}")
        
        return jsonify({
            'success': True,
            'message': 'Banner force saved successfully',
            'image_id': new_image.id,
            'image_url': new_image.image_url,
            'caption': new_image.caption
        })
        
    except Exception as e:
        print(f"❌ Error force saving banner: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Error: {str(e)}'}), 500

@generate_banner_bp.route('/delete_image/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Delete an image from database"""
    try:
        # Check user authentication
        if 'user_id' not in session:
            return jsonify({'error': 'User belum login'}), 401
        
        user_id = session.get('user_id')
        
        # Find the image
        image = Image.query.filter_by(id=image_id, user_id=user_id).first()
        if not image:
            return jsonify({'error': 'Image tidak ditemukan'}), 404
        
        # Delete from database
        db.session.delete(image)
        db.session.commit()
        
        print(f"🗑️ Image deleted: ID {image_id} by user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Image berhasil dihapus'
        })
        
    except Exception as e:
        print(f"❌ Error deleting image: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Error: {str(e)}'}), 500

@generate_banner_bp.route('/download_banner_pdf')
def download_banner_pdf():
    """Download banner as PDF"""
    try:
        banner_url = request.args.get('banner_url')
        width_m = float(request.args.get('width_m', 2.0))
        height_m = float(request.args.get('height_m', 1.0))
        
        if not banner_url:
            return jsonify({'error': 'Banner URL tidak ditemukan'}), 400
        
        # Download banner image
        response = requests.get(banner_url)
        banner_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"temp_banner_{uuid.uuid4().hex}.png")
        
        with open(banner_path, 'wb') as f:
            f.write(response.content)
        
        # Convert to PDF with 1000 DPI
        pdf_path = convert_to_pdf(banner_path, width_m, height_m, dpi=1000)
        
        if pdf_path and os.path.exists(pdf_path):
            # Clean up temp file
            os.remove(banner_path)
            
            # Return PDF file
            from flask import send_file
            return send_file(
                pdf_path, 
                as_attachment=True, 
                download_name=f"banner_{width_m}x{height_m}m_1000dpi.pdf",
                mimetype='application/pdf'
            )
        else:
            # Clean up temp file if PDF creation failed
            if os.path.exists(banner_path):
                os.remove(banner_path)
            return jsonify({'error': 'Gagal membuat PDF. Pastikan ReportLab terinstall.'}), 500
            
    except Exception as e:
        print(f"Error downloading PDF: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500

