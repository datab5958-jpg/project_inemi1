# 🎨 Generate Banner AI - Dokumentasi Lengkap

## 📋 **Overview**
Generate Banner AI adalah fitur canggih yang memungkinkan pengguna membuat banner profesional otomatis hanya dari judul, dengan kemampuan deteksi cerdas dan simulasi billboard.

## 🚀 **Fitur Utama**

### 1. **AI Banner Generation**
- Generate banner otomatis hanya dari judul
- Menggunakan AI Banana model yang sudah terintegrasi
- Output resolusi tinggi siap cetak (150 DPI)

### 2. **Smart Detection System**
- Deteksi otomatis ukuran banner dari contoh
- Analisis warna dominan menggunakan K-means clustering
- OCR untuk ekstraksi teks dari banner contoh
- Estimasi ukuran real berdasarkan aspect ratio

### 3. **Multi-File Upload**
- Upload banner contoh (opsional)
- Upload multiple logo/gambar tambahan
- Drag & drop interface yang user-friendly

### 4. **Billboard Simulation**
- Preview banner di mockup billboard
- Background gradient yang menarik
- Simulasi real-world application

### 5. **PDF Export**
- Konversi otomatis ke PDF ukuran real
- Siap cetak dengan dimensi yang tepat
- Download langsung dari browser

## 🛠️ **Teknologi yang Digunakan**

### Backend
- **Flask** - Web framework
- **OpenCV** - Image processing
- **PIL/Pillow** - Image manipulation
- **Tesseract OCR** - Text extraction
- **Scikit-learn** - Color clustering
- **ReportLab** - PDF generation
- **WaveSpeed AI** - Banana AI integration

### Frontend
- **Alpine.js** - Reactive framework
- **Bootstrap 5** - UI components
- **Bootstrap Icons** - Icon library

## 📁 **Struktur File**

```
backend/
├── generate_banner.py          # Main backend logic
├── templates/
│   └── generate_banner.html    # Frontend template
├── app.py                      # Blueprint registration
└── requirements.txt            # Dependencies
```

## 🔧 **Instalasi & Setup**

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Tesseract OCR
```bash
# Windows
# Download dari: https://github.com/UB-Mannheim/tesseract/wiki

# Linux
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract
```

### 3. Environment Variables
Pastikan file `.env` memiliki:
```bash
WAVESPEED_API_KEY=your_api_key_here
DOMAIN_PUBLIC=http://your-domain.com
```

## 🎯 **Cara Penggunaan**

### 1. **Akses Menu**
- Login ke sistem
- Klik menu "Generate Banner" (dengan badge "New")

### 2. **Input Data**
- Masukkan judul banner di field "Judul Banner"
- Upload banner contoh (opsional) - nama file harus mengandung "contoh" atau "example"
- Upload logo/gambar tambahan (opsional)

### 3. **Generate Banner**
- Klik tombol "Generate Banner Otomatis"
- Sistem akan:
  - Menganalisis banner contoh (jika ada)
  - Generate banner menggunakan AI Banana
  - Membuat simulasi billboard
  - Menyiapkan PDF untuk download

### 4. **Download Hasil**
- Preview banner hasil AI
- Lihat simulasi billboard
- Download PDF siap cetak
- Download gambar PNG

## 💰 **Sistem Kredit**

### Perhitungan Kredit
```python
base_credits = 20                    # Base cost
title_credits = min(len(title)//20, 10)  # Max 10 credits
analysis_credits = 15 if has_example else 0  # Banner analysis
extra_credits = extra_files_count * 5       # Per extra file
```

### Contoh Perhitungan
- Judul: "Promo Besar" (12 karakter)
- Banner contoh: Ya
- Extra files: 2 logo
- **Total**: 20 + 0 + 15 + 10 = **45 kredit**

## 🔍 **API Endpoints**

### 1. **GET /generate_banner**
- Halaman utama Generate Banner
- Requires: User login

### 2. **POST /smart_banner**
- Generate banner dengan AI
- Input: title, files (optional)
- Output: request_id untuk polling

### 3. **GET /check_banner_status/<request_id>**
- Check status banner generation
- Output: banner_url, simulation_url

### 4. **GET /download_banner_pdf**
- Download banner sebagai PDF
- Parameters: banner_url, width_m, height_m

## 🎨 **AI Prompt Engineering**

### Default Prompt (Tanpa Contoh)
```
Desain banner profesional dengan teks utama: '{title}'.
Ukuran: 2 x 1 meter (standar billboard).
Gaya: Modern, profesional, mudah dibaca dari jarak jauh.
Warna: Kombinasi biru dan putih yang menarik.
Tambahkan area kosong untuk logo dan QR code.
Hasil dalam resolusi tinggi, siap cetak 150 DPI.
Background gradient atau solid yang menarik.
```

### Enhanced Prompt (Dengan Contoh)
```
Desain banner profesional dengan teks utama: '{title}'.
Ukuran: {width_m} x {height_m} meter.
Gaya: Modern, profesional, mudah dibaca dari jarak jauh.
Warna dominan: {colors}.
Teks yang terdeteksi dari contoh: {detected_text}
Tambahkan area kosong untuk logo dan QR code.
Hasil dalam resolusi tinggi, siap cetak 150 DPI.
Background gradient atau solid yang menarik.
```

## 🔧 **Konfigurasi AI Model**

### Model URLs
```python
model_urls = {
    'nano-banana': "https://api.wavespeed.ai/api/v3/google/nano-banana/edit",
    'flux-kontext-dev': "https://api.wavespeed.ai/api/v3/wavespeed-ai/flux-kontext-dev/multi-ultra-fast",
    'flux-kontext-pro': "https://api.wavespeed.ai/api/v3/wavespeed-ai/flux-kontext-pro/multi"
}
```

### Default Model
- Menggunakan **nano-banana** sebagai default
- Bisa diubah di function `generate_banner_with_banana_ai()`

## 📊 **Deteksi Banner**

### Fungsi `detect_banner_info()`
```python
def detect_banner_info(image_path):
    # 1. Load image dan hitung aspect ratio
    # 2. Estimasi ukuran real berdasarkan ratio
    # 3. K-means clustering untuk warna dominan
    # 4. OCR untuk ekstraksi teks
    # 5. Return structured data
```

### Output Detection
```python
{
    "width_m": 2.0,                    # Estimated width in meters
    "height_m": 1.0,                   # Estimated height in meters
    "dominant_colors": ["#007BFF", "#FFFFFF"],  # Top 3 colors
    "detected_text": "PROMO BESAR",    # Extracted text
    "aspect_ratio": "2.0:1",           # Aspect ratio
    "original_size": "2048x1024"       # Original image size
}
```

## 🎭 **Billboard Simulation**

### Fungsi `create_billboard_simulation()`
- Background gradient biru langit
- Resize banner untuk fit billboard
- Center positioning
- Output: 800x600px simulation image

## 📄 **PDF Generation**

### Fungsi `convert_to_pdf()`
- Calculate PDF dimensions in points
- 150 DPI resolution
- Real-world measurements
- Download-ready format

### PDF Dimensions
```python
width_pt = width_m * 100 * dpi / 2.54  # Convert meters to points
height_pt = height_m * 100 * dpi / 2.54
```

## 🚨 **Error Handling**

### Common Errors
1. **Insufficient Credits** - User tidak punya cukup kredit
2. **API Key Missing** - WAVESPEED_API_KEY tidak dikonfigurasi
3. **File Upload Error** - File tidak valid atau terlalu besar
4. **AI Generation Failed** - Error dari WaveSpeed API

### Error Messages
- User-friendly error messages
- Detailed logging untuk debugging
- Graceful fallback untuk setiap error

## 🔒 **Security Features**

### File Upload Security
- File type validation (PNG, JPG, JPEG, GIF, WEBP)
- File size limits
- Secure filename generation
- Path traversal protection

### User Authentication
- Login required untuk semua endpoints
- Session validation
- Credit system protection

## 📈 **Performance Optimization**

### Polling Strategy
- 3-second intervals untuk status check
- Automatic timeout handling
- Efficient resource cleanup

### Image Processing
- Optimized image resizing
- Memory-efficient file handling
- Temporary file cleanup

## 🧪 **Testing**

### Manual Testing
1. Test dengan judul saja
2. Test dengan banner contoh
3. Test dengan multiple files
4. Test error scenarios
5. Test PDF download

### Test Cases
- Valid input scenarios
- Invalid file types
- Insufficient credits
- API failures
- Network timeouts

## 🚀 **Deployment Notes**

### Production Setup
1. Install Tesseract OCR
2. Configure WAVESPEED_API_KEY
3. Set proper file permissions
4. Configure upload directory
5. Test all endpoints

### Monitoring
- Log all API calls
- Monitor credit usage
- Track generation success rate
- Monitor file upload sizes

## 🔮 **Future Enhancements**

### Planned Features
1. **Template Library** - Pre-made banner templates
2. **Brand Guidelines** - Company-specific styling
3. **Batch Processing** - Multiple banners at once
4. **Advanced Analytics** - Usage statistics
5. **Custom Dimensions** - User-defined sizes
6. **Text Effects** - Shadow, outline, gradient text
7. **Logo Positioning** - Smart logo placement
8. **Color Palette** - Brand color suggestions

### Technical Improvements
1. **Caching** - Redis untuk hasil generation
2. **Queue System** - Background processing
3. **CDN Integration** - Faster file delivery
4. **API Rate Limiting** - Prevent abuse
5. **Webhook Support** - Real-time notifications

## 📞 **Support**

### Troubleshooting
1. Check API key configuration
2. Verify Tesseract installation
3. Check file permissions
4. Monitor server logs
5. Test with minimal input

### Contact
- Developer: AI Assistant
- Documentation: This file
- Issues: Check server logs

---

**🎉 Generate Banner AI siap digunakan! Fitur ini memberikan pengalaman yang seamless untuk membuat banner profesional dengan teknologi AI terdepan.**


