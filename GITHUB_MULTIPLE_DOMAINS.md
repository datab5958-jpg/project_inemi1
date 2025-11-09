# Setup GitHub OAuth untuk Local dan Public Domain

## Masalah
GitHub OAuth perlu bekerja di:
- **Local development**: `http://localhost:5000` dan `http://127.0.0.1:5000`
- **Public domain**: `https://yourdomain.com`

## ⚠️ PENTING: GitHub OAuth App Hanya Mendukung Satu Callback URL

**GitHub OAuth App tidak mendukung multiple callback URLs** (tidak bisa pakai koma atau cara lain). Setiap OAuth App hanya bisa memiliki **satu Authorization callback URL**.

## Solusi: Gunakan Satu URL yang Konsisten

Aplikasi sudah dikonfigurasi untuk menggunakan satu URL yang konsisten:
- **Development**: Selalu menggunakan `http://localhost:5000/auth/github/callback` (meskipun diakses via `127.0.0.1`)
- **Production**: Menggunakan domain production (misalnya `https://inemi.id/auth/github/callback`)

### Langkah 1: Setup untuk Development

1. Buka: https://github.com/settings/developers
2. Klik aplikasi "inemi"
3. Di bagian **"Authorization callback URL"**, isi:
   ```
   http://localhost:5000/auth/github/callback
   ```
4. Klik **"Update application"**
5. Tunggu 10-15 detik

**Cara menggunakan:**
- Akses via `http://localhost:5000/login` → GitHub login bekerja ✅
- Akses via `http://127.0.0.1:5000/login` → Aplikasi otomatis convert ke `localhost` ✅

### Langkah 2: Pastikan Session Configuration Benar

Aplikasi sudah dikonfigurasi untuk:
- Menggunakan `session.permanent = True` untuk persist session
- Menyimpan state token dengan aman
- Menormalisasi host (127.0.0.1 → localhost)

### Langkah 3: Test di Local

1. Buka `http://localhost:5000/login` atau `http://127.0.0.1:5000/login`
2. Klik "Continue with GitHub"
3. Login seharusnya berhasil

### Langkah 4: Test di Production

1. Deploy aplikasi ke production domain
2. Pastikan menggunakan HTTPS
3. Buka `https://yourdomain.com/login`
4. Klik "Continue with GitHub"
5. Login seharusnya berhasil

## Alternatif: Buat OAuth App Terpisah untuk Production

Jika Anda ingin menggunakan local dan production secara bersamaan tanpa mengganti URL:

### Opsi: Buat 2 OAuth Apps Terpisah

1. **OAuth App untuk Development:**
   - Name: `inemi-dev`
   - Callback URL: `http://localhost:5000/auth/github/callback`
   - Client ID: Simpan sebagai `GITHUB_CLIENT_ID_DEV` di `.env`

2. **OAuth App untuk Production:**
   - Name: `inemi-prod`
   - Callback URL: `https://inemi.id/auth/github/callback`
   - Client ID: Simpan sebagai `GITHUB_CLIENT_ID_PROD` di `.env`

3. **Update kode** untuk menggunakan Client ID yang sesuai berdasarkan environment

## Catatan Penting

1. **GitHub OAuth App hanya mendukung satu callback URL** - Tidak bisa pakai koma atau multiple URLs
2. **GitHub Apps (bukan OAuth Apps) mendukung hingga 10 callback URLs** - Tapi ini berbeda dari OAuth App
3. **Solusi terbaik**: Gunakan satu URL konsisten untuk development, ganti ke production saat deploy
4. **Atau**: Buat OAuth App terpisah untuk development dan production
5. **URL harus sama persis** - termasuk protocol (http/https), domain, port, dan path
6. **Tidak boleh ada trailing slash** - `/auth/github/callback` (bukan `/auth/github/callback/`)

## Troubleshooting

### Error: "Invalid state parameter"
- Pastikan session configuration benar (`session.permanent = True`)
- Pastikan tidak ada masalah dengan cookie/session di browser
- Coba clear browser cache atau gunakan Incognito mode
- Cek console log aplikasi untuk melihat state token

### Error: "redirect_uri_mismatch"
- Pastikan URL di GitHub sama persis dengan yang digunakan aplikasi
- Pastikan semua variasi URL sudah ditambahkan (localhost, 127.0.0.1, production domain)
- Pastikan protocol benar (http untuk local, https untuk production)

### Session tidak persist
- Pastikan `session.permanent = True` sudah di-set sebelum menyimpan state
- Pastikan browser mengizinkan cookies
- Cek `app.py` untuk session configuration

## Perbedaan dengan Google OAuth

**Google OAuth** mendukung multiple redirect URIs:
- Tambahkan multiple URLs di Google Cloud Console → OAuth 2.0 Client → Authorized redirect URIs
- Bisa menambahkan banyak URL sekaligus

**GitHub OAuth App** hanya mendukung satu callback URL:
- Hanya bisa satu URL per OAuth App
- Tidak bisa pakai koma atau multiple URLs
- Solusi: Buat OAuth App terpisah untuk setiap environment, atau ganti URL saat deploy

