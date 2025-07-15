-- Active: 1741977031313@@127.0.0.1@3306
CREATE DATABASE IF NOT EXISTS inventory_management;
USE inventory_management;

CREATE TABLE IF NOT EXISTS stocks (
    product_id VARCHAR(50) PRIMARY KEY,
    quantity INT NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL,
    quantity INT NOT NULL,
    date DATE NOT NULL
);

-- Sample data for stocks
INSERT INTO stocks (product_id, quantity) VALUES
('PROD001', 100),
('PROD002', 150),
('PROD003', 75);

-- Sample data for sales
INSERT INTO sales (product_id, quantity, date) VALUES
('PROD001', 5, '2023-08-01'),
('PROD002', 3, '2023-08-01'),
('PROD001', 7, '2023-08-02'),
('PROD003', 2, '2023-08-02'),
('PROD002', 4, '2023-08-03'),
('PROD001', 6, '2023-08-03');

SELECT* FROM sales;

-- User table for role-based access
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    role ENUM('admin', 'manager', 'customer') NOT NULL
);

INSERT INTO users (username, password, role) VALUES
('admin1', '$2b$12$BFUJ8xLQ6q5/sYCh8AHFM.GZJ2TDdEL3j6Kx5fx3GZfG34CmVRV7u', 'admin'),
('manager1', '$2b$12$TTfFTwK23JEVLrgxnw50Eu9i6vOY3jdhLDhAHCFXiUPZzV7z6C8by', 'manager'),
('Steve Rogers', '$2b$12$9V3kLGi/ymxG9x.cLpyaS.jx0NDi9Po55EmohmnfCHoUIF8KhD5yi', 'customer');
INSERT IGNORE INTO users (username, password, role) VALUES
('Tony Stark', '$2b$12$3OVe.v3YTIduPKB.klP45ur9o5UgbUuY9I2Rw5RwRvF8VjAwGMR16', 'customer'),
('Thor', '$2b$12$zrDqOtSztfnn1dKrkBRSquXfV1vR4STpiXVXYAVruJ1RXEJ17MT0y', 'customer'),
('Bruce', '$2b$12$BIoIRU3aCJ9qbXUS0ueJuOYh8sDdu3Gl6Hgxd7jzQU8Q5F1M/F18S', 'customer'),
('Loki', '$2b$12$TfbM1Lgsx6jPjiu9V6G3z.R6B/HdRU8DPHMff3OBVyzYwlZXaZPMu', 'customer'),
('Peter', '$2b$12$DKA.6G9rhMTGHW13JSqTcePtbboKjA91ieJh5MEz8iBzfpakDH0vW', 'customer');

SELECT * FROM users;

ALTER TABLE users
ADD COLUMN last_login DATETIME DEFAULT NULL;
