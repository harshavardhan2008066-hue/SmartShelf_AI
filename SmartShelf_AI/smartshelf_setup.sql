-- 1. Drop existing tables if they exist to prevent schema collision conflicts
DROP TABLE IF EXISTS saved_recipes CASCADE;
DROP TABLE IF EXISTS expirations CASCADE;
DROP TABLE IF EXISTS inventory CASCADE;
DROP TABLE IF EXISTS meal_logs CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 2. Create foundational standalone table first
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    dietary_preference VARCHAR(100) DEFAULT 'None',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create dependent tables that link back to users
CREATE TABLE inventory (
    item_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL DEFAULT 1.00,
    category VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE expirations (
    alert_id SERIAL PRIMARY KEY,
    item_id INT NOT NULL,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estimated_expiry DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'Fresh',
    CONSTRAINT fk_item FOREIGN KEY (item_id) REFERENCES inventory(item_id) ON DELETE CASCADE
);

CREATE TABLE saved_recipes (
    recipe_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    instructions TEXT NOT NULL,
    calories INT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_recipe_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE meal_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    calories DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    food_item TEXT NOT NULL DEFAULT '',
    CONSTRAINT fk_meal_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);