# Setup GitHub OAuth Login

## Langkah-langkah Setup GitHub OAuth

### 1. Buat GitHub OAuth App

1. Buka GitHub dan login ke akun Anda
2. Pergi ke **Settings** → **Developer settings** → **OAuth Apps**
3. Klik **New OAuth App**
4. Isi informasi berikut:
   - **Application name**: `INEMI` (atau nama aplikasi Anda)
   - **Homepage URL**: `http://localhost:5000` (untuk development) atau domain production Anda
   - **Authorization callback URL**: 
     - Development: `http://localhost:5000/auth/github/callback`
     - Production: `https://yourdomain.com/auth/github/callback`
5. Klik **Register application**

### 2. Dapatkan Client ID dan Client Secret

1. Setelah OAuth App dibuat, Anda akan melihat **Client ID** dan **Client Secret**
2. **Client ID** bisa langsung dilihat
3. Untuk **Client Secret**, klik **Generate a new client secret** (jika belum ada)
4. **PENTING**: Simpan Client Secret dengan baik, karena hanya ditampilkan sekali!

### 3. Tambahkan ke Environment Variables

Tambahkan ke file `.env` di folder `backend/`:

```env
GITHUB_CLIENT_ID=your-github-client-id-here
GITHUB_CLIENT_SECRET=your-github-client-secret-here
```

Atau set sebagai environment variables di sistem:

**Windows (PowerShell):**
```powershell
$env:GITHUB_CLIENT_ID="your-github-client-id-here"
$env:GITHUB_CLIENT_SECRET="your-github-client-secret-here"
```

**Linux/Mac:**
```bash
export GITHUB_CLIENT_ID="your-github-client-id-here"
export GITHUB_CLIENT_SECRET="your-github-client-secret-here"
```

### 4. Restart Aplikasi

Setelah menambahkan environment variables, restart aplikasi Flask Anda:

```bash
py app.py
```

### 5. Test Login

1. Buka `http://localhost:5000/login`
2. Klik tombol **Continue with GitHub**
3. Anda akan diarahkan ke GitHub untuk authorize aplikasi
4. Setelah authorize, Anda akan kembali ke aplikasi dan login berhasil

## Troubleshooting

### Error: "GitHub login belum dikonfigurasi"
- Pastikan `GITHUB_CLIENT_ID` dan `GITHUB_CLIENT_SECRET` sudah di-set di environment variables
- Restart aplikasi setelah menambahkan environment variables

### Error: "redirect_uri_mismatch"
- Pastikan Authorization callback URL di GitHub OAuth App sama persis dengan yang digunakan aplikasi
- Untuk development: `http://localhost:5000/auth/github/callback`
- Untuk production: `https://yourdomain.com/auth/github/callback`
- Pastikan tidak ada trailing slash (`/`) di akhir URL

### Error: "Gagal mendapatkan token dari GitHub"
- Pastikan Client ID dan Client Secret benar
- Pastikan redirect URI sudah benar di GitHub OAuth App
- Cek console/log untuk detail error

### Email tidak ditemukan
- Pastikan scope `user:email` sudah ditambahkan (sudah otomatis di kode)
- Beberapa user GitHub mungkin menyembunyikan email mereka
- Aplikasi akan mencoba mengambil email dari endpoint `/user/emails` jika email tidak tersedia di `/user`

## Catatan Penting

1. **Client Secret**: Jangan pernah commit Client Secret ke repository public!
2. **Redirect URI**: Harus sama persis antara GitHub OAuth App dan aplikasi Anda
3. **HTTPS**: Untuk production, pastikan menggunakan HTTPS
4. **State Token**: Aplikasi sudah menggunakan secure state token untuk mencegah CSRF attacks

## Perbedaan dengan Google OAuth

- GitHub menggunakan `Bearer` token untuk Authorization header (sudah diimplementasikan)
- GitHub memerlukan scope `user:email` untuk mendapatkan email user
- GitHub menggunakan endpoint `/user/emails` sebagai fallback jika email tidak tersedia di `/user`

