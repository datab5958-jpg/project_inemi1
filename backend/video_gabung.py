import os
os.environ["IMAGEMAGICK_BINARY"] = r"C:/Program Files/ImageMagick-7.1.1-Q16/magick.exe"
from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, session, jsonify, current_app, abort
from werkzeug.utils import secure_filename
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, ColorClip, concatenate_audioclips
from pydub import AudioSegment
import uuid
import time
import requests
import json
import urllib.parse
from PIL import Image as PILImage
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video.tools.subtitles import TextClip
import re
from models import db, Video, Image, Song, VideoIklan
from config import Config

video_gabung_bp = Blueprint('video_gabung', __name__, template_folder='templates')

# Hapus semua baris current_app.config[...] dan current_app.secret_key di level global
# Tambahkan pengecekan dan pembuatan folder di dalam fungsi index dan upload_files

ALLOWED_VIDEO_EXTENSIONS = {'mp4'}
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3'}

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def allowed_audio_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def safe_remove(filepath):
    try:
        os.remove(filepath)
    except PermissionError:
        pass

def srt_time_to_seconds(s):
    h, m, rest = s.split(':')
    if '.' in rest:
        s_, ms = rest.split('.')
    else:
        s_, ms = rest, '0'
    return int(h) * 3600 + int(m) * 60 + int(s_) + int(ms) / 1000

def parse_srt_to_list(srt_path):
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(srt_path, 'r', encoding='latin-1') as f:
            content = f.read()
    pattern = re.compile(r'(\d+)\s+([\d:,]+)\s+-->\s+([\d:,]+)\s+([\s\S]*?)(?=\n\d+\n|\Z)', re.MULTILINE)
    subs = []
    for match in pattern.finditer(content):
        start = srt_time_to_seconds(match.group(2).replace(',', '.'))
        end = srt_time_to_seconds(match.group(3).replace(',', '.'))
        text = match.group(4).replace('\n', ' ').strip()
        subs.append(((start, end), text))
    return subs

def ensure_local_file(file_path_or_url, upload_folder, prefix):
    import shutil
    import requests
    import os
    import uuid
    if file_path_or_url.startswith('http://') or file_path_or_url.startswith('https://'):
        # Download file ke uploads
        ext = file_path_or_url.split('.')[-1].split('?')[0].split('&')[0]
        filename = f'{prefix}_{uuid.uuid4().hex}.{ext}'
        local_path = os.path.join(upload_folder, filename)
        r = requests.get(file_path_or_url, stream=True)
        with open(local_path, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
        return filename
    elif file_path_or_url.startswith('/static/'):
        # Copy file dari static ke uploads
        ext = file_path_or_url.split('.')[-1]
        filename = f'{prefix}_{uuid.uuid4().hex}.{ext}'
        src_path = file_path_or_url[1:] if file_path_or_url.startswith('/') else file_path_or_url
        src_path = os.path.join(os.getcwd(), src_path)
        local_path = os.path.join(upload_folder, filename)
        if os.path.exists(src_path):
            shutil.copy(src_path, local_path)
            return filename
        else:
            raise FileNotFoundError(f'Static file not found: {src_path}')
    else:
        # Sudah lokal (hasil upload manual)
        return file_path_or_url

@video_gabung_bp.route('/')
def index():
    # Initialize session if not exists
    if 'uploaded_files' not in session:
        session['uploaded_files'] = {
            'videos': [],
            'images': [],
            'audios': [],
            'subtitle': None
        }
    # Ensure upload and result directories exist
    current_app.config['UPLOAD_FOLDER'] = 'static/uploads'
    current_app.config['RESULT_FOLDER'] = 'static/results'
    current_app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload
    current_app.secret_key = 'inemiluxury2023'  # Secret key untuk session
    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(current_app.config['RESULT_FOLDER'], exist_ok=True)
    
    # Debug: cek isi folder
    print(f"UPLOAD_FOLDER: {current_app.config['UPLOAD_FOLDER']}")
    print(f"RESULT_FOLDER: {current_app.config['RESULT_FOLDER']}")
    print(f"Upload folder exists: {os.path.exists(current_app.config['UPLOAD_FOLDER'])}")
    print(f"Result folder exists: {os.path.exists(current_app.config['RESULT_FOLDER'])}")
    if os.path.exists(current_app.config['RESULT_FOLDER']):
        result_files = os.listdir(current_app.config['RESULT_FOLDER'])
        print(f"Files in result folder: {result_files}")
    return render_template('video_gabung.html')

@video_gabung_bp.route('/upload', methods=['POST'])
def upload_files():
    print('=== MULAI UPLOAD VIDEO GABUNGAN ===')
    user_id = session.get('user_id')
    
    # Cek session user
    if not user_id:
        return jsonify({'error': 'User belum login'}), 401
    
    from models import User, Song
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User tidak ditemukan'}), 404
    
    # Cek kredit user
    if user.kredit < 15:
        return jsonify({'error': 'Kredit Anda tidak cukup untuk generate video (minimal 15 kredit)'}), 403
    
    # Kurangi kredit
    user.kredit -= 15
    db.session.commit()
    print(f'User {user_id} kredit berkurang 15, sisa: {user.kredit}')
    try:
        project_id = str(uuid.uuid4())
        if 'uploaded_files' not in session:
            session['uploaded_files'] = {
                'videos': [],
                'images': [],
                'audios': [],
                'subtitle': None
            }
        existing_files = session['uploaded_files']
        for f in os.listdir(current_app.config['UPLOAD_FOLDER']):
            if f.startswith('project_') or f.startswith('result_'):
                safe_remove(os.path.join(current_app.config['UPLOAD_FOLDER'], f))
        gallery_videos = request.form.getlist('gallery_videos[]')
        gallery_images = request.form.getlist('gallery_images[]')
        gallery_audios = request.form.getlist('gallery_audios[]')
        video_files = existing_files['videos'].copy() + gallery_videos
        image_files = existing_files['images'].copy() + gallery_images
        audio_files = existing_files['audios'].copy() + gallery_audios
        if 'videos' in request.files:
            for file in request.files.getlist('videos'):
                if file and allowed_video_file(file.filename):
                    filename = secure_filename(f'video_{uuid.uuid4().hex}.mp4')
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    video_files.append(filename)
                    existing_files['videos'].append(filename)
        if 'images' in request.files:
            for file in request.files.getlist('images'):
                if file and allowed_image_file(file.filename):
                    filename = secure_filename(f'image_{uuid.uuid4().hex}.{file.filename.rsplit(".", 1)[1].lower()}')
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    image_files.append(filename)
                    existing_files['images'].append(filename)
        if 'audios' in request.files:
            for file in request.files.getlist('audios'):
                if file and allowed_audio_file(file.filename):
                    filename = secure_filename(f'audio_{uuid.uuid4().hex}.mp3')
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    audio_files.append(filename)
                    existing_files['audios'].append(filename)
        subtitle_file = existing_files['subtitle']
        if 'subtitle' in request.files:
            file = request.files['subtitle']
            if file and file.filename.endswith('.srt'):
                subtitle_file = secure_filename(f'subtitle_{uuid.uuid4().hex}.srt')
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], subtitle_file))
                existing_files['subtitle'] = subtitle_file
        subtitle_text = request.form.get('subtitle_text', '').strip()
        if subtitle_text:
            lines = [l.strip() for l in subtitle_text.split('\n') if l.strip()]
            srt_lines = []
            for i, line in enumerate(lines):
                start = i * 2
                end = (i + 1) * 2
                srt_lines.append(f"{i+1}\n00:00:{start:02d},000 --> 00:00:{end:02d},000\n{line}\n")
            subtitle_file = f'subtitle_{uuid.uuid4().hex}.srt'
            srt_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subtitle_file)
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(srt_lines))
            existing_files['subtitle'] = subtitle_file
        
        # Ambil orientasi video dari form
        video_orientation = request.form.get('video_orientation', 'landscape')
        print(f'Video orientation: {video_orientation}')
        
        # Tentukan target_size berdasarkan orientasi
        if video_orientation == 'portrait':
            target_size = (1080, 1920)  # Portrait 9:16
        else:
            target_size = (1920, 1080)  # Landscape 16:9 (default)
        # --- SUBTITLE OTOMATIS DARI LIRIK ---
        subtitle_otomatis = request.form.get('subtitle_otomatis') == 'on'
        if not subtitle_text and not subtitle_file and subtitle_otomatis and audio_files:
            # Cek audio dari galeri (bukan upload manual)
            audio_galeri = None
            for gal_audio in gallery_audios:
                # Cari Song di database
                song = Song.query.filter((Song.audio_url == gal_audio) | (Song.stream_audio_url == gal_audio)).first()
                if song and getattr(song, 'lyrics', None):
                    audio_galeri = (gal_audio, song.lyrics)
                    break
            if audio_galeri:
                # Ambil durasi audio
                audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], ensure_local_file(audio_galeri[0], current_app.config['UPLOAD_FOLDER'], 'audio'))
                audio_clip = AudioFileClip(audio_path)
                durasi = audio_clip.duration
                lirik_baris = [l.strip() for l in audio_galeri[1].split('\n') if l.strip()]
                n = len(lirik_baris)
                if n > 0:
                    srt_lines = []
                    for i, line in enumerate(lirik_baris):
                        start = int(i * durasi / n)
                        end = int((i + 1) * durasi / n)
                        srt_lines.append(f"{i+1}\n00:00:{start:02d},000 --> 00:00:{end:02d},000\n{line}\n")
                    subtitle_file = f'subtitle_{uuid.uuid4().hex}.srt'
                    srt_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subtitle_file)
                    with open(srt_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(srt_lines))
                    existing_files['subtitle'] = subtitle_file
        # --- END SUBTITLE OTOMATIS ---
        if request.form.get('generate_ai_music') == 'on':
            prompt = request.form.get('ai_music_prompt') or 'musik santai, piano, suasana pagi'
            url = f"{Config.SUNO_BASE_URL}/api/v1/generate"
            callback_url = f"{Config.CALLBACK_DOMAIN}/api/music_callback?project_id={project_id}"
            payload = json.dumps({
                "prompt": prompt,
                "style": "Classical",
                "title": "AI Generated Music",
                "customMode": True,
                "instrumental": True,
                "model": "V3_5",
                "negativeTags": "Heavy Metal, Upbeat Drums",
                "callBackUrl": callback_url
            })
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {Config.SUNO_API_KEY}'
            }
            try:
                response = requests.post(url, headers=headers, data=payload, timeout=60)
                print('RESPON API MUSIK:', response.text)
                if response.status_code == 200:
                    data = response.json()
                    audio_url = data.get('audio_url') or data.get('result', {}).get('url') or data.get('url')
                    if audio_url:
                        print('Link mp3 ditemukan di respons, download dan gabungkan langsung.')
                        audio_filename = f'ai_music_{uuid.uuid4().hex}.mp3'
                        audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], audio_filename)
                        audio_resp = requests.get(audio_url)
                        with open(audio_path, 'wb') as f:
                            f.write(audio_resp.content)
                        audio_files.append(audio_filename)
                        existing_files['audios'].append(audio_filename)
                    else:
                        print('Tidak ada link mp3 di respons. Menunggu callback dari API. Jika server di localhost, callback TIDAK akan masuk kecuali pakai ngrok/public URL!')
                else:
                    print('Gagal request API musik, status:', response.status_code)
            except Exception as e:
                print('Gagal generate musik AI:', e)
        session['uploaded_files'] = existing_files
        session.modified = True
        with open(os.path.join(current_app.config['UPLOAD_FOLDER'], f'project_{project_id}.json'), 'w') as f:
            json.dump({
                'video_files': video_files,
                'image_files': image_files,
                'audio_files': audio_files,
                'video_orientation': video_orientation,
                'target_size': target_size
            }, f)
        video_files = [ensure_local_file(f, current_app.config['UPLOAD_FOLDER'], 'video') for f in video_files]
        image_files = [ensure_local_file(f, current_app.config['UPLOAD_FOLDER'], 'image') for f in image_files]
        audio_files = [ensure_local_file(f, current_app.config['UPLOAD_FOLDER'], 'audio') for f in audio_files]
        video_files = [f for f in video_files if f and os.path.isfile(os.path.join(current_app.config['UPLOAD_FOLDER'], f))]
        image_files = [f for f in image_files if f and os.path.isfile(os.path.join(current_app.config['UPLOAD_FOLDER'], f))]
        audio_files = [f for f in audio_files if f and os.path.isfile(os.path.join(current_app.config['UPLOAD_FOLDER'], f))]
        # --- LOGIC DURASI VIDEO ---
        # Jika hanya gambar+audio (tanpa video), set durasi video sepanjang audio
        # Jika ada video, durasi video mengikuti video, audio dipotong jika lebih panjang
        print(f"Calling process_files with:")
        print(f"  video_files: {video_files}")
        print(f"  image_files: {image_files}")
        print(f"  audio_files: {audio_files}")
        print(f"  project_id: {project_id}")
        print(f"  subtitle_file: {subtitle_file}")
        print(f"  video_orientation: {video_orientation}")
        
        result_filename = process_files(video_files, image_files, audio_files, project_id, 'AWAL', subtitle_file, video_orientation)
        print(f"process_files returned: {result_filename}")
        print('=== SELESAI PROSES, REDIRECT KE HASIL ===')
        try:
            caption = request.form.get('caption', '')
            result_path = os.path.join(current_app.config['RESULT_FOLDER'], result_filename)
            
            # Cek apakah file hasil ada
            if not os.path.exists(result_path):
                print(f"ERROR: File hasil tidak ditemukan: {result_path}")
                raise FileNotFoundError(f"File hasil tidak ditemukan: {result_path}")
            
            print(f"File hasil ditemukan: {result_path}")
            print(f"File size: {os.path.getsize(result_path)} bytes")
            
            with open(result_path, 'rb') as f:
                video_binary = f.read()
            
            print(f"Video binary size: {len(video_binary)} bytes")
            
            video_iklan = VideoIklan(
                user_id=user_id,
                video_url=result_filename,
                caption=caption,
            )
            db.session.add(video_iklan)
            db.session.commit()
            print(f"Video gabungan berhasil disimpan ke database dengan id: {video_iklan.id}")
            print(f"Video URL: {video_iklan.video_url}")
        except Exception as e:
            print(f"Gagal simpan video ke database: {e}")
            import traceback
            traceback.print_exc()
        
        # Jangan hapus file hasil dari RESULT_FOLDER, hanya hapus dari UPLOAD_FOLDER
        print("Cleaning up temporary files from UPLOAD_FOLDER...")
        for f in os.listdir(current_app.config['UPLOAD_FOLDER']):
            if f.startswith('project_') or f.startswith('result_'):
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f)
                print(f"Removing: {file_path}")
                safe_remove(file_path)
        
        # Cek file hasil di RESULT_FOLDER
        print(f"Checking RESULT_FOLDER: {current_app.config['RESULT_FOLDER']}")
        if os.path.exists(current_app.config['RESULT_FOLDER']):
            result_files = os.listdir(current_app.config['RESULT_FOLDER'])
            print(f"Files in RESULT_FOLDER: {result_files}")
            if result_filename in result_files:
                print(f"✓ Result file found: {result_filename}")
            else:
                print(f"✗ Result file NOT found: {result_filename}")
        print('DEBUG: request.args =', request.args)
        if request.args.get('ajax') == '1':
            print('DEBUG: AJAX detected, returning JSON')
            return jsonify({'result_filename': result_filename})
        print('DEBUG: fallback, returning redirect')
        return redirect(url_for('video_gabung.result', filename=result_filename))
    except Exception as e:
        print('ERROR upload_files:', e)
        import traceback; traceback.print_exc()
        print('=== ERROR, RETURN JSON ERROR ===')
        print('DEBUG: request.args =', request.args)
        if request.args.get('ajax') == '1':
            print('DEBUG: AJAX error, returning JSON')
            return jsonify({'error': str(e)}), 500
        return jsonify({'error': str(e)}), 500

def process_files(video_files, image_files, audio_files, project_id=None, status='AWAL', subtitle_file=None, video_orientation='landscape'):
    clips = []
    image_clips = []
    audio_clips = []
    final_video = None
    
    # Tentukan ukuran target berdasarkan orientasi
    if video_orientation == 'portrait':
        target_size = (1080, 1920)  # Portrait 9:16
        print(f'Using portrait orientation: {target_size}')
    else:
        target_size = (1920, 1080)  # Landscape 16:9 (default)
        print(f'Using landscape orientation: {target_size}')
    video_clips = []
    for video in video_files:
        video_path = os.path.join(current_app.config['UPLOAD_FOLDER'], video)
        clip = VideoFileClip(video_path)
        video_clips.append(clip)
    
    # Gunakan target_size yang sudah ditentukan berdasarkan orientasi
    # Tidak lagi mengikuti ukuran video pertama untuk konsistensi orientasi
    # --- LOGIC BARU: Jika hanya gambar+audio (tanpa video), durasi video = durasi audio ---
    durasi_audio = None
    if not video_clips and audio_files:
        # Ambil durasi audio terpanjang
        max_dur = 0
        for audio_file in audio_files:
            audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], audio_file)
            audio_clip = AudioFileClip(audio_path)
            audio_clips.append(audio_clip)
            if audio_clip.duration > max_dur:
                max_dur = audio_clip.duration
        durasi_audio = max_dur
        n_img = len(image_files)
        if n_img == 0:
            # Tidak ada gambar, pakai ColorClip hitam
            image_clips = [ColorClip(target_size, color=(0,0,0), duration=durasi_audio)]
        elif n_img == 1:
            # Satu gambar, tampilkan sepanjang audio
            image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_files[0])
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            try:
                img = PILImage.open(image_path).convert('RGB')
                img.save(image_path)
                image_clips = [ImageClip(image_path, duration=durasi_audio).resize(newsize=target_size)]
            except Exception as e:
                print(f"Error processing image {image_path}: {e}")
                raise
        else:
            # Banyak gambar, bagi rata durasi audio
            durasi_per_gambar = durasi_audio / n_img
            for image_file in image_files:
                image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_file)
                if not os.path.exists(image_path):
                    print(f"Warning: Image file not found: {image_path}, skipping...")
                    continue
                try:
                    img = PILImage.open(image_path).convert('RGB')
                    img.save(image_path)
                    image_clips.append(ImageClip(image_path, duration=durasi_per_gambar).resize(newsize=target_size))
                except Exception as e:
                    print(f"Error processing image {image_path}: {e}")
                    continue
        clips = image_clips
    else:
        # Proses gambar: konversi ke RGB dan resize ke target_size (default lama)
        for image_file in image_files:
            image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_file)
            img = PILImage.open(image_path).convert('RGB')
            img.save(image_path)
            image_clip = ImageClip(image_path, duration=2).resize(newsize=target_size)
            clips.append(image_clip)
            image_clips.append(image_clip)
    # Resize semua video ke target_size
    for i, clip in enumerate(video_clips):
        video_clips[i] = clip.resize(newsize=target_size)
    if video_clips:
        final_clip = concatenate_videoclips(video_clips)
        clips.append(final_clip)
    # Combine all clips (openings + videos)
    if len(clips) > 1:
        final_video = concatenate_videoclips(clips)
    elif clips:
        final_video = clips[0]
    else:
        final_video = ColorClip(target_size, color=(0, 0, 0), duration=5)
    # Gabungkan semua audio jika ada
    if audio_files:
        combined_audio = None
        if not audio_clips:
            for audio_file in audio_files:
                audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], audio_file)
                audio_clip = AudioFileClip(audio_path)
                audio_clips.append(audio_clip)
        for audio_clip in audio_clips:
            if combined_audio is None:
                combined_audio = audio_clip
            else:
                combined_audio = concatenate_audioclips([combined_audio, audio_clip])
        # Potong audio jika lebih panjang dari video
        if combined_audio.duration > final_video.duration:
            combined_audio = combined_audio.subclip(0, final_video.duration)
        final_video = final_video.set_audio(combined_audio)
    # Setelah final_video terbentuk, tambahkan subtitle jika ada
    if subtitle_file:
        srt_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subtitle_file)
        def generator(txt):
            return (
                TextClip(
                    txt,
                    font='Arial-Bold',
                    fontsize=40,
                    color='white',
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(int(final_video.w * 0.9), None),
                    align='center'
                )
                .margin(bottom=40, opacity=0)
                .set_position(('center', int(final_video.h * 0.80)))
            )
        subs_list = parse_srt_to_list(srt_path)
        subs = SubtitlesClip(subs_list, generator)
        subtitle_y = int(final_video.h * 0.80)
        final_video = CompositeVideoClip([
            final_video,
            subs.set_pos(('center', subtitle_y))
        ])
    result_filename = f'result_{uuid.uuid4().hex}.mp4'
    result_path = os.path.join(current_app.config['RESULT_FOLDER'], result_filename)
    write_args = dict(codec='libx264', audio_codec='aac')
    if not hasattr(final_video, 'fps') or final_video.fps is None:
        write_args['fps'] = 24
    final_video.write_videofile(result_path, **write_args)
    for clip in video_clips:
        clip.close()
    for clip in image_clips:
        clip.close()
    for clip in audio_clips:
        clip.close()
    if final_video is not None:
        final_video.close()
    
    # Cek apakah file hasil benar-benar dibuat
    if os.path.exists(result_path):
        file_size = os.path.getsize(result_path)
        print(f"=== [PROJECT {project_id or '-'} | VIDEO {status}] ===")
        print(f"File video siap: {result_path}")
        print(f"File size: {file_size} bytes")
        print('===============================')
    else:
        print(f"ERROR: File hasil tidak dibuat: {result_path}")
        raise FileNotFoundError(f"File hasil tidak dibuat: {result_path}")
    
    return result_filename

@video_gabung_bp.route('/result/<filename>')
def result(filename):
    # Cari semua file project di uploads
    project_files = [f for f in os.listdir(current_app.config['UPLOAD_FOLDER']) if f.startswith('project_') and f.endswith('.json')]
    all_results = []
    for pf in project_files:
        with open(os.path.join(current_app.config['UPLOAD_FOLDER'], pf), 'r') as f:
            pdata = json.load(f)
            # Cari semua hasil video di folder results
            result_videos = [f for f in os.listdir(current_app.config['RESULT_FOLDER']) if f.startswith('result_') and f.endswith('.mp4')]
            all_results.extend(result_videos)
    # Hilangkan duplikat
    all_results = list(sorted(set(all_results)))
    return render_template('index.html', result_filename=filename, all_results=all_results)

@video_gabung_bp.route('/download/<filename>')
def download(filename):
    return send_from_directory(current_app.config['RESULT_FOLDER'], filename, as_attachment=True)

@video_gabung_bp.route('/api/get_uploaded_files')
def get_uploaded_files():
    """API untuk mendapatkan daftar file yang sudah diupload"""
    if 'uploaded_files' not in session:
        session['uploaded_files'] = {
            'videos': [],
            'images': [],
            'audios': [],
            'subtitle': None
        }
    
    # Filter files that actually exist
    existing_files = {}
    for file_type, files in session['uploaded_files'].items():
        if isinstance(files, list):
            existing_files[file_type] = [
                f for f in files 
                if os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'], f))
            ]
        else:
            existing_files[file_type] = files if (
                files and os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'], files))
            ) else None
    
    return json.dumps(existing_files)

@video_gabung_bp.route('/api/remove_file', methods=['POST'])
def remove_file():
    """API untuk menghapus file tertentu"""
    data = request.get_json()
    file_type = data.get('type')
    filename = data.get('filename')
    
    if not file_type or not filename:
        return json.dumps({'success': False, 'error': 'Missing parameters'})
    
    if 'uploaded_files' not in session:
        return json.dumps({'success': False, 'error': 'No session found'})
    
    # Remove file from session
    if file_type == 'subtitle':
        if session['uploaded_files']['subtitle'] == filename:
            session['uploaded_files']['subtitle'] = None
    else:
        if filename in session['uploaded_files'][file_type + 's']:
            session['uploaded_files'][file_type + 's'].remove(filename)
    
    # Remove file from disk
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        safe_remove(file_path)
    
    session.modified = True
    return json.dumps({'success': True})

@video_gabung_bp.route('/api/clear_all_files', methods=['POST'])
def clear_all_files():
    """API untuk menghapus semua file"""
    if 'uploaded_files' not in session:
        return json.dumps({'success': False, 'error': 'No session found'})
    
    # Remove all files from disk
    for file_type, files in session['uploaded_files'].items():
        if isinstance(files, list):
            for filename in files:
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(file_path):
                    safe_remove(file_path)
        elif files:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], files)
            if os.path.exists(file_path):
                safe_remove(file_path)
    
    # Clear session
    session['uploaded_files'] = {
        'videos': [],
        'images': [],
        'audios': [],
        'subtitle': None
    }
    session.modified = True
    
    return json.dumps({'success': True})

@video_gabung_bp.route('/api/music_callback', methods=['POST'])
def music_callback():
    data = request.json
    print('Callback musik diterima:', data)
    audio_url = data.get('audio_url') or data.get('result', {}).get('url') or data.get('url')
    # Ambil project_id dari query string
    project_id = request.args.get('project_id')
    if audio_url and project_id:
        audio_filename = f'ai_music_{uuid.uuid4().hex}.mp3'
        audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], audio_filename)
        audio_resp = requests.get(audio_url)
        with open(audio_path, 'wb') as f:
            f.write(audio_resp.content)
        print(f'File musik AI disimpan: {audio_filename}')
        # Gabungkan ke video project terkait (demo: print log)
        project_file = os.path.join(current_app.config['UPLOAD_FOLDER'], f'project_{project_id}.json')
        if os.path.exists(project_file):
            with open(project_file, 'r') as f:
                project_data = json.load(f)
            # Tambahkan audio baru ke list audio_files
            project_data['audio_files'].append(audio_filename)
            # Jalankan proses penggabungan video baru
            result_filename = process_files(project_data['video_files'], project_data['image_files'], project_data['audio_files'], project_id, 'AI')
            print(f'Video baru dengan musik AI digabungkan: {result_filename}')
    return '', 200

@video_gabung_bp.route('/api/upload_file', methods=['POST'])
def api_upload_file():
    try:
        print('UPLOAD DEBUG: request.files =', request.files)
        print('UPLOAD DEBUG: request.form =', request.form)
        if 'uploaded_files' not in session:
            session['uploaded_files'] = {
                'videos': [],
                'images': [],
                'audios': [],
                'subtitle': None
            }
        file_type = request.form.get('type')
        file = request.files.get('file')
        print('UPLOAD DEBUG: file_type =', file_type)
        print('UPLOAD DEBUG: file =', file)
        if not file_type or not file:
            print('UPLOAD ERROR: Missing file or type')
            return jsonify({'success': False, 'error': 'Missing file or type'}), 400

        # Tentukan ekstensi dan validasi
        if file_type == 'video' and allowed_video_file(file.filename):
            filename = secure_filename(f'video_{uuid.uuid4().hex}.mp4')
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            session['uploaded_files']['videos'].append(filename)
        elif file_type == 'image' and allowed_image_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f'image_{uuid.uuid4().hex}.{ext}')
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            session['uploaded_files']['images'].append(filename)
        elif file_type == 'audio' and allowed_audio_file(file.filename):
            filename = secure_filename(f'audio_{uuid.uuid4().hex}.mp3')
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            session['uploaded_files']['audios'].append(filename)
        elif file_type == 'subtitle' and file.filename.endswith('.srt'):
            filename = secure_filename(f'subtitle_{uuid.uuid4().hex}.srt')
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            session['uploaded_files']['subtitle'] = filename
        else:
            print('UPLOAD ERROR: Invalid file type or extension:', file_type, file.filename)
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        session.modified = True
        print('UPLOAD SUCCESS:', filename)
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        print('UPLOAD ERROR:', e)
        return jsonify({'success': False, 'error': str(e)}), 500

@video_gabung_bp.route('/api/gallery')
def api_gallery():
    tipe = request.args.get('type')
    result = []
    if tipe == 'video':
        # Ambil 15 video terbaru saja untuk performa lebih cepat
        videos = Video.query.order_by(Video.created_at.desc()).limit(15).all()
        for v in videos:
            result.append({'src': v.video_url, 'name': v.caption or v.video_url, 'id': v.id})
    elif tipe == 'image':
        # Ambil 15 gambar terbaru saja untuk performa lebih cepat
        images = Image.query.order_by(Image.created_at.desc()).limit(15).all()
        for img in images:
            result.append({'src': img.image_url, 'name': img.caption or img.image_url, 'id': img.id})
    elif tipe == 'audio':
        # Ambil 15 audio terbaru saja untuk performa lebih cepat
        songs = Song.query.order_by(Song.created_at.desc()).limit(15).all()
        for s in songs:
            # Cek image_url dari database
            image_url = s.image_url
            # Jika tidak ada, cek file dengan nama sama di folder audio
            if not image_url and s.audio_url:
                import os
                audio_path = s.audio_url
                base, _ = os.path.splitext(audio_path)
                for ext in ['.jpg', '.png', '.jpeg']:
                    img_path = base + ext
                    # Asumsi path relatif ke /static/uploads/ atau /static/audio_results/
                    static_path = img_path.replace('/uploads/', '/static/uploads/').replace('/audio_results/', '/static/audio_results/')
                    if os.path.exists(os.path.join('backend/static', static_path.strip('/'))):
                        image_url = static_path
                        break
            # Jika tetap tidak ada, pakai default
            if not image_url:
                image_url = '/static/assets/image/default.jpg'
            result.append({'src': s.audio_url, 'name': s.title or s.audio_url, 'id': s.id, 'image_url': image_url})
    return jsonify(result)

@video_gabung_bp.route('/api/list_videos_db')
def list_videos_db():
    try:
        print('=== API LIST VIDEOS DB ===')
        print(f'Request from: {request.remote_addr}')
        
        # Cek apakah database connection berfungsi
        try:
            # Ambil 4 video terbaru saja untuk performa optimal
            videos = VideoIklan.query.order_by(VideoIklan.created_at.desc()).limit(4).all()
            print(f'Found {len(videos)} videos in database')
        except Exception as db_error:
            print(f'Database error: {db_error}')
            return jsonify({'error': f'Database error: {str(db_error)}'}), 500
        
        result = []
        for v in videos:
            try:
                print(f'Processing video ID: {v.id}, URL: {v.video_url}')
                # Pastikan video_url adalah string, bukan bytes
                video_url = v.video_url
                if isinstance(video_url, bytes):
                    video_url = video_url.decode('utf-8')
                
                result.append({
                    'id': v.id,
                    'caption': v.caption or '',
                    'created_at': v.created_at.strftime('%Y-%m-%d %H:%M') if v.created_at else '',
                    'video_url': video_url or ''
                })
                print(f'Added video to result: {v.id}')
            except Exception as e:
                print(f'Error processing video {v.id}: {e}')
                continue
        
        print(f'Returning {len(result)} videos')
        print(f'Response: {result}')
        return jsonify(result)
    except Exception as e:
        print(f'Error in list_videos_db: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Gagal memuat daftar video'}), 500

@video_gabung_bp.route('/api/test_db')
def test_db():
    """Test endpoint untuk cek database"""
    try:
        print('=== TEST DATABASE ===')
        # Cek total video di database
        total_videos = VideoIklan.query.count()
        print(f'Total videos in database: {total_videos}')
        
        # Cek video terbaru
        latest_videos = VideoIklan.query.order_by(VideoIklan.created_at.desc()).limit(5).all()
        print(f'Latest {len(latest_videos)} videos:')
        for v in latest_videos:
            print(f'  ID: {v.id}, URL: {v.video_url}, Created: {v.created_at}')
        
        return jsonify({
            'total_videos': total_videos,
            'latest_videos': [
                {
                    'id': v.id,
                    'video_url': v.video_url.decode('utf-8') if isinstance(v.video_url, bytes) else v.video_url,
                    'created_at': v.created_at.strftime('%Y-%m-%d %H:%M') if v.created_at else None
                }
                for v in latest_videos
            ]
        })
    except Exception as e:
        print(f'Test DB error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@video_gabung_bp.route('/stream/<int:video_id>')
def stream_video_db(video_id):
    video = VideoIklan.query.get(video_id)
    if not video or not video.video_url:
        from flask import abort
        abort(404)
    
    # Pastikan filename string dan bersih
    filename = video.video_url
    if isinstance(filename, bytes):
        filename = filename.decode('utf-8')
    filename = filename.strip() if filename else None
    
    if not filename:
        print(f'Invalid filename for video {video_id}')
        abort(404)
    
    # Cek apakah file exists
    file_path = os.path.join(current_app.config['RESULT_FOLDER'], filename)
    if not os.path.exists(file_path):
        print(f'Video file not found: {file_path}')
        abort(404)
    
    # Stream video dengan proper headers untuk video playback
    response = send_from_directory(current_app.config['RESULT_FOLDER'], filename)
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Content-Type'] = 'video/mp4'
    response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache untuk 1 jam
    return response

def create_video_gabung_blueprint():
    return video_gabung_bp

if __name__ == '__main__':
    current_app.run(debug=True)