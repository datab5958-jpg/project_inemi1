# ✅ Setup Google OAuth yang BENAR

## ⚠️ PENTING: Ada 2 Bagian yang Berbeda!

### 1. Authorized JavaScript origins
**Untuk:** Request dari browser (tidak digunakan untuk OAuth redirect)
**Format:** Hanya domain:port, TIDAK boleh ada path
**Contoh yang BENAR:**
```
http://127.0.0.1:5000
http://localhost:5000
https://www.inemi.id
```

**Contoh yang SALAH:**
```
❌ http://127.0.0.1:5000/auth/google/callback (tidak boleh ada path)
❌ https://www.inemi.id/auth/google/callback (tidak boleh ada path)
```

### 2. Authorized redirect URIs ⭐ (INI YANG PENTING!)
**Untuk:** OAuth callback dari Google (yang digunakan aplikasi)
**Format:** Harus LENGKAP dengan path `/auth/google/callback`
**Contoh yang BENAR:**
```
http://127.0.0.1:5000/auth/google/callback
http://localhost:5000/auth/google/callback
https://www.inemi.id/auth/google/callback
```

**Contoh yang SALAH:**
```
❌ http://127.0.0.1:5000 (tidak lengkap, kurang path)
❌ https://www.inemi.id (tidak lengkap, kurang path)
```

## Langkah Perbaikan

### Langkah 1: Perbaiki Authorized JavaScript origins
1. Di Google Cloud Console, scroll ke bagian **"Authorized JavaScript origins"**
2. **Hapus** URI yang salah: `http://127.0.0.1:5000/auth/google/callback`
3. Klik **"+ Add URI"**
4. Tambahkan URI yang BENAR (tanpa path):
   ```
   http://127.0.0.1:5000
   http://localhost:5000
   https://www.inemi.id
   ```

### Langkah 2: Perbaiki Authorized redirect URIs ⭐
1. Scroll ke bagian **"Authorized redirect URIs"**
2. **Hapus** URI yang salah:
   - `https://www.inemi.id` (tidak lengkap)
   - `http://127.0.0.1:5000` (tidak lengkap)
3. Klik **"+ Add URI"**
4. Tambahkan URI yang BENAR (dengan path lengkap):
   ```
   http://127.0.0.1:5000/auth/google/callback
   http://localhost:5000/auth/google/callback
   https://www.inemi.id/auth/google/callback
   ```

### Langkah 3: Save
1. Klik **"SAVE"** di bagian bawah halaman
2. Tunggu 1-2 menit agar perubahan tersebar
3. Coba login dengan Google lagi

## Ringkasan

| Bagian | Format | Contoh Benar | Contoh Salah |
|--------|--------|--------------|--------------|
| **JavaScript origins** | Domain:port saja | `http://127.0.0.1:5000` | `http://127.0.0.1:5000/auth/google/callback` |
| **Redirect URIs** ⭐ | Lengkap dengan path | `http://127.0.0.1:5000/auth/google/callback` | `http://127.0.0.1:5000` |

## Catatan Penting

- ⭐ **Redirect URIs** adalah yang paling penting untuk OAuth login
- **JavaScript origins** biasanya tidak diperlukan untuk OAuth flow standar
- Pastikan redirect URI **exact match** dengan yang digunakan aplikasi
- Tidak boleh ada trailing slash (`/`) di akhir
- Protocol (`http://` atau `https://`) harus sesuai
- Port (`5000`) harus sesuai

## Cek Redirect URI yang Digunakan Aplikasi

Buka: http://127.0.0.1:5000/auth/google/debug

Halaman ini akan menampilkan redirect URI yang digunakan aplikasi. Pastikan URI tersebut sudah ditambahkan di bagian **"Authorized redirect URIs"**.

