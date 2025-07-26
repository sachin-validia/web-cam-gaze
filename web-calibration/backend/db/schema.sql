-- Calibration Database Schema
-- Database: calibration_db

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS calibration_db;
USE calibration_db;

-- Calibration sessions table
CREATE TABLE IF NOT EXISTS calibration_sessions (
    id VARCHAR(36) PRIMARY KEY,
    candidate_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status ENUM('in_progress', 'completed', 'failed') DEFAULT 'in_progress',
    interview_id VARCHAR(255),
    error_message TEXT,
    metadata JSON,
    INDEX idx_candidate_id (candidate_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Screen information table
CREATE TABLE IF NOT EXISTS screen_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id VARCHAR(255) NOT NULL UNIQUE,
    screen_data JSON NOT NULL COMMENT 'Stores complete screen configuration',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_candidate_id (candidate_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Calibration data table
CREATE TABLE IF NOT EXISTS calibration_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id VARCHAR(255) NOT NULL,
    calibration_csv LONGTEXT NOT NULL COMMENT 'CSV data for calibration points',
    transform_matrix_data LONGBLOB NOT NULL COMMENT 'NPZ file data as binary',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    file_checksum VARCHAR(64) COMMENT 'SHA256 checksum for data validation',
    INDEX idx_candidate_id (candidate_id),
    UNIQUE KEY unique_candidate (candidate_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Calibration frames table (for real-time processing)
CREATE TABLE IF NOT EXISTS calibration_frames (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    frame_index INT NOT NULL,
    frame_data JSON NOT NULL COMMENT 'Frame metadata and gaze data',
    target_position JSON NOT NULL COMMENT 'Target position for this frame',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_frame_index (session_id, frame_index),
    FOREIGN KEY (session_id) REFERENCES calibration_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Audit log table for compliance
CREATE TABLE IF NOT EXISTS calibration_audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id VARCHAR(255),
    action VARCHAR(50) NOT NULL,
    user_agent VARCHAR(255),
    ip_address VARCHAR(45),
    details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_candidate_id (candidate_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- API access tokens table (for external system integration)
CREATE TABLE IF NOT EXISTS api_access_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    system_name VARCHAR(100) NOT NULL,
    permissions JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    last_used_at TIMESTAMP NULL,
    INDEX idx_token_hash (token_hash),
    INDEX idx_system_name (system_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;