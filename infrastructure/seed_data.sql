-- Seed promotions data
INSERT INTO promotions (promo_id, product_id, product_name, original_price, promo_price, discount_percentage, start_date, end_date, is_active, predicted_sales)
VALUES 
    ('PROMO001', 'P001', 'Premium Coffee Beans', 25.99, 18.19, 30, NOW(), NOW() + INTERVAL '7 days', true, 130),
    ('PROMO002', 'P002', 'Organic Protein Powder', 49.99, 24.99, 50, NOW(), NOW() + INTERVAL '7 days', true, 160),
    ('PROMO003', 'P003', 'Smart Watch Series X', 299.99, 179.99, 40, NOW(), NOW() + INTERVAL '7 days', true, 70),
    ('PROMO004', 'P004', 'Designer Sunglasses', 149.99, 104.99, 30, NOW(), NOW() + INTERVAL '7 days', true, 78)
ON CONFLICT (promo_id) DO NOTHING;
