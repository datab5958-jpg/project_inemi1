# ⚠️ PERBAIKAN: Redirect URI Harus Lengkap!

## Masalah yang Ditemukan

Di Google Cloud Console, redirect URI yang ditambahkan adalah:
- ❌ `http://127.0.0.1:5000` (SALAH - tidak lengkap)
- ❌ `https://www.inemi.id` (SALAH - tidak lengkap)

## Solusi: Tambahkan Path Lengkap

Redirect URI harus LENGKAP dengan path `/auth/google/callback`:

### Yang Benar:
- ✅ `http://127.0.0.1:5000/auth/google/callback`
- ✅ `http://localhost:5000/auth/google/callback`
- ✅ `https://www.inemi.id/auth/google/callback`

### Yang Salah:
- ❌ `http://127.0.0.1:5000` (tanpa path)
- ❌ `https://www.inemi.id` (tanpa path)

## Langkah Perbaikan

1. **Buka Google Cloud Console:**
   - https://console.cloud.google.com/apis/credentials

2. **Klik OAuth 2.0 Client ID Anda**

3. **Di bagian "Authorized redirect URIs":**
   - Hapus URI yang salah: `http://127.0.0.1:5000`
   - Hapus URI yang salah: `https://www.inemi.id`
   - Klik **"+ Add URI"**
   - Tambahkan URI yang BENAR (satu per satu):
     ```
     http://127.0.0.1:5000/auth/google/callback
     http://localhost:5000/auth/google/callback
     https://www.inemi.id/auth/google/callback
     ```

4. **Klik "SAVE"**

5. **Tunggu 1-2 menit**, lalu coba login lagi

## Catatan Penting

- ✅ Redirect URI harus **exact match** dengan yang digunakan aplikasi
- ✅ Harus lengkap dengan path `/auth/google/callback`
- ✅ Tidak boleh ada trailing slash di akhir
- ✅ Protocol (`http://` atau `https://`) harus sesuai
- ✅ Port (`5000`) harus sesuai

## Cek Redirect URI yang Digunakan

Untuk melihat redirect URI yang digunakan aplikasi:
- Buka: http://127.0.0.1:5000/auth/google/debug
- Copy redirect URI yang ditampilkan
- Pastikan URI tersebut sudah ditambahkan di Google Cloud Console

