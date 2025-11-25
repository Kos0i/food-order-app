CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    items JSONB NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO orders (customer_name, items, total, status) VALUES 
('John Doe', '["Pizza", "Coke"]', 25.99, 'completed'),
('Jane Smith', '["Burger", "Fries"]', 15.50, 'pending'),
('Bob Johnson', '["Sushi", "Green Tea"]', 32.75, 'preparing');