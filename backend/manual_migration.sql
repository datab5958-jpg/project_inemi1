-- Manual Migration untuk menambahkan kolom genre dan mode ke tabel songs
-- Jalankan SQL ini secara manual di database MySQL

-- Cek apakah kolom genre sudah ada, jika belum tambahkan
SET @col_exists = (SELECT COUNT(*) 
                   FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_NAME = 'songs' 
                   AND COLUMN_NAME = 'genre' 
                   AND TABLE_SCHEMA = DATABASE());

SET @sql = IF(@col_exists = 0, 
              'ALTER TABLE songs ADD COLUMN genre VARCHAR(100) DEFAULT NULL', 
              'SELECT "Kolom genre sudah ada" as message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Cek apakah kolom mode sudah ada, jika belum tambahkan
SET @col_exists = (SELECT COUNT(*) 
                   FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_NAME = 'songs' 
                   AND COLUMN_NAME = 'mode' 
                   AND TABLE_SCHEMA = DATABASE());

SET @sql = IF(@col_exists = 0, 
              'ALTER TABLE songs ADD COLUMN mode VARCHAR(50) DEFAULT NULL', 
              'SELECT "Kolom mode sudah ada" as message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Verifikasi struktur tabel
DESCRIBE songs;

