# Setup Google OAuth Login

## Masalah: Error `redirect_uri_mismatch`

Error ini terjadi karena redirect URI yang digunakan aplikasi belum ditambahkan di Google Cloud Console.

## Solusi: Tambahkan Redirect URI di Google Cloud Console

### Langkah 1: Buka Google Cloud Console
1. Buka: https://console.cloud.google.com/
2. Login dengan akun Google Anda
3. Pilih project yang sesuai (atau buat project baru)

### Langkah 2: Setup OAuth Consent Screen
1. Buka **APIs & Services** → **OAuth consent screen**
2. Pilih **External** (untuk testing) atau **Internal** (untuk Google Workspace)
3. Isi informasi:
   - App name: `INEMI`
   - User support email: Email Anda
   - Developer contact: Email Anda
4. Klik **SAVE AND CONTINUE**
5. Di **Scopes**, klik **SAVE AND CONTINUE**
6. Di **Test users** (jika External), tambahkan email yang akan digunakan untuk testing
7. Klik **SAVE AND CONTINUE**

### Langkah 3: Buat OAuth 2.0 Client ID
1. Buka **APIs & Services** → **Credentials**
2. Klik **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Application type: Pilih **Web application**
4. Name: `INEMI Web Client`
5. **Authorized redirect URIs**: Tambahkan semua URI berikut (satu per satu):
   ```
   http://127.0.0.1:5000/auth/google/callback
   http://localhost:5000/auth/google/callback
   http://172.20.10.11:5000/auth/google/callback
   https://www.inemi.id/auth/google/callback
   ```
   **⚠️ PENTING:** 
   - Redirect URI harus LENGKAP dengan path `/auth/google/callback`
   - JANGAN hanya menambahkan domain saja seperti `http://127.0.0.1:5000`
   - Harus lengkap: `http://127.0.0.1:5000/auth/google/callback`
   - Tambahkan juga domain/IP lain yang Anda gunakan
6. Klik **CREATE**
7. **Copy Client ID dan Client Secret**

### Langkah 4: Tambahkan ke Environment Variables
Tambahkan ke file `.env` di folder `backend/`:

```env
GOOGLE_CLIENT_ID=your-client-id-here
GOOGLE_CLIENT_SECRET=your-client-secret-here
```

Atau set sebagai environment variables di sistem:

**Windows (PowerShell):**
```powershell
$env:GOOGLE_CLIENT_ID="your-client-id-here"
$env:GOOGLE_CLIENT_SECRET="your-client-secret-here"
```

**Linux/Mac:**
```bash
export GOOGLE_CLIENT_ID="your-client-id-here"
export GOOGLE_CLIENT_SECRET="your-client-secret-here"
```

### Langkah 5: Restart Server
Setelah menambahkan environment variables, restart server Flask:
```bash
# Stop server (CTRL+C)
# Start server lagi
python app.py
```

### Langkah 6: Test Login
1. Buka: http://127.0.0.1:5000/login
2. Klik "Continue with Google"
3. Pilih akun Google
4. Setujui permissions
5. Seharusnya redirect kembali ke aplikasi dan login berhasil

## Troubleshooting

### Masih Error `redirect_uri_mismatch`?
1. **Cek redirect URI yang digunakan:**
   - Buka: http://127.0.0.1:5000/auth/google/debug
   - Copy redirect URI yang ditampilkan
   - Pastikan URI tersebut sudah ditambahkan di Google Cloud Console

2. **Pastikan exact match:**
   - Tidak ada trailing slash (`/`)
   - Protocol (`http://` atau `https://`) sesuai
   - Port (`5000`) sesuai
   - Case-sensitive

3. **Tunggu beberapa detik:**
   - Setelah menambahkan URI di Google Cloud Console, tunggu 1-2 menit agar perubahan tersebar

4. **Cek di Google Cloud Console:**
   - Pastikan URI sudah tersimpan (refresh halaman)
   - Pastikan tidak ada typo
   - Pastikan semua URI yang mungkin digunakan sudah ditambahkan

### Error Lainnya?
- **Error 400: invalid_client**: Client ID atau Client Secret salah
- **Error 403: access_denied**: User menolak permissions atau app belum di-approve
- **Error 401: invalid_token**: Token expired atau invalid

## Catatan Penting

1. **Development vs Production:**
   - Untuk development, gunakan `http://localhost:5000` atau `http://127.0.0.1:5000`
   - Untuk production, gunakan domain production Anda (misal: `https://inemi.id`)

2. **Security:**
   - Jangan commit Client Secret ke Git
   - Gunakan environment variables
   - Jangan share Client Secret dengan orang lain

3. **Testing:**
   - Untuk testing, app harus dalam mode "Testing"
   - Hanya test users yang bisa login
   - Untuk production, perlu submit untuk review Google

## Bantuan

Jika masih ada masalah:
1. Cek log di console Flask untuk melihat redirect URI yang digunakan
2. Buka halaman debug: http://127.0.0.1:5000/auth/google/debug
3. Pastikan semua langkah di atas sudah dilakukan dengan benar

