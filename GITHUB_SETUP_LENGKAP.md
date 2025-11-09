# Setup GitHub OAuth - Panduan Lengkap

## Yang Perlu Diisi di GitHub OAuth App Settings

### 1. Homepage URL (Bukan untuk OAuth Callback)
- **Field**: "Homepage URL"
- **Isi**: `http://localhost:5000/` atau `http://127.0.0.1:5000/`
- **Catatan**: Field ini hanya untuk homepage aplikasi, **BUKAN untuk OAuth callback**
- **Bisa pakai koma?**: Bisa, tapi tidak perlu karena ini hanya untuk display

### 2. Authorization Callback URL (Yang Penting!)
- **Field**: "Authorization callback URL" ⭐ **INI YANG PENTING**
- **Isi**: `http://localhost:5000/auth/github/callback`
- **Catatan**: 
  - **Hanya bisa satu URL** (tidak bisa pakai koma)
  - **Cukup isi dengan `localhost` saja**
  - Aplikasi sudah dikonfigurasi untuk otomatis convert `127.0.0.1` ke `localhost`

## Setup Lengkap

### Langkah 1: Buka GitHub OAuth App Settings
1. Buka: https://github.com/settings/developers
2. Klik aplikasi "inemi"

### Langkah 2: Isi Form

**Application name:**
```
inemi
```

**Homepage URL:**
```
http://localhost:5000/
```
(atau `http://127.0.0.1:5000/` - tidak masalah, ini hanya untuk display)

**Authorization callback URL:** ⭐ **PENTING**
```
http://localhost:5000/auth/github/callback
```
**Hanya isi satu URL ini saja!** Jangan pakai koma.

### Langkah 3: Update Application
1. Klik tombol hijau **"Update application"** di bagian bawah
2. Tunggu 10-15 detik

## Mengapa Cukup Satu URL?

Aplikasi sudah dikonfigurasi untuk:
- Jika diakses via `http://localhost:5000/login` → menggunakan `localhost` untuk callback ✅
- Jika diakses via `http://127.0.0.1:5000/login` → **otomatis convert** ke `localhost` untuk callback ✅

Jadi meskipun Anda akses via `127.0.0.1`, aplikasi akan tetap menggunakan `localhost` untuk callback ke GitHub.

## Test

1. **Test via localhost:**
   - Buka: `http://localhost:5000/login`
   - Klik "Continue with GitHub"
   - Seharusnya berhasil ✅

2. **Test via 127.0.0.1:**
   - Buka: `http://127.0.0.1:5000/login`
   - Klik "Continue with GitHub"
   - Seharusnya berhasil ✅ (aplikasi otomatis convert ke localhost)

## Untuk Production

Saat deploy ke production, ganti **Authorization callback URL** menjadi:
```
https://inemi.id/auth/github/callback
```

Atau buat OAuth App terpisah untuk production (lebih disarankan).

## Ringkasan

| Field | Isi | Bisa Koma? | Keterangan |
|-------|-----|------------|------------|
| **Homepage URL** | `http://localhost:5000/` | Bisa, tapi tidak perlu | Hanya untuk display |
| **Authorization callback URL** | `http://localhost:5000/auth/github/callback` | **TIDAK BISA** | Hanya satu URL, ini yang penting! |

**Yang penting diisi:** Authorization callback URL dengan `http://localhost:5000/auth/github/callback` (satu URL saja, tanpa koma).

