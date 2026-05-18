-- Create custom ENUM types
CREATE TYPE session_step AS ENUM ('welcome', 'ordering', 'address', 'confirming', 'completed');
CREATE TYPE order_status AS ENUM ('pending', 'preparing', 'dispatched', 'completed', 'cancelled');

-- Identity Layer
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    default_delivery_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Menu Categories
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- Individual Menu Items
CREATE TABLE menu_items (
    id SERIAL PRIMARY KEY,
    category_id INT REFERENCES categories(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Item Modifiers (Add-ons)
CREATE TABLE item_modifiers (
    id SERIAL PRIMARY KEY,
    menu_item_id INT REFERENCES menu_items(id) ON DELETE CASCADE,
    modifier_name VARCHAR(100) NOT NULL,
    extra_price NUMERIC(10, 2) DEFAULT 0.00,
    is_available BOOLEAN DEFAULT TRUE
);

-- Promotional Offers / Combo Deals
CREATE TABLE deals (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    deal_price NUMERIC(10, 2) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Mapping Items inside a Combo Deal
CREATE TABLE deal_items (
    id SERIAL PRIMARY KEY,
    deal_id INT REFERENCES deals(id) ON DELETE CASCADE,
    menu_item_id INT REFERENCES menu_items(id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 1
);

-- Live Call State Machine Coordinator
CREATE TABLE sessions (
    id VARCHAR(255) PRIMARY KEY,
    customer_id INT REFERENCES customers(id) ON DELETE SET NULL,
    current_step session_step DEFAULT 'welcome',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main Master Orders Table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id) ON DELETE SET NULL,
    session_id VARCHAR(255) REFERENCES sessions(id) ON DELETE SET NULL,
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    status order_status DEFAULT 'pending',
    delivery_address TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Line Items Purchased inside an Order
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id INT REFERENCES menu_items(id) ON DELETE SET NULL,
    deal_id INT REFERENCES deals(id) ON DELETE SET NULL,
    quantity INT NOT NULL DEFAULT 1,
    price_at_purchase NUMERIC(10, 2) NOT NULL
);

-- Modifiers Chosen During Live Call
CREATE TABLE order_item_modifiers (
    id SERIAL PRIMARY KEY,
    order_item_id INT REFERENCES order_items(id) ON DELETE CASCADE,
    item_modifier_id INT REFERENCES item_modifiers(id) ON DELETE SET NULL,
    price_at_purchase NUMERIC(10, 2) NOT NULL
);

-- Create indexes for better query performance
CREATE INDEX idx_customers_phone ON customers(phone_number);
CREATE INDEX idx_menu_items_category ON menu_items(category_id);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_sessions_customer ON sessions(customer_id);

-- Insert sample data
INSERT INTO categories (name, description) VALUES
('Burgers', 'Delicious grilled burgers'),
('Beverages', 'Cold and hot drinks'),
('Desserts', 'Sweet treats and desserts'),
('Sides', 'Fries, salads, and sides');

INSERT INTO menu_items (category_id, name, description, price, is_available) VALUES
(1, 'Zinger Burger', 'Spicy fried chicken burger', 450.00, TRUE),
(1, 'Classic Burger', 'Beef patty with cheese and lettuce', 350.00, TRUE),
(2, 'Coke', 'Coca-Cola cold drink', 80.00, TRUE),
(2, 'Iced Tea', 'Fresh iced tea', 100.00, TRUE),
(4, 'French Fries', 'Crispy golden fries', 120.00, TRUE),
(3, 'Ice Cream', 'Vanilla ice cream', 150.00, TRUE);

INSERT INTO item_modifiers (menu_item_id, modifier_name, extra_price, is_available) VALUES
(1, 'Extra Cheese', 50.00, TRUE),
(1, 'Bacon', 80.00, TRUE),
(2, 'Double Patty', 150.00, TRUE),
(2, 'Extra Sauce', 20.00, TRUE);

INSERT INTO deals (name, description, deal_price, start_date, end_date, is_active) VALUES
('Combo Deal', 'Burger + Fries + Coke', 599.00, NOW(), NOW() + INTERVAL '30 days', TRUE),
('Family Pack', '2 Burgers + 2 Fries + 2 Cokes', 1099.00, NOW(), NOW() + INTERVAL '30 days', TRUE);