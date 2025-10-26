import json
import logging
import requests
from typing import Dict, Any, Optional
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiChatService:
    """Service untuk berinteraksi dengan Gemini Flash API"""
    
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.base_url = Config.GEMINI_API_URL
        self.headers = {
            "Content-Type": "application/json",
        }
    
    def _make_gemini_request(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """Membuat request ke Gemini Flash API"""
        try:
            # Gabungkan system prompt dengan user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": full_prompt
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
            
            url = f"{self.base_url}?key={self.api_key}"
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    return result['candidates'][0]['content']['parts'][0]['text']
                else:
                    logger.error("No candidates in Gemini response")
                    return None
            else:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error making Gemini request: {str(e)}")
            return None
    
    def analyze_image_for_music(self, image_base64: str) -> Dict[str, Any]:
        """Menganalisis gambar dan menghasilkan deskripsi + lirik musik yang mendalam"""
        system_prompt = (
            "Anda adalah seorang penulis lagu profesional yang ahli menganalisis gambar dan menciptakan lirik musik yang mendalam.\n\n"
            "TUGAS: Analisis gambar ini dengan detail dan buatkan lirik musik yang benar-benar mencerminkan apa yang Anda lihat.\n\n"
            "PENTING: SEMUA OUTPUT HARUS DALAM BAHASA INDONESIA!\n\n"
            "LANGKAH ANALISIS:\n"
            "1. Perhatikan dengan seksama semua elemen visual: objek utama, warna dominan, suasana, emosi yang terpancar\n"
            "2. Identifikasi cerita atau pesan yang tersembunyi dalam gambar\n"
            "3. Rasakan mood dan atmosfer yang diciptakan gambar\n"
            "4. Tentukan genre musik yang paling cocok dengan visual dan mood\n\n"
            "FORMAT OUTPUT:\n"
            "Deskripsi: [Jelaskan secara detail dalam bahasa Indonesia apa yang terlihat dalam gambar - objek, warna, suasana, emosi]\n"
            "Mood: [Suasana emosional yang tepat untuk musik dalam bahasa Indonesia - contoh: melankolis, energik, romantis, misterius, nostalgia]\n"
            "Genre: [Genre musik yang sesuai dalam bahasa Indonesia - contoh: Pop Ballad, Folk Akustik, Rock Alternative, Jazz Blues]\n"
            "Lirik:\n"
            "(Verse 1)\n"
            "[4-6 baris lirik dalam bahasa Indonesia yang menggambarkan scene atau objek utama dalam gambar]\n\n"
            "(Chorus)\n"
            "[4-6 baris lirik dalam bahasa Indonesia yang menangkap emosi dan pesan inti dari gambar]\n\n"
            "(Verse 2)\n"
            "[4-6 baris lirik dalam bahasa Indonesia yang melanjutkan cerita atau mendalami makna gambar]\n\n"
            "(Bridge)\n"
            "[2-4 baris lirik dalam bahasa Indonesia yang memberikan perspektif baru atau klimaks emosional]\n\n"
            "PETUNJUK PENULISAN LIRIK:\n"
            "- WAJIB menggunakan bahasa Indonesia yang puitis dan bermakna\n"
            "- Lirik harus spesifik sesuai dengan apa yang terlihat di gambar (JANGAN GENERIK)\n"
            "- Ciptakan narasi yang koheren dan emosional berdasarkan elemen visual dalam foto\n"
            "- Gunakan metafora dan imagery yang kuat yang terkait dengan gambar\n"
            "- Hindari lirik yang terlalu umum atau klise\n"
            "- Pastikan lirik bisa dinyanyikan dengan baik\n"
            "- Deskripsi harus detail dan akurat sesuai dengan foto yang diupload\n\n"
            "Buatlah lirik yang benar-benar unik dan personal sesuai gambar ini dalam bahasa Indonesia!"
        )
        
        try:
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": system_prompt
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_base64
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
            
            url = f"{self.base_url}?key={self.api_key}"
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    analysis_text = result['candidates'][0]['content']['parts'][0]['text']
                    return {
                        "success": True,
                        "analysis": analysis_text.strip(),
                        "type": "image_to_music"
                    }
                else:
                    logger.error("No candidates in Gemini vision response")
                    return {
                        "success": False,
                        "error": "Tidak ada respons dari AI"
                    }
            else:
                logger.error(f"Gemini Vision API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"Error dari AI: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            return {
                "success": False,
                "error": f"Error menganalisis gambar: {str(e)}"
            }

    def generate_music_prompt(self, user_input: str, file_urls: list = None) -> Dict[str, Any]:
        """Menghasilkan lagu lengkap (judul, genre, mood, instrumen, lirik, durasi) dalam bahasa Indonesia"""
        system_prompt = (
            "Anda adalah AI penulis lagu profesional. Dari permintaan user, buatkan satu usulan lagu lengkap yang terdiri dari:\n"
            "Judul lagu: (satu baris)\n"
            "Genre: (sangat spesifik dan siap pakai, misal: Indonesian Pop Ballad, Folk Melayu Jambi, Modern Dangdut, Jambi Ethnic Fusion, dsb)\n"
            "Mood: (singkat, koma dipisah)\n"
            "Instrumen: (singkat, koma dipisah)\n"
            "Lirik: (minimal 2 verse, 1 chorus, dan jika memungkinkan tambahkan pre-chorus, bridge, chorus outro. Setiap bagian harus diberi label, misal: (Verse 1), (Pre-Chorus), (Chorus), (Verse 2), (Bridge), (Chorus Outro). Beri 1 baris kosong antar bagian agar tidak dempet. Lirik dalam bahasa Indonesia, pastikan lirik tidak terpotong dan selesai.)\n"
            "Durasi: (jika disebutkan)\n"
            "Tampilkan hasil dalam urutan di atas, tanpa tanda bintang, tanpa markdown, tanpa format tebal, hanya plain text, rapi, dan mudah di-copy-paste ke aplikasi lain.\n"
            "Jangan beri penjelasan tambahan, opsi, atau catatan. Hanya hasil lagu."
        )
        
        # Jika ada file_urls, tambahkan informasi file ke prompt
        if file_urls:
            file_info = f"\n\nFile yang dilampirkan: {', '.join(file_urls)}"
            user_prompt = f"{user_input}{file_info}"
        else:
            user_prompt = f"{user_input}"
            
        result = self._make_gemini_request(user_prompt, system_prompt)
        if result:
            return {
                "success": True,
                "prompt": result.strip(),
                "type": "music",
                "original_input": user_input
            }
        else:
            return {
                "success": False,
                "error": "Gagal menghasilkan lagu",
                "type": "music",
                "original_input": user_input
            }
    
    def generate_video_prompt(self, user_input: str, file_urls: list = None) -> Dict[str, Any]:
        """Menghasilkan prompt video yang akurat"""
        system_prompt = """Anda adalah ahli pembuatan video yang spesialis dalam membuat prompt untuk AI video generator.
        
        Tugas Anda adalah mengubah deskripsi video dari user menjadi prompt yang optimal untuk AI video generator.
        
        Format yang diharapkan:
        - Style visual (realistic, cartoon, anime, cinematic, etc.)
        - Setting/lokasi yang jelas
        - Aksi/gerakan yang spesifik
        - Lighting dan mood
        - Camera angle dan movement
        - Durasi (jika disebutkan)
        
        Contoh format output:
        "Cinematic shot of a person walking through a forest at sunset, golden hour lighting, slow motion, wide angle shot, realistic style, 10 seconds"
        
        Pastikan prompt:
        1. Spesifik dan detail
        2. Menggunakan bahasa Inggris yang jelas
        3. Mencakup semua elemen visual yang penting
        4. Sesuai dengan kemampuan AI video generator"""
        
        # Jika ada file_urls, tambahkan informasi file ke prompt
        if file_urls:
            file_info = f"\n\nFile yang dilampirkan: {', '.join(file_urls)}"
            user_prompt = f"Buatkan prompt video yang akurat untuk: {user_input}{file_info}"
        else:
            user_prompt = f"Buatkan prompt video yang akurat untuk: {user_input}"
        
        result = self._make_gemini_request(user_prompt, system_prompt)
        
        if result:
            return {
                "success": True,
                "prompt": result.strip(),
                "type": "video",
                "original_input": user_input
            }
        else:
            return {
                "success": False,
                "error": "Gagal menghasilkan prompt video",
                "type": "video",
                "original_input": user_input
            }
    
    def generate_photo_prompt(self, user_input: str, file_urls: list = None) -> Dict[str, Any]:
        """Menghasilkan prompt foto yang akurat dalam Bahasa Indonesia dengan detail lengkap"""
        system_prompt = """Anda adalah ahli fotografi profesional yang mengkhususkan diri dalam membuat prompt detail untuk AI image generator.
        
        TUGAS ANDA adalah mengubah deskripsi foto dari pengguna menjadi prompt yang komprehensif, detail, dan dioptimalkan untuk AI image generation.
        
        PENTING - SYARAT WAJIB:
        1. Output HARUS dalam BAHASA INDONESIA
        2. Buat SANGAT DETAIL dan LENGKAP (200-300 kata)
        3. Sertakan SEMUA elemen visual: subjek, gaya, komposisi, pencahayaan, suasana, warna, latar belakang, kualitas
        4. Gunakan terminologi fotografi profesional
        5. Optimalkan untuk hasil AI generation terbaik
        
        STRUKTUR PROMPT:
        - Deskripsi subjek utama (detail)
        - Gaya artistik dan teknik
        - Komposisi dan framing
        - Setup pencahayaan dan suasana
        - Palet warna dan atmosfer
        - Latar belakang dan lingkungan
        - Spesifikasi kualitas teknis
        - Detail artistik tambahan
        
        CONTOH FORMAT OUTPUT:
        "Potret fotorealistik ultra-detail seorang wanita muda dengan rambut cokelat kemerahan yang mengalir, mengenakan gaun sutra hijau zamrud yang elegan, berdiri dengan anggun di taman Victoria yang diterangi matahari. Pencahayaan golden hour menciptakan bayangan dramatis yang hangat di wajahnya, menyoroti mata hijau yang mencolok dan bintik-bintik alami. Kedalaman bidang yang dangkal dengan latar belakang menampilkan semak mawar yang subur, jalan setapak batu, dan elemen arsitektur yang jauh. Komposisi mengikuti aturan sepertiga, dengan subjek diposisikan sedikit di luar tengah. Palet warna yang kaya dan jenuh dengan hijau zamrud, emas hangat, dan cokelat gelap. Kualitas fotografi profesional resolusi tinggi dengan detail 8K, pencahayaan sempurna, komposisi studio-grade, atmosfer sinematik, dan estetika layak majalah. Suasana keseluruhan adalah elegan, canggih, dan abadi."
        
        Pastikan prompt:
        1. Sangat detail dan deskriptif
        2. Ditulis dalam bahasa Indonesia yang profesional
        3. Mencakup semua aspek visual secara komprehensif
        4. Dioptimalkan untuk AI image generation
        5. Siap pakai segera tanpa modifikasi"""
        
        # Jika ada file_urls, tambahkan informasi file ke prompt
        if file_urls:
            file_info = f"\n\nFile yang dilampirkan: {', '.join(file_urls)}"
            user_prompt = f"Buatkan prompt foto yang akurat untuk: {user_input}{file_info}"
        else:
            user_prompt = f"Buatkan prompt foto yang akurat untuk: {user_input}"
        
        result = self._make_gemini_request(user_prompt, system_prompt)
        
        if result:
            return {
                "success": True,
                "prompt": result.strip(),
                "type": "photo",
                "original_input": user_input
            }
        else:
            # Fallback prompt jika Gemini API error atau quota exceeded
            fallback_prompt = f"Gambar fotorealistik ultra-detail dari {user_input}, kualitas fotografi profesional, pencahayaan sempurna, komposisi studio-grade, atmosfer sinematik, resolusi tinggi, detail, kualitas 8K, estetika layak majalah, warna alami, fokus tajam, kamera profesional, fotografi pemenang penghargaan"
            return {
                "success": True,
                "prompt": fallback_prompt,
                "type": "photo",
                "original_input": user_input,
                "note": "Menggunakan prompt fallback karena error API"
            }
    
    def generate_fusigaya_prompt(self, user_input: str, file_urls: list = None) -> Dict[str, Any]:
        """Menghasilkan prompt fusigaya yang singkat, jelas, dan efektif untuk FLUX.1 Kontext dalam bahasa Indonesia"""
        system_prompt = """Anda adalah ahli AI image editing profesional yang mengkhususkan diri dalam FLUX.1 Kontext style fusion dan transformasi gambar.
        
        TUGAS ANDA adalah membuat prompt yang DETAIL tapi PRAKTIS untuk FLUX.1 Kontext yang akan mengubah gambar sesuai permintaan pengguna.
        
        PENTING - SYARAT WAJIB:
        1. Output HARUS dalam BAHASA INDONESIA
        2. Buat DETAIL dan SPESIFIK (30-60 kata)
        3. Fokus pada INSTRUKSI JELAS dengan DETAIL SPESIFIK
        4. Buat SATU prompt yang siap pakai segera
        5. Sertakan elemen gaya, warna, dan detail transformasi yang spesifik
        6. Buat cukup detail untuk mencapai hasil yang diinginkan
        
        STRUKTUR PROMPT UNTUK FLUX.1 KONCONTEXT:
        Buat SATU prompt detail yang:
        - Memberikan instruksi jelas untuk apa yang harus diubah
        - Menentukan gaya, warna, dan elemen yang diinginkan
        - Sertakan detail spesifik untuk transformasi yang akurat
        - Mudah untuk FLUX.1 Kontext eksekusi
        - Menghasilkan transformasi gambar yang natural dan realistis
        
        CONTOH FORMAT OUTPUT (DETAIL TAPI PRAKTIS):
        - "Ubah kemeja putih pria menjadi kemeja batik merah tradisional dengan desain elang emas, pertahankan latar belakang asli"
        - "Transformasi potret ke gaya Klimt Art Nouveau dengan pola daun emas, elemen dekoratif mengalir, dan nada perunggu yang kaya"
        - "Ubah gaun wanita menjadi gaun malam merah yang elegan dengan detail renda dan hiasan mutiara"
        - "Buat latar belakang menjadi pemandangan pantai matahari terbenam dengan langit oranye, pohon kelapa, dan ombak laut"
        - "Transformasi ke gaya anime dengan mata ekspresif besar, rambut berwarna-warni, dan proporsi seperti kartun"
        - "Ubah ke gaya lukisan minyak dengan goresan kuas yang terlihat, tekstur kaya, dan estetika seni klasik"
        
        Pastikan prompt:
        1. DETAIL dan SPESIFIK (30-60 kata)
        2. JELAS dan DESKRIPTIF
        3. Sertakan elemen gaya dan warna yang spesifik
        4. Mudah dipahami dan eksekusi
        5. Menghasilkan transformasi yang akurat
        6. Siap pakai segera dengan FLUX.1 Kontext"""
        
        # Jika ada file_urls, tambahkan informasi file ke prompt
        if file_urls:
            file_info = f"\n\nSource images provided: {', '.join(file_urls)}. Analyze the uploaded image and create a DETAILED but PRACTICAL prompt (30-60 words) for FLUX.1 Kontext that includes specific style elements, colors, and transformation details. Output ONLY ONE detailed prompt, no long descriptions."
            user_prompt = f"Create a DETAILED FLUX.1 Kontext prompt for: {user_input}{file_info}"
        else:
            user_prompt = f"Create a DETAILED FLUX.1 Kontext prompt for: {user_input}. Output ONLY ONE detailed prompt (30-60 words) with specific style elements and colors."
        
        result = self._make_gemini_request(user_prompt, system_prompt)
        
        if result:
            return {
                "success": True,
                "prompt": result.strip(),
                "type": "fusigaya",
                "original_input": user_input
            }
        else:
            # Fallback prompt jika Gemini API error atau quota exceeded
            fallback_prompt = f"Transformasi gambar ini ke gaya {user_input} dengan elemen artistik yang detail, mempertahankan komposisi dan pencahayaan asli untuk hasil fusion yang natural"
            return {
                "success": True,
                "prompt": fallback_prompt,
                "type": "fusigaya",
                "original_input": user_input,
                "note": "Menggunakan prompt fallback karena error API"
            }
    
    def generate_general_prompt(self, user_input: str, prompt_type: str) -> Dict[str, Any]:
        """Menghasilkan prompt umum berdasarkan tipe yang diminta"""
        if prompt_type.lower() == "music":
            return self.generate_music_prompt(user_input)
        elif prompt_type.lower() == "video":
            return self.generate_video_prompt(user_input)
        elif prompt_type.lower() == "photo":
            return self.generate_photo_prompt(user_input)
        elif prompt_type.lower() == "fusigaya":
            return self.generate_fusigaya_prompt(user_input)
        else:
            return {
                "success": False,
                "error": f"Tipe prompt '{prompt_type}' tidak didukung. Gunakan 'music', 'video', 'photo', atau 'fusigaya'",
                "type": prompt_type,
                "original_input": user_input
            }
    
    def generate_negative_prompt(self, user_input: str, prompt_type: str = 'image') -> Dict[str, Any]:
        """Menghasilkan negative prompt yang optimal untuk AI image generation dalam bahasa Indonesia"""
        system_prompt = """Anda adalah ahli AI image generation yang mengkhususkan diri dalam membuat negative prompt yang efektif.
        
        TUGAS ANDA adalah menghasilkan negative prompt yang komprehensif yang akan membantu menghindari masalah umum AI generation dan meningkatkan kualitas gambar.
        
        PENTING - SYARAT WAJIB:
        1. Output HARUS dalam BAHASA INDONESIA
        2. Output HANYA negative prompt, TIDAK ADA kalimat penjelas
        3. Fokus pada kualitas teknis dan menghindari masalah umum
        4. Sertakan semua elemen negatif yang relevan
        5. Optimalkan untuk hasil AI generation terbaik
        
        STRUKTUR NEGATIVE PROMPT:
        - Indikator kualitas rendah (blur, noise, distorsi, dll)
        - Gaya artistik yang tidak diinginkan
        - Masalah teknis yang harus dihindari
        - Masalah komposisi
        - Masalah pencahayaan
        - Masalah warna
        - Masalah anatomi (untuk potret)
        - Masalah latar belakang
        
        CONTOH FORMAT OUTPUT (HANYA PROMPT, TIDAK ADA PENJELASAN):
        "blur, noise, distorsi, kualitas rendah, resolusi rendah, pixelated, artefak jpeg, tidak fokus, fokus lembut, overexposed, underexposed, anatomi buruk, cacat, cacat bentuk, wajah yang digambar buruk, tangan bermutasi, jari bermutasi, anggota tubuh ekstra, anggota tubuh hilang, anggota tubuh mengambang, anggota tubuh terputus, tangan cacat, blur, tidak fokus, leher panjang, tubuh panjang, tangan dan jari bermutasi, keluar frame, blender, boneka, terpotong, resolusi rendah, close-up, wajah yang digambar buruk, frame ganda, dua kepala, blur, jelek, cacat, terlalu banyak jari, cacat, berulang, hitam putih, berbutir, anggota tubuh ekstra, anatomi buruk, filter high pass, airbrush, potret, zoom, cahaya lembut, kulit halus, closeup, cacat, anggota tubuh ekstra, jari ekstra, tangan bermutasi, anatomi buruk, proporsi buruk, buta, mata buruk, mata jelek, mata mati, blur, vignette, keluar shot, tidak fokus, gaussian, closeup, monokrom, berbutir, berisik, teks, watermarked, logo, watermark"
        
        PENTING: Output HANYA negative prompt dalam bahasa Indonesia, TIDAK ADA kalimat penjelas, deskripsi, atau instruksi tambahan."""
        
        user_prompt = f"Buatkan negative prompt yang komprehensif untuk: {user_input}. Output HANYA negative prompt dalam bahasa Indonesia, TIDAK ADA kalimat penjelas atau deskripsi tambahan."
        
        result = self._make_gemini_request(user_prompt, system_prompt)
        if result:
            return {
                "success": True,
                "negative_prompt": result.strip(),
                "type": "negative_prompt",
                "original_input": user_input
            }
        else:
            # Fallback negative prompt jika Gemini API error
            fallback_negative = "blur, noise, distorsi, kualitas rendah, resolusi rendah, pixelated, artefak jpeg, tidak fokus, fokus lembut, overexposed, underexposed, anatomi buruk, cacat, cacat bentuk, wajah yang digambar buruk, tangan bermutasi, jari bermutasi, anggota tubuh ekstra, anggota tubuh hilang, anggota tubuh mengambang, anggota tubuh terputus, tangan cacat, blur, tidak fokus, leher panjang, tubuh panjang, tangan dan jari bermutasi, keluar frame, blender, boneka, terpotong, resolusi rendah, close-up, wajah yang digambar buruk, frame ganda, dua kepala, blur, jelek, cacat, terlalu banyak jari, cacat, berulang, hitam putih, berbutir, anggota tubuh ekstra, anatomi buruk, filter high pass, airbrush, potret, zoom, cahaya lembut, kulit halus, closeup, cacat, anggota tubuh ekstra, jari ekstra, tangan bermutasi, anatomi buruk, proporsi buruk, buta, mata buruk, mata jelek, mata mati, blur, vignette, keluar shot, tidak fokus, gaussian, closeup, monokrom, berbutir, berisik, teks, watermarked, logo, watermark"
            return {
                "success": True,
                "negative_prompt": fallback_negative,
                "type": "negative_prompt",
                "original_input": user_input,
                "note": "Menggunakan negative prompt fallback karena error API"
            }
    
    def analyze_image_for_fusigaya(self, image_base64: str, user_input: str = "") -> Dict[str, Any]:
        """Menganalisis gambar untuk fusigaya dan menghasilkan prompt FLUX.1 Kontext yang siap pakai dalam bahasa Indonesia"""
        system_prompt = (
            "Anda adalah ahli AI image editing profesional yang mengkhususkan diri dalam transformasi gaya FLUX.1 Kontext.\n\n"
            "TUGAS: Analisis gambar yang diupload dan buat prompt yang DETAIL tapi PRAKTIS untuk FLUX.1 Kontext.\n\n"
            "PENTING - SYARAT WAJIB:\n"
            "1. Output HARUS dalam BAHASA INDONESIA\n"
            "2. Buat DETAIL dan SPESIFIK (30-60 kata)\n"
            "3. Fokus pada INSTRUKSI JELAS dengan DETAIL SPESIFIK\n"
            "4. Buat SATU prompt detail yang siap pakai segera\n"
            "5. Sertakan elemen gaya, warna, dan detail transformasi yang spesifik\n\n"
            "STRUKTUR PROMPT:\n"
            "Buat SATU prompt detail yang:\n"
            "1. Menganalisis gambar yang diupload (apa yang Anda lihat)\n"
            "2. Memberikan instruksi jelas untuk apa yang harus diubah\n"
            "3. Sertakan detail gaya dan warna yang spesifik\n"
            "4. Menghasilkan transformasi yang akurat\n\n"
            "CONTOH FORMAT OUTPUT (DETAIL TAPI PRAKTIS):\n"
            "- \"Ubah kemeja putih pria menjadi kemeja batik merah tradisional dengan desain elang emas, pertahankan latar belakang asli\"\n"
            "- \"Transformasi potret ke gaya Klimt Art Nouveau dengan pola daun emas, elemen dekoratif mengalir, dan nada perunggu yang kaya\"\n"
            "- \"Ubah gaun wanita menjadi gaun malam merah yang elegan dengan detail renda dan hiasan mutiara\"\n\n"
            "PENTING: Output HANYA SATU prompt detail (30-60 kata), tidak ada deskripsi panjang atau bagian terpisah."
        )
        
        try:
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"{system_prompt}\n\nPermintaan pengguna: {user_input if user_input else 'Transformasi gambar ini'}\n\nAnalisis gambar yang diupload dan buat prompt yang DETAIL tapi PRAKTIS (30-60 kata) yang menyertakan elemen gaya, warna, dan detail transformasi yang spesifik. Output HANYA SATU prompt detail, tidak ada deskripsi panjang."
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_base64
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
            
            url = f"{self.base_url}?key={self.api_key}"
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    analysis_text = result['candidates'][0]['content']['parts'][0]['text']
                    return {
                        "success": True,
                        "prompt": analysis_text.strip(),
                        "type": "fusigaya_analysis",
                        "original_input": user_input
                    }
                else:
                    logger.error("No candidates in Gemini vision response for fusigaya")
                    return {
                        "success": False,
                        "error": "Tidak ada respons dari AI"
                    }
            else:
                logger.error(f"Gemini Vision API error for fusigaya: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"Error dari AI: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Error analyzing image for fusigaya: {str(e)}")
            return {
                "success": False,
                "error": f"Error menganalisis gambar: {str(e)}"
            }

# Instance global untuk digunakan di routes
gemini_service = GeminiChatService()

def get_prompt_service():
    """Mengembalikan instance GeminiChatService"""
    return gemini_service 