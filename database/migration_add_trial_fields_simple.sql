-- Migration sederhana untuk menambahkan field trial ke tabel users
-- Jalankan SQL ini di MySQL database

-- Tambahkan kolom video_trial_used
ALTER TABLE users 
ADD COLUMN video_trial_used BOOLEAN DEFAULT FALSE NOT NULL;

-- Tambahkan kolom image_to_video_trial_used
ALTER TABLE users 
ADD COLUMN image_to_video_trial_used BOOLEAN DEFAULT FALSE NOT NULL;

-- Tambahkan kolom face_swap_trial_used
ALTER TABLE users 
ADD COLUMN face_swap_trial_used BOOLEAN DEFAULT FALSE NOT NULL;

