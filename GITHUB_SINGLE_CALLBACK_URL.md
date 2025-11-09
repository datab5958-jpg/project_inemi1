# Setup GitHub OAuth dengan Satu Callback URL

## Masalah
GitHub OAuth App **hanya mendukung satu Authorization callback URL** (berbeda dengan Google OAuth yang bisa multiple). Tapi kita perlu bekerja di:
- **Local development**: `http://localhost:5000` dan `http://127.0.0.1:5000`
- **Public domain**: `https://yourdomain.com`

## Solusi: Gunakan Satu Callback URL yang Konsisten

Aplikasi sudah dikonfigurasi untuk:
- **Development**: Selalu menggunakan `http://localhost:5000/auth/github/callback` (bahkan jika diakses via `127.0.0.1`)
- **Production**: Menggunakan domain production (misalnya `https://inemi.id/auth/github/callback`)

### Untuk Development (Local)

**Setup di GitHub:**
1. Buka: https://github.com/settings/developers
2. Klik aplikasi "inemi"
3. Di bagian **"Authorization callback URL"**, isi:
   ```
   http://localhost:5000/auth/github/callback
   ```
4. Klik **"Update application"**

**Cara menggunakan:**
- Akses aplikasi via `http://localhost:5000/login` → GitHub login akan bekerja
- Akses aplikasi via `http://127.0.0.1:5000/login` → Aplikasi akan otomatis menggunakan `localhost` untuk callback

### Untuk Production

**Setup di GitHub:**
1. Buka: https://github.com/settings/developers
2. Klik aplikasi "inemi"
3. Di bagian **"Authorization callback URL"**, ganti dengan:
   ```
   https://inemi.id/auth/github/callback
   ```
   (atau domain production Anda)
4. Klik **"Update application"**

**Cara menggunakan:**
- Akses aplikasi via `https://inemi.id/login` → GitHub login akan bekerja

## Alternatif: Buat OAuth App Terpisah

Jika Anda ingin menggunakan keduanya (local dan production) secara bersamaan:

### Opsi 1: Buat 2 OAuth Apps Terpisah

1. **OAuth App untuk Development:**
   - Name: `inemi-dev`
   - Callback URL: `http://localhost:5000/auth/github/callback`
   - Client ID: Simpan di `.env` sebagai `GITHUB_CLIENT_ID_DEV`

2. **OAuth App untuk Production:**
   - Name: `inemi-prod`
   - Callback URL: `https://inemi.id/auth/github/callback`
   - Client ID: Simpan di `.env` sebagai `GITHUB_CLIENT_ID_PROD`

3. **Update kode untuk menggunakan Client ID yang sesuai:**
   ```python
   # Di routes.py
   if 'inemi.id' in request.host or 'inemi.com' in request.host:
       github_client_id = Config.GITHUB_CLIENT_ID_PROD
       github_client_secret = Config.GITHUB_CLIENT_SECRET_PROD
   else:
       github_client_id = Config.GITHUB_CLIENT_ID_DEV
       github_client_secret = Config.GITHUB_CLIENT_SECRET_DEV
   ```

### Opsi 2: Gunakan Environment Variable untuk Callback URL

Tambahkan di `.env`:
```env
# Untuk development
GITHUB_CALLBACK_URL=http://localhost:5000/auth/github/callback

# Untuk production (set saat deploy)
GITHUB_CALLBACK_URL=https://inemi.id/auth/github/callback
```

## Rekomendasi

**Untuk development:** Gunakan satu OAuth App dengan callback URL `http://localhost:5000/auth/github/callback`

**Untuk production:** 
- **Opsi A**: Ganti callback URL di GitHub ke production domain saat deploy
- **Opsi B**: Buat OAuth App terpisah untuk production (lebih aman dan fleksibel)

## Catatan Penting

1. **GitHub hanya mendukung satu callback URL per OAuth App** (berbeda dengan Google)
2. **Aplikasi sudah dikonfigurasi** untuk menormalisasi `127.0.0.1` menjadi `localhost` di development
3. **Untuk production**, pastikan menggunakan HTTPS dan domain yang benar
4. **Setelah mengubah callback URL di GitHub**, tunggu 10-15 detik agar perubahan diterapkan

## Troubleshooting

### Error: "redirect_uri_mismatch" di Production
- Pastikan callback URL di GitHub sudah diganti ke production domain
- Pastikan menggunakan HTTPS (bukan HTTP) untuk production
- Pastikan domain benar (misalnya `https://inemi.id/auth/github/callback`)

### Error: "redirect_uri_mismatch" di Local
- Pastikan callback URL di GitHub adalah `http://localhost:5000/auth/github/callback`
- Jangan gunakan `127.0.0.1` di GitHub (aplikasi akan otomatis convert ke `localhost`)
- Pastikan port `5000` benar

