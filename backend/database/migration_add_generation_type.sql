-- Migration: Add generation_type field to images and videos tables
-- This migration adds a field to track which feature was used to generate the content

-- Add generation_type column to images table
ALTER TABLE images 
ADD COLUMN generation_type VARCHAR(50) NULL 
COMMENT 'Type of generation: ai_generate, face_swap, generate_image, generate_miniatur, fusigaya, etc.';

-- Add generation_type column to videos table
ALTER TABLE videos 
ADD COLUMN generation_type VARCHAR(50) NULL 
COMMENT 'Type of generation: generate_video, image_to_video, generate_video_avatar, face_swap_video, generate_miniatur_video, etc.';

-- Optional: Add index for faster queries if needed
-- CREATE INDEX idx_images_generation_type ON images(generation_type);
-- CREATE INDEX idx_videos_generation_type ON videos(generation_type);

