CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 2. Menu items table (populated/updated via admin dashboard)
CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,              -- This acts as the serial number (e.g. 9, 55)
    item_name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL,      -- 'tiffins', 'fast food', 'meals'
    price NUMERIC(10, 2) NOT NULL,
    photo_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,     -- TRUE: Green dot, FALSE: Red dot
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Cart table with custom code encoding and total price
CREATE TABLE IF NOT EXISTS carts (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) UNIQUE NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    cart_code TEXT NOT NULL DEFAULT '', -- Stores formatted code: e.g. '9+2a55+1a'
    total_price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed sample items so your menu has data immediately
INSERT INTO menu_items (id, item_name, category, price, photo_url, is_active) VALUES
(9, 'Masala Dosa', 'tiffins', 80.00, 'https://images.unsplash.com/photo-1668236543090-82eba5ee5976?w=600&auto=format&fit=crop&q=80', TRUE),
(12, 'Idli Vada Sambar', 'tiffins', 60.00, 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&auto=format&fit=crop&q=80', TRUE),
(25, 'Veg Manchurian', 'fast food', 140.00, 'https://images.unsplash.com/photo-1525755662778-989d0524087e?w=600&auto=format&fit=crop&q=80', TRUE),
(31, 'Chicken Burger', 'fast food', 180.00, 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&auto=format&fit=crop&q=80', FALSE),
(55, 'Special Thali Meal', 'meals', 220.00, 'https://images.unsplash.com/photo-1610057099443-fde8c4d50f91?w=600&auto=format&fit=crop&q=80', TRUE),
(60, 'Chicken Biryani', 'meals', 260.00, 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&auto=format&fit=crop&q=80', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Reset sequence to prevent ID collisions on new inserts
SELECT setval('menu_items_id_seq', (SELECT COALESCE(MAX(id), 1) FROM menu_items));

-- Orders table to track customer orders and status
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    items_code TEXT NOT NULL,           -- e.g. '9+2a55+1a'
    total_amount NUMERIC(10, 2) NOT NULL,
    payment_method VARCHAR(50) DEFAULT 'UPI',
    status VARCHAR(50) DEFAULT 'placed', -- 'placed', 'preparing', 'delivered', 'cancelled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_email, status);