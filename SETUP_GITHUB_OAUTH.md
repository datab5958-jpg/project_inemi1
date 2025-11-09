# Setup GitHub OAuth - Panduan Lengkap

## Langkah 1: Buat File .env

Buat file `.env` di folder `backend/` dengan isi berikut:

```env
# GitHub OAuth Configuration
GITHUB_CLIENT_ID=Ov231iIXT6EyOvLleJ0l
GITHUB_CLIENT_SECRET=your-client-secret-here

# Google OAuth Configuration (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

**PENTING**: 
- Ganti `your-client-secret-here` dengan Client Secret yang Anda dapatkan dari GitHub
- Client Secret hanya ditampilkan sekali saat pertama kali dibuat!

## Langkah 2: Dapatkan Client Secret dari GitHub

1. Buka https://github.com/settings/developers
2. Klik pada aplikasi "inemi" yang sudah Anda buat
3. Scroll ke bagian "Client secrets"
4. Klik tombol **"Generate a new client secret"**
5. **Copy Client Secret** yang muncul (hanya ditampilkan sekali!)
6. Paste ke file `.env` di bagian `GITHUB_CLIENT_SECRET=`

## Langkah 3: Pastikan Authorization Callback URL Benar

Di GitHub OAuth App settings, pastikan:
- **Authorization callback URL**: `http://localhost:5000/auth/github/callback`

Untuk production, tambahkan juga:
- `https://yourdomain.com/auth/github/callback`

## Langkah 4: Restart Aplikasi

Setelah menambahkan credentials ke file `.env`, **restart aplikasi Flask**:

```bash
# Stop aplikasi yang sedang berjalan (Ctrl+C)
# Kemudian jalankan lagi:
cd backend
py app.py
```

## Langkah 5: Test Login

1. Buka `http://127.0.0.1:5000/login`
2. Klik tombol **"Continue with GitHub"**
3. Anda akan diarahkan ke GitHub untuk authorize
4. Setelah authorize, Anda akan kembali ke aplikasi dan login berhasil!

## Troubleshooting

### Error: "GitHub login belum dikonfigurasi"
- Pastikan file `.env` ada di folder `backend/`
- Pastikan `GITHUB_CLIENT_ID` dan `GITHUB_CLIENT_SECRET` sudah diisi
- Restart aplikasi setelah mengubah file `.env`

### Error: "redirect_uri_mismatch"
- Pastikan Authorization callback URL di GitHub sama persis dengan: `http://localhost:5000/auth/github/callback`
- Tidak boleh ada trailing slash (`/`) di akhir

### Error: "Gagal mendapatkan token dari GitHub"
- Pastikan Client Secret benar
- Pastikan Client Secret belum expired (jika sudah expired, generate yang baru)

### File .env tidak terbaca
- Pastikan file `.env` ada di folder `backend/` (sama dengan `app.py`)
- Pastikan tidak ada spasi sebelum atau sesudah `=`
- Format: `GITHUB_CLIENT_ID=Ov231iIXT6EyOvLleJ0l` (tanpa spasi)

## Contoh File .env Lengkap

```env
# GitHub OAuth Configuration
GITHUB_CLIENT_ID=Ov231iIXT6EyOvLleJ0l
GITHUB_CLIENT_SECRET=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=inemi

# Secret Key
SECRET_KEY=your-secret-key-here
```

## Catatan Penting

1. **Jangan commit file `.env` ke Git!** File ini berisi credentials rahasia
2. File `.env` harus ada di folder `backend/` (sama level dengan `app.py`)
3. Setelah mengubah `.env`, selalu restart aplikasi
4. Client Secret GitHub hanya ditampilkan sekali, simpan dengan baik!

