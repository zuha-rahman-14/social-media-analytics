-- ============================================================
-- SocialGuard — MySQL Database Setup
-- Run: mysql -u root -p < database_setup.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS social_media_analytics
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE social_media_analytics;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Posts table
CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    caption TEXT,
    image_path VARCHAR(255),
    likes INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    shares INT DEFAULT 0,
    engagement_score FLOAT DEFAULT 0.0,
    image_tamper_score FLOAT DEFAULT 0.0,
    image_tamper_label VARCHAR(50) DEFAULT 'N/A',
    text_manipulation_score FLOAT DEFAULT 0.0,
    text_manipulation_label VARCHAR(50) DEFAULT 'N/A',
    is_flagged BOOLEAN DEFAULT FALSE,
    flag_reason TEXT,
    platform VARCHAR(50) DEFAULT 'Instagram',
    posted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_is_flagged (is_flagged),
    INDEX idx_created_at (created_at),
    INDEX idx_engagement (engagement_score DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Comments table
CREATE TABLE IF NOT EXISTS comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    sentiment VARCHAR(20) DEFAULT 'neutral',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_post_id (post_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Useful Queries ───────────────────────────────────────────────────
-- Top engaging posts:
--   SELECT * FROM posts ORDER BY engagement_score DESC LIMIT 10;
-- 
-- All flagged content:
--   SELECT * FROM posts WHERE is_flagged = 1;
--
-- Avg engagement per user:
--   SELECT user_id, AVG(engagement_score) FROM posts GROUP BY user_id;
--
-- Posts with high tamper risk:
--   SELECT * FROM posts WHERE image_tamper_score > 0.65 OR text_manipulation_score > 0.65;

SELECT 'Database setup complete.' AS status;
