-- Seed promotions data
INSERT INTO promotions (promo_id, product_id, product_name, original_price, promo_price, discount_percentage, start_date, end_date, is_active, predicted_sales)
VALUES 
    ('PROMO001', 'P001', 'Premium Coffee Beans', 25.99, 18.19, 30, NOW(), NOW() + INTERVAL '7 days', true, 40),
    ('PROMO002', 'P002', 'Organic Protein Powder', 49.99, 24.99, 50, NOW(), NOW() + INTERVAL '7 days', true, 50),
    ('PROMO003', 'P003', 'Smart Watch Series X', 299.99, 179.99, 40, NOW(), NOW() + INTERVAL '7 days', true, 35),
    ('PROMO004', 'P004', 'Designer Sunglasses', 149.99, 104.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 38),
    ('PROMO005', 'P005', 'Wireless Earbuds Pro', 179.99, 134.99, 25, NOW(), NOW() + INTERVAL '7 days', true, 26),
    ('PROMO006', 'P006', 'Gourmet Snack Box', 59.99, 44.99, 25, NOW(), NOW() + INTERVAL '7 days', true, 22),
    ('PROMO007', 'P007', 'Eco Home Starter Kit', 89.99, 62.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 28),
    ('PROMO008', 'P008', 'Running Shoes Elite', 129.99, 90.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 30)
ON CONFLICT (promo_id) DO NOTHING;
