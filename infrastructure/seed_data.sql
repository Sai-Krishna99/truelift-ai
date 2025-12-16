-- Enhanced seed promotions data with realistic product variety
-- 35 products across multiple categories with varied pricing, discounts, and price sensitivity
-- Categories: Electronics, Food & Beverage, Fashion, Home & Living, Health & Beauty, Sports & Fitness

INSERT INTO promotions (promo_id, product_id, product_name, original_price, promo_price, discount_percentage, start_date, end_date, is_active, predicted_sales, category, price_sensitivity)
VALUES 
    -- FOOD & BEVERAGE (High price sensitivity - elastic demand)
    ('PROMO001', 'P001', 'Premium Coffee Beans 1kg', 24.99, 17.49, 30, NOW(), NOW() + INTERVAL '7 days', true, 120, 'Food & Beverage', 'high'),
    ('PROMO002', 'P002', 'Energy Drink 12-Pack', 18.99, 11.39, 40, NOW(), NOW() + INTERVAL '7 days', true, 200, 'Food & Beverage', 'high'),
    ('PROMO003', 'P003', 'Artisan Dark Chocolate Bar', 8.99, 6.29, 30, NOW(), NOW() + INTERVAL '7 days', true, 150, 'Food & Beverage', 'high'),
    ('PROMO004', 'P004', 'Organic Protein Bars 12ct', 29.99, 20.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 95, 'Food & Beverage', 'medium'),
    ('PROMO005', 'P005', 'Gourmet Tea Sampler', 34.99, 24.49, 30, NOW(), NOW() + INTERVAL '7 days', true, 85, 'Food & Beverage', 'medium'),
    
    -- HOME & LIVING (Medium-high price sensitivity)
    ('PROMO006', 'P006', 'Scented Candle Set 3pk', 32.99, 22.09, 33, NOW(), NOW() + INTERVAL '7 days', true, 110, 'Home & Living', 'medium'),
    ('PROMO007', 'P007', 'Kitchen Knife Set Premium', 79.99, 55.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 65, 'Home & Living', 'medium'),
    ('PROMO008', 'P008', 'Throw Blanket Luxury', 49.99, 34.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 88, 'Home & Living', 'medium'),
    ('PROMO009', 'P009', 'Coffee Maker 12-Cup', 89.99, 62.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 72, 'Home & Living', 'low'),
    ('PROMO010', 'P010', 'Wall Art Canvas Set', 119.99, 89.99, 25, NOW(), NOW() + INTERVAL '7 days', true, 45, 'Home & Living', 'low'),
    
    -- FASHION (Medium price sensitivity - brand matters)
    ('PROMO011', 'P011', 'Designer Sunglasses', 149.99, 119.99, 20, NOW(), NOW() + INTERVAL '7 days', true, 58, 'Fashion', 'low'),
    ('PROMO012', 'P012', 'Leather Wallet Premium', 69.99, 48.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 82, 'Fashion', 'medium'),
    ('PROMO013', 'P013', 'Cashmere Scarf', 89.99, 62.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 67, 'Fashion', 'medium'),
    ('PROMO014', 'P014', 'Designer Watch', 299.99, 239.99, 20, NOW(), NOW() + INTERVAL '7 days', true, 38, 'Fashion', 'low'),
    ('PROMO015', 'P015', 'Leather Handbag', 189.99, 132.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 52, 'Fashion', 'low'),
    
    -- ELECTRONICS (Low-medium price sensitivity - research-driven)
    ('PROMO016', 'P016', 'Wireless Earbuds Pro', 129.99, 103.99, 20, NOW(), NOW() + INTERVAL '7 days', true, 95, 'Electronics', 'medium'),
    ('PROMO017', 'P017', 'Smart Watch Fitness', 199.99, 169.99, 15, NOW(), NOW() + INTERVAL '7 days', true, 68, 'Electronics', 'low'),
    ('PROMO018', 'P018', 'Bluetooth Speaker Portable', 79.99, 63.99, 20, NOW(), NOW() + INTERVAL '7 days', true, 110, 'Electronics', 'medium'),
    ('PROMO019', 'P019', 'Noise-Cancel Headphones', 249.99, 199.99, 20, NOW(), NOW() + INTERVAL '7 days', true, 55, 'Electronics', 'low'),
    ('PROMO020', 'P020', 'Tablet 10-inch', 329.99, 263.99, 20, NOW(), NOW() + INTERVAL '7 days', true, 48, 'Electronics', 'low'),
    ('PROMO021', 'P021', 'Webcam 4K', 149.99, 119.99, 20, NOW(), NOW() + INTERVAL '7 days', true, 72, 'Electronics', 'medium'),
    ('PROMO022', 'P022', 'Mechanical Keyboard RGB', 99.99, 74.99, 25, NOW(), NOW() + INTERVAL '7 days', true, 85, 'Electronics', 'medium'),
    
    -- HEALTH & BEAUTY (Medium-high price sensitivity)
    ('PROMO023', 'P023', 'Skincare Set Anti-Aging', 89.99, 62.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 92, 'Health & Beauty', 'medium'),
    ('PROMO024', 'P024', 'Hair Dryer Professional', 129.99, 90.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 68, 'Health & Beauty', 'medium'),
    ('PROMO025', 'P025', 'Electric Toothbrush', 79.99, 55.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 105, 'Health & Beauty', 'high'),
    ('PROMO026', 'P026', 'Massage Gun Deep Tissue', 149.99, 104.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 75, 'Health & Beauty', 'medium'),
    ('PROMO027', 'P027', 'Essential Oils Gift Set', 49.99, 34.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 115, 'Health & Beauty', 'high'),
    
    -- SPORTS & FITNESS (Medium price sensitivity)
    ('PROMO028', 'P028', 'Yoga Mat Premium Non-Slip', 49.99, 34.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 125, 'Sports & Fitness', 'high'),
    ('PROMO029', 'P029', 'Resistance Bands Set', 34.99, 24.49, 30, NOW(), NOW() + INTERVAL '7 days', true, 140, 'Sports & Fitness', 'high'),
    ('PROMO030', 'P030', 'Dumbbell Set 20lb', 119.99, 89.99, 25, NOW(), NOW() + INTERVAL '7 days', true, 62, 'Sports & Fitness', 'medium'),
    ('PROMO031', 'P031', 'Running Shoes Pro', 139.99, 97.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 88, 'Sports & Fitness', 'medium'),
    ('PROMO032', 'P032', 'Gym Bag Large', 59.99, 41.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 95, 'Sports & Fitness', 'high'),
    
    -- PREMIUM ELECTRONICS (Low price sensitivity - brand loyal)
    ('PROMO033', 'P033', 'Smart Home Hub Bundle', 279.99, 237.59, 15, NOW(), NOW() + INTERVAL '7 days', true, 42, 'Electronics', 'low'),
    ('PROMO034', 'P034', 'Robot Vacuum Premium', 449.99, 404.99, 10, NOW(), NOW() + INTERVAL '7 days', true, 35, 'Electronics', 'low'),
    ('PROMO035', 'P035', '4K Action Camera Waterproof', 349.99, 297.49, 15, NOW(), NOW() + INTERVAL '7 days', true, 48, 'Electronics', 'low')
ON CONFLICT (promo_id) DO NOTHING;
