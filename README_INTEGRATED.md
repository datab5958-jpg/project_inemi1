# INEMI Landing Page - MySQL Integration

Landing page modern dan futuristik yang terintegrasi dengan database MySQL yang sudah ada.

## 🚀 Features

- **Dynamic Content Loading**: Mengambil gambar dan musik dari database MySQL
- **Modern Futuristic UI**: Desain gelap dengan efek glassmorphism dan gradient
- **3D Animations**: Animasi 3D yang smooth dengan optimasi GPU (60 FPS)
- **Real-time Statistics**: Counter animasi yang menampilkan statistik database
- **Responsive Design**: Tampilan optimal di semua perangkat
- **Performance Optimized**: Menggunakan `will-change`, `transform`, dan `opacity` untuk animasi GPU

## 📋 Prerequisites

- Python 3.8+
- MySQL Server
- Database INEMI yang sudah ada dengan tabel:
  - `images` (dengan kolom: id, user_id, caption, image_url, created_at, model_name)
  - `songs` (dengan kolom: id, user_id, title, prompt, audio_url, image_url, duration, created_at, model_name)
  - `users` (dengan kolom: id, username, avatar_url)

## 🛠️ Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Database**
   - Pastikan MySQL server berjalan
   - Update konfigurasi database di `backend/app_integrated.py`:
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@localhost/database_name'
   ```

3. **Run Application**
   ```bash
   python run_integrated_app.py
   ```

## 🌐 API Endpoints

### Landing Page
- `GET /` - Halaman landing utama

### Content APIs
- `GET /api/landing/images` - Mengambil gambar dari database
  - Parameters: `page`, `per_page`, `category`, `featured`
- `GET /api/landing/music` - Mengambil musik dari database
  - Parameters: `page`, `per_page`, `genre`, `featured`

### Metadata APIs
- `GET /api/landing/categories` - Daftar kategori gambar
- `GET /api/landing/genres` - Daftar genre musik
- `GET /api/landing/stats` - Statistik database

### System APIs
- `GET /health` - Health check
- `GET /api/database-info` - Informasi database

## 🎨 UI Features

### Modern Design Elements
- **Glassmorphism**: Efek kaca dengan backdrop-filter
- **Gradient Backgrounds**: Gradien multi-warna yang dinamis
- **3D Card Effects**: Kartu dengan efek 3D dan hover animations
- **Neon Accents**: Aksen neon dengan glow effects
- **Smooth Transitions**: Transisi halus dengan cubic-bezier

### Performance Optimizations
- **GPU Acceleration**: Menggunakan `transform` dan `opacity`
- **Will-change Property**: Optimasi untuk elemen yang sering dianimasikan
- **Lazy Loading**: Loading konten secara bertahap
- **RequestAnimationFrame**: Animasi yang sinkron dengan refresh rate
- **Intersection Observer**: Monitoring performa dan lazy loading

### Responsive Design
- **Mobile First**: Desain yang dioptimalkan untuk mobile
- **Flexible Grid**: Grid system yang responsif
- **Adaptive Typography**: Ukuran font yang menyesuaikan layar
- **Touch Friendly**: Interface yang mudah digunakan di touch screen

## 📊 Database Integration

### Automatic Category Detection
Sistem secara otomatis mendeteksi kategori gambar berdasarkan:
- Caption content analysis
- Model name patterns
- Keyword matching

### Genre Classification
Genre musik ditentukan berdasarkan:
- Model name analysis
- Prompt content
- Audio characteristics

### Statistics Tracking
- Total content count
- User statistics
- Recent activity
- Category distribution

## 🔧 Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=mysql+pymysql://user:pass@localhost/db

# Security
SECRET_KEY=your-secret-key

# Flask
FLASK_ENV=development
FLASK_DEBUG=True
```

### Performance Settings
```javascript
// Animation settings
const ANIMATION_SETTINGS = {
  duration: 0.6,
  ease: "power3.out",
  stagger: 0.1
};

// Performance monitoring
const PERFORMANCE_CONFIG = {
  targetFPS: 60,
  adaptiveScaling: true,
  maxConcurrentAnimations: 10
};
```

## 🎯 Usage Examples

### Load Images with Filtering
```javascript
// Load images by category
fetch('/api/landing/images?category=Portrait&page=1&per_page=8')
  .then(response => response.json())
  .then(data => {
    // Handle image data
    data.data.forEach(image => {
      console.log(image.title, image.image_url);
    });
  });
```

### Get Statistics
```javascript
// Load landing page statistics
fetch('/api/landing/stats')
  .then(response => response.json())
  .then(data => {
    // Update UI with statistics
    updateStatElement('total-content', data.data.total_content);
    updateStatElement('total-users', data.data.total_users);
  });
```

## 🚀 Performance Tips

1. **Database Optimization**
   - Index pada kolom `created_at`, `user_id`
   - Limit query results dengan pagination
   - Cache frequently accessed data

2. **Frontend Optimization**
   - Gunakan WebP/AVIF untuk gambar
   - Implement lazy loading
   - Minimize DOM manipulations
   - Use CSS transforms instead of position changes

3. **Animation Performance**
   - Prefer `transform` and `opacity`
   - Use `will-change` sparingly
   - Limit concurrent animations
   - Monitor FPS with DevTools

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```
   Error: Can't connect to MySQL server
   ```
   - Check MySQL server status
   - Verify connection credentials
   - Ensure database exists

2. **No Content Loading**
   ```
   API returns empty data
   ```
   - Check database tables exist
   - Verify data in tables
   - Check API endpoint URLs

3. **Performance Issues**
   ```
   Low FPS or laggy animations
   ```
   - Reduce animation complexity
   - Check browser DevTools
   - Enable performance monitoring

### Debug Mode
```bash
# Enable debug logging
export FLASK_DEBUG=1
python run_integrated_app.py
```

## 📈 Monitoring

### Performance Metrics
- FPS monitoring
- Animation performance
- Database query time
- API response time

### Health Checks
- Database connectivity
- API endpoint availability
- Content loading status
- Error rate monitoring

## 🔄 Updates

### Version History
- **v1.0.0**: Initial release with MySQL integration
- **v1.1.0**: Added 3D animations and performance optimizations
- **v1.2.0**: Enhanced UI with glassmorphism effects

### Future Enhancements
- Real-time content updates
- Advanced filtering options
- User authentication integration
- Content recommendation system

## 📞 Support

Untuk bantuan dan pertanyaan:
- Check troubleshooting section
- Review API documentation
- Monitor console logs
- Check database connectivity

---

**INEMI Landing Page** - Modern, Fast, and Beautiful 🚀
