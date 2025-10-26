-- Manual SQL to create moderation_actions table (MySQL/MariaDB)
-- Run this in your INEMI database:
--   mysql -u <user> -p <db_name> < database/create_moderation_actions.sql

CREATE TABLE IF NOT EXISTS `moderation_actions` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `content_type` ENUM('video','image','song','video_iklan') NOT NULL,
  `content_id` VARCHAR(50) NOT NULL,
  `action` ENUM('deactivate','report') NOT NULL,
  `reason` TEXT NULL,
  `active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `_content_action_uc` (`content_type`,`content_id`,`action`),
  KEY `idx_content_lookup` (`content_type`,`content_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



