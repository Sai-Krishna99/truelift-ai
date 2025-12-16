CREATE TABLE IF NOT EXISTS promotions (
    id SERIAL PRIMARY KEY,
    promo_id VARCHAR(100) UNIQUE NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    original_price DECIMAL(10, 2) NOT NULL,
    promo_price DECIMAL(10, 2) NOT NULL,
    discount_percentage DECIMAL(5, 2) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT true,
    predicted_sales INTEGER NOT NULL,
    category VARCHAR(100) DEFAULT 'General',
    price_sensitivity VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    promo_id VARCHAR(100) REFERENCES promotions(promo_id),
    product_id VARCHAR(100) NOT NULL,
    shopper_id VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cannibalization_alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(100) UNIQUE NOT NULL,
    promo_id VARCHAR(100) REFERENCES promotions(promo_id),
    product_id VARCHAR(100) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    actual_sales INTEGER NOT NULL,
    predicted_sales INTEGER NOT NULL,
    sales_difference INTEGER NOT NULL,
    loss_percentage DECIMAL(10, 2) NOT NULL,
    loss_amount DECIMAL(15, 2) NOT NULL,
    alert_timestamp TIMESTAMP NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    severity VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_strategies (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(100) UNIQUE NOT NULL,
    alert_id VARCHAR(100) REFERENCES cannibalization_alerts(alert_id),
    explanation TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    alternative_actions JSONB,
    confidence_score DECIMAL(5, 2),
    generated_by VARCHAR(50) DEFAULT 'gemini-pro',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_actions (
    id SERIAL PRIMARY KEY,
    action_id VARCHAR(100) UNIQUE NOT NULL,
    alert_id VARCHAR(100) REFERENCES cannibalization_alerts(alert_id),
    promo_id VARCHAR(100) REFERENCES promotions(promo_id),
    action_type VARCHAR(50) NOT NULL,
    action_details JSONB,
    performed_by VARCHAR(100),
    action_timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback_loop (
    id SERIAL PRIMARY KEY,
    feedback_id VARCHAR(100) UNIQUE NOT NULL,
    action_id VARCHAR(100) REFERENCES user_actions(action_id),
    promo_id VARCHAR(100) REFERENCES promotions(promo_id),
    old_price DECIMAL(10, 2),
    new_price DECIMAL(10, 2),
    sales_before INTEGER,
    sales_after INTEGER,
    effectiveness_score DECIMAL(5, 2),
    feedback_timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_promotions_active ON promotions(is_active);
CREATE INDEX idx_promotions_dates ON promotions(start_date, end_date);
CREATE INDEX idx_sales_events_timestamp ON sales_events(event_timestamp);
CREATE INDEX idx_sales_events_promo ON sales_events(promo_id);
CREATE INDEX idx_alerts_status ON cannibalization_alerts(status);
CREATE INDEX idx_alerts_timestamp ON cannibalization_alerts(alert_timestamp);
CREATE INDEX idx_user_actions_timestamp ON user_actions(action_timestamp);
