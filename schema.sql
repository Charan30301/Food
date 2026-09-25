-- ==========================================
-- 1. Users Table
-- ==========================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ==========================================
-- 2. Menu Items Table
-- ==========================================
CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    item_name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL,      -- 'tiffins', 'fast food', 'meals'
    price NUMERIC(10, 2) NOT NULL,
    photo_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,     -- TRUE: Green dot, FALSE: Red dot
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed baseline sample menu items
INSERT INTO menu_items (id, item_name, category, price, photo_url, is_active) VALUES
(9, 'Masala Dosa', 'tiffins', 80.00, 'https://images.unsplash.com/photo-1668236543090-82eba5ee5976?w=600&auto=format&fit=crop&q=80', TRUE),
(12, 'Idli Vada Sambar', 'tiffins', 60.00, 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&auto=format&fit=crop&q=80', TRUE),
(25, 'Veg Manchurian', 'fast food', 140.00, 'https://images.unsplash.com/photo-1525755662778-989d0524087e?w=600&auto=format&fit=crop&q=80', TRUE),
(31, 'Chicken Burger', 'fast food', 180.00, 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&auto=format&fit=crop&q=80', FALSE),
(55, 'Special Thali Meal', 'meals', 220.00, 'https://images.unsplash.com/photo-1610057099443-fde8c4d50f91?w=600&auto=format&fit=crop&q=80', TRUE),
(60, 'Chicken Biryani', 'meals', 260.00, 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&auto=format&fit=crop&q=80', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Synchronize sequence to prevent primary key collisions on new admin additions
SELECT setval('menu_items_id_seq', (SELECT COALESCE(MAX(id), 1) FROM menu_items));

-- ==========================================
-- 3. Active Carts Table
-- ==========================================
CREATE TABLE IF NOT EXISTS carts (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) UNIQUE NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    cart_code TEXT NOT NULL DEFAULT '', -- Encoded string: '9+2a55+1a'
    total_price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 4. Customer Orders Table
-- ==========================================
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    daily_order_number INT DEFAULT 0,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    items_code TEXT NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL,
    gateway_order_id VARCHAR(100) UNIQUE,
    payment_id VARCHAR(100),
    payment_status VARCHAR(50) DEFAULT 'pending',   -- 'pending', 'paid', 'failed'
    order_status VARCHAR(50) DEFAULT 'placed',      -- 'placed', 'accepted', 'preparing', 'prepared', 'delivered', 'cancelled'
    cancellation_reason TEXT DEFAULT NULL,
    customer_alert BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Query acceleration indexes
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_email, order_status, payment_status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- ==========================================
-- 5. Admin Authentication Table
-- ==========================================
CREATE TABLE IF NOT EXISTS admin_auth (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Default admin credentials (User: admin | Pass: adminpassword123)
INSERT INTO admin_auth (username, password_hash)
VALUES ('admin', 'scrypt:32768:8:1$K5jL796Z5H7VwHwA$a48b30ce379b360566370bb03cb8eeae4a1be9989fe943be1772fe2440ea9d885a08fb6f595f039bb38ff8e5d0f1eb7c8a6669fcf78c3c1bcce2ad3203f707f1')
ON CONFLICT (username) DO NOTHING;