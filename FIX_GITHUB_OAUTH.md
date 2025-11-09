# Fix GitHub OAuth Error - redirect_uri not associated

## Masalah
Error: "The `redirect_uri` is not associated with this application."

## Solusi Lengkap

### Langkah 1: Pastikan Authorization Callback URL di GitHub BENAR

1. Buka: https://github.com/settings/developers
2. Klik aplikasi "inemi"
3. Scroll ke bagian **"Authorization callback URL"**
4. **HAPUS SEMUA URL YANG ADA** (jika ada lebih dari satu)
5. **TAMBAHKAN URL INI:**
   ```
   http://localhost:5000/auth/github/callback
   ```
6. **ATAU TAMBAHKAN JUGA:**
   ```
   http://127.0.0.1:5000/auth/github/callback
   ```
7. **Klik tombol "Update application"** (hijau di bagian bawah)

### Langkah 2: Pastikan Format URL Benar

**✅ BENAR:**
- `http://localhost:5000/auth/github/callback`
- `http://127.0.0.1:5000/auth/github/callback`

**❌ SALAH:**
- `http://localhost:3000/api/auth/callback/github` (port salah, path salah)
- `http://127.0.0.1:5000/auth/github/callback/` (ada trailing slash)
- `https://localhost:5000/auth/github/callback` (menggunakan https untuk localhost)

### Langkah 3: Tunggu Beberapa Detik

Setelah klik "Update application", tunggu 10-15 detik agar perubahan diterapkan oleh GitHub.

### Langkah 4: Clear Browser Cache (Opsional)

Jika masih error, coba:
1. Clear cache browser
2. Atau gunakan Incognito/Private mode
3. Atau coba browser lain

### Langkah 5: Test Lagi

1. Buka `http://127.0.0.1:5000/login`
2. Klik "Continue with GitHub"
3. Seharusnya tidak ada error lagi

## Checklist

Pastikan semua ini sudah benar:

- [ ] Authorization callback URL di GitHub: `http://localhost:5000/auth/github/callback`
- [ ] Sudah klik "Update application"
- [ ] Sudah menunggu 10-15 detik setelah update
- [ ] File `.env` berisi `GITHUB_CLIENT_ID` dan `GITHUB_CLIENT_SECRET`
- [ ] Aplikasi Flask sudah di-restart setelah mengubah `.env`

## Jika Masih Error

1. **Cek di console aplikasi Flask** - lihat log `[GitHub OAuth] Redirect URI: ...`
2. **Pastikan URL di log sama persis** dengan yang ada di GitHub
3. **Coba tambahkan kedua URL** (localhost dan 127.0.0.1) di GitHub
4. **Pastikan tidak ada spasi** sebelum/sesudah URL di GitHub

## Screenshot yang Diperlukan

Jika masih error, kirim screenshot:
1. Halaman GitHub OAuth App settings (bagian Authorization callback URL)
2. Console log dari aplikasi Flask (lihat `[GitHub OAuth] Redirect URI`)

