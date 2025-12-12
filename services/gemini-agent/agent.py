import json
import os
import logging
from typing import Dict, List
from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from google import genai
from datetime import datetime
import time
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiStrategyAgent:
    def __init__(self):
        self.kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9094')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'database': os.getenv('POSTGRES_DB', 'truelift'),
            'user': os.getenv('POSTGRES_USER', 'truelift_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'truelift_pass')
        }
        
        self.client = genai.Client(api_key=self.gemini_api_key)
        
        self.consumer = KafkaConsumer(
            'cannibalization-alerts',
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='gemini-agent-group',
            auto_offset_reset='latest',
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000,
            max_poll_interval_ms=300000,
            max_poll_records=5
        )
        
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )

        self.cache_ttl_seconds = int(os.getenv('STRATEGY_CACHE_TTL', '900'))
        self.rate_limit_window = int(os.getenv('STRATEGY_RATE_LIMIT_SECONDS', '600'))


    def _get_db_connection(self):
        return psycopg2.connect(**self.db_config)

    def _get_cached_strategy(self, promo_id: str) -> Dict:
        cached = self.redis_client.get(f"strategy_cache:{promo_id}")
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                return None
        return None

    def _set_cached_strategy(self, promo_id: str, strategy: Dict):
        try:
            self.redis_client.setex(
                f"strategy_cache:{promo_id}",
                self.cache_ttl_seconds,
                json.dumps(strategy)
            )
            self.redis_client.setex(
                f"strategy_last:{promo_id}",
                self.rate_limit_window,
                str(int(time.time()))
            )
        except Exception as e:
            logger.warning(f"Failed to cache strategy: {e}")

    def _fetch_alert_context(self, alert_data: Dict) -> Dict:
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT p.*, 
                           COUNT(se.id) as recent_sales,
                           AVG(se.total_amount) as avg_order_value
                    FROM promotions p
                    LEFT JOIN sales_events se ON p.promo_id = se.promo_id
                    WHERE p.promo_id = %s
                    GROUP BY p.id
                """, (alert_data['promo_id'],))
                promo_context = dict(cursor.fetchone()) if cursor.rowcount > 0 else {}
                
                cursor.execute("""
                    SELECT COUNT(*) as total_alerts,
                           AVG(loss_percentage) as avg_loss_percentage
                    FROM cannibalization_alerts
                    WHERE promo_id = %s
                """, (alert_data['promo_id'],))
                alert_history = dict(cursor.fetchone()) if cursor.rowcount > 0 else {}
                
                return {
                    'promotion': promo_context,
                    'alert_history': alert_history,
                    'current_alert': alert_data
                }
        finally:
            conn.close()

    def _generate_gemini_prompt(self, context: Dict) -> str:
        alert = context['current_alert']
        promo = context['promotion']
        
        prompt = f"""You are an expert retail pricing strategist analyzing a promotion cannibalization issue.

**Current Situation:**
- Product: {alert['product_name']} (ID: {alert['product_id']})
- Promotion: {alert['promo_id']}
- Original Price: ${promo.get('original_price', 'N/A')}
- Promotional Price: ${promo.get('promo_price', 'N/A')}
- Discount: {promo.get('discount_percentage', 'N/A')}%

**Performance Metrics:**
- Predicted Sales (per minute): {alert['predicted_sales']} units
- Actual Sales (per minute): {alert['actual_sales']} units
- Sales Shortfall: {alert['sales_difference']} units
- Loss Percentage: {alert['loss_percentage']}%
- Estimated Revenue Loss: ${alert['loss_amount']}

**Task:**
1. Explain WHY this cannibalization is occurring in 2-3 sentences
2. Provide ONE primary recommended action with specific details
3. Suggest TWO alternative strategies

Format your response as JSON:
{{
    "explanation": "Your detailed explanation here",
    "primary_recommendation": {{
        "action": "Action name",
        "details": "Specific implementation details",
        "expected_impact": "Expected outcome"
    }},
    "alternatives": [
        {{
            "action": "Alternative 1",
            "details": "Implementation details",
            "expected_impact": "Expected outcome"
        }},
        {{
            "action": "Alternative 2",
            "details": "Implementation details",
            "expected_impact": "Expected outcome"
        }}
    ],
    "confidence_score": 0.85
}}

Provide actionable, data-driven recommendations."""
        
        return prompt

    def _query_gemini(self, prompt: str) -> Dict:
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            response_text = response.text.strip()
            
            if response_text.startswith('```json'):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith('```'):
                response_text = response_text[3:-3].strip()
            
            strategy = json.loads(response_text)
            return strategy
        except Exception as e:
            logger.error(f"Error querying Gemini: {e}")
            return self._get_fallback_strategy()

    def _get_fallback_strategy(self) -> Dict:
        return {
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

    def _store_strategy(self, alert_id: str, strategy: Dict):
        strategy_id = f"STRAT-{alert_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO ai_strategies 
                    (strategy_id, alert_id, explanation, recommended_action, 
                     alternative_actions, confidence_score, generated_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    strategy_id,
                    alert_id,
                    strategy['explanation'],
                    json.dumps(strategy['primary_recommendation']),
                    json.dumps(strategy['alternatives']),
                    strategy.get('confidence_score', 0.8),
                    'gemini-pro'
                ))
                conn.commit()
        finally:
            conn.close()
        
        self.redis_client.setex(
            f"strategy:{alert_id}",
            3600,
            json.dumps(strategy)
        )
        
        logger.info(f"Strategy generated for alert {alert_id}")

    def _update_alert_status(self, alert_id: str, status: str):
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE cannibalization_alerts 
                    SET status = %s 
                    WHERE alert_id = %s
                """, (status, alert_id))
                conn.commit()
        finally:
            conn.close()

    def process_alerts(self):
        logger.info("Starting Gemini Strategy Agent...")
        
        backend_url = os.getenv('BACKEND_URL', 'http://backend-api:8000')
        
        for message in self.consumer:
            try:
                alert_data = message.value
                alert_id = alert_data['alert_id']
                promo_id = alert_data['promo_id']
                
                logger.info(f"Processing alert: {alert_id}")
                
                cached_strategy = self._get_cached_strategy(promo_id)
                last_generated = self.redis_client.get(f"strategy_last:{promo_id}")
                now_ts = int(time.time())

                context = self._fetch_alert_context(alert_data)
                
                prompt = self._generate_gemini_prompt(context)

                strategy = None
                if cached_strategy and last_generated and (now_ts - int(last_generated) < self.rate_limit_window):
                    strategy = cached_strategy
                    logger.info(f"Using cached strategy for {promo_id}")
                else:
                    strategy = self._query_gemini(prompt)
                    self._set_cached_strategy(promo_id, strategy)
                
                self._store_strategy(alert_id, strategy)
                
                self._update_alert_status(alert_id, 'strategy_generated')
                
                # Broadcast new alert to all WebSocket clients
                try:
                    broadcast_data = {
                        **alert_data,
                        'strategy': strategy,
                        'status': 'strategy_generated'
                    }
                    requests.post(
                        f"{backend_url}/internal/broadcast-alert",
                        json=broadcast_data,
                        timeout=2
                    )
                    logger.info(f"Broadcasted alert {alert_id} via WebSocket")
                except Exception as broadcast_error:
                    logger.warning(f"Failed to broadcast alert: {broadcast_error}")
                
                logger.info(f"✓ Strategy generated for {alert_id}: {strategy['primary_recommendation']['action']}")
            except Exception as e:
                logger.error(f"Error processing alert {alert_data.get('alert_id', 'unknown')}: {e}", exc_info=True)
                # Continue processing next message even if this one fails
                continue

    def run(self):
        try:
            self.process_alerts()
        except KeyboardInterrupt:
            logger.info("Shutting down Gemini Agent...")
            self.consumer.close()
        except Exception as e:
            logger.error(f"Error in Gemini Agent: {e}")
            raise


if __name__ == "__main__":
    agent = GeminiStrategyAgent()
    agent.run()
