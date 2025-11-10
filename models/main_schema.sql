CREATE DATABASE IF NOT EXISTS sya_main;
USE sya_main;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    db_name VARCHAR(100) NOT NULL UNIQUE,
    db_user VARCHAR(100) NOT NULL UNIQUE,
    db_password VARCHAR(255) NOT NULL,
    db_host VARCHAR(100) DEFAULT 'localhost',
    sms_api_url VARCHAR(255),
    sms_api_token VARCHAR(255),
    sms_sender_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE users ADD COLUMN last_sms_message TEXT NULL;
ALTER TABLE users ADD COLUMN suspended TINYINT(1) DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS company_type VARCHAR(100);



-- 1️⃣ Create the database
CREATE DATABASE IF NOT EXISTS sya_main
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- 2️⃣ Use the database
USE sya_main;

-- 3️⃣ Create the table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) DEFAULT NULL,
    db_name VARCHAR(100) NOT NULL,
    db_user VARCHAR(100) NOT NULL,
    db_password VARCHAR(255) NOT NULL,
    db_host VARCHAR(100) NOT NULL DEFAULT 'localhost',
    sms_api_url VARCHAR(255) DEFAULT NULL,
    sms_api_token VARCHAR(255) DEFAULT NULL,
    sms_sender_id VARCHAR(50) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sms_quota INT DEFAULT 0,
    sms_used INT DEFAULT 0,
    is_admin TINYINT(1) DEFAULT 0,
    sms_sending TINYINT(1) DEFAULT 0,
    last_sms_message TEXT DEFAULT NULL,
    suspended TINYINT(1) DEFAULT 0,
    company_type VARCHAR(100) DEFAULT NULL
);



INSERT INTO users (
    username,
    password_hash,
    email,
    db_name,
    db_user,
    db_password,
    db_host,
    sms_api_url,
    sms_api_token,
    sms_sender_id,
    sms_quota,
    sms_used,
    is_admin,
    sms_sending,
    suspended,
    company_type
)
VALUES (
    'admin',
    'hashed_admin_password',
    'admin@example.com',
    'admin_db',
    'admin_user',
    'admin_password',
    'localhost',
    NULL,
    NULL,
    NULL,
    999999,
    0,
    1,
    0,
    0,
    'Admin'
);
