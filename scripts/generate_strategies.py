#!/usr/bin/env python3
"""
Generate fallback AI strategies for all alerts that don't have strategies yet.
This is a workaround script for when the Gemini agent isn't processing alerts.
"""

import psycopg2
import json
import os
from datetime import datetime

DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'database': os.getenv('POSTGRES_DB', 'truelift'),
    'user': os.getenv('POSTGRES_USER', 'truelift_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'truelift_pass')
}

FALLBACK_STRATEGY = {
    "explanation": "Sales are significantly below predictions, indicating potential promotion cannibalization or market saturation.",
    "primary_recommendation": {
        "action": "Stop Promotion",
        "details": "Immediately halt the current promotion and revert to original pricing",
        "expected_impact": "Reduce revenue loss and restore normal sales patterns"
    },
    "alternatives": [
        {
            "action": "Adjust Discount",
            "details": "Reduce discount by 10-15% to test price sensitivity",
            "expected_impact": "Balance promotion appeal with profitability"
        },
        {
            "action": "Target Specific Segments",
            "details": "Limit promotion to loyalty members or new customers only",
            "expected_impact": "Improve conversion rates and reduce cannibalization"
        }
    ],
    "confidence_score": 0.75
}

def generate_strategies():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # Find alerts without strategies
            cursor.execute("""
                SELECT ca.alert_id 
                FROM cannibalization_alerts ca
                LEFT JOIN ai_strategies s ON ca.alert_id = s.alert_id
                WHERE s.strategy_id IS NULL
            """)
            
            alerts_without_strategies = cursor.fetchall()
            
            if not alerts_without_strategies:
                print("✅ All alerts already have strategies!")
                return
            
            print(f"📝 Generating strategies for {len(alerts_without_strategies)} alerts...")
            
            for (alert_id,) in alerts_without_strategies:
                strategy_id = f"STRAT-{alert_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                
                cursor.execute("""
                    INSERT INTO ai_strategies 
                    (strategy_id, alert_id, explanation, recommended_action, 
                     alternative_actions, confidence_score, generated_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    strategy_id,
                    alert_id,
                    FALLBACK_STRATEGY['explanation'],
                    json.dumps(FALLBACK_STRATEGY['primary_recommendation']),
                    json.dumps(FALLBACK_STRATEGY['alternatives']),
                    FALLBACK_STRATEGY['confidence_score'],
                    'fallback-script'
                ))
                
                # Update alert status
                cursor.execute("""
                    UPDATE cannibalization_alerts 
                    SET status = 'strategy_generated' 
                    WHERE alert_id = %s
                """, (alert_id,))
            
            conn.commit()
            print(f"✅ Generated {len(alerts_without_strategies)} strategies!")
            
    finally:
        conn.close()

if __name__ == "__main__":
    generate_strategies()
