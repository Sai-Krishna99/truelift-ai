import json
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict
from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import uuid
import redis
import json
import requests

import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return  # Silent health checks


def run_health_check_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Health check server starting on port {port}...")
    server.serve_forever()


class FeedbackLoopProcessor:
    def __init__(self):
        self.kafka_bootstrap_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9094"
        )
        self.db_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "database": os.getenv("POSTGRES_DB", "truelift"),
            "user": os.getenv("POSTGRES_USER", "truelift_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "truelift_pass"),
        }

        kafka_config = {
            "bootstrap_servers": self.kafka_bootstrap_servers,
            "security_protocol": os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
            "sasl_mechanism": "PLAIN",
            "sasl_plain_username": os.getenv("KAFKA_SASL_USERNAME"),
            "sasl_plain_password": os.getenv("KAFKA_SASL_PASSWORD"),
        }

        if not (
            kafka_config["sasl_plain_username"] and kafka_config["sasl_plain_password"]
        ):
            kafka_config.pop("sasl_mechanism", None)
            kafka_config.pop("sasl_plain_username", None)
            kafka_config.pop("sasl_plain_password", None)
            kafka_config.pop("security_protocol", None)

        self.consumer = KafkaConsumer(
            "user-actions",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id="feedback-loop-group",
            auto_offset_reset="latest",
            **kafka_config,
        )

        self.action_monitoring = {}
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )
        self.backend_url = os.getenv("BACKEND_URL", "http://backend-api:8000")
        self.http_timeout = float(os.getenv("HTTP_TIMEOUT_SECONDS", 2))

    def _get_db_connection(self):
        return psycopg2.connect(**self.db_config)

    def _get_alert_context(self, alert_id: str) -> Dict:
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT alert_timestamp, predicted_sales, promo_price, original_price
                    FROM cannibalization_alerts
                    WHERE alert_id = %s
                """,
                    (alert_id,),
                )
                result = cursor.fetchone()
                return dict(result) if result else {}
        finally:
            conn.close()

    def _get_promotion_data(self, promo_id: str) -> Dict:
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM promotions WHERE promo_id = %s
                """,
                    (promo_id,),
                )
                result = cursor.fetchone()
                return dict(result) if result else None
        finally:
            conn.close()

    def _get_sales_before_action(self, promo_id: str, anchor_ts: str) -> int:
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) as sales_count
                    FROM sales_events
                    WHERE promo_id = %s 
                    AND event_timestamp < %s::timestamp
                    AND event_timestamp > (%s::timestamp - INTERVAL '5 minutes')
                """,
                    (promo_id, anchor_ts, anchor_ts),
                )
                result = cursor.fetchone()
                return result[0] if result else 0
        finally:
            conn.close()

    def _get_sales_after_action(self, promo_id: str, anchor_ts: str) -> int:
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) as sales_count
                    FROM sales_events
                    WHERE promo_id = %s 
                    AND event_timestamp > %s::timestamp
                    AND event_timestamp < (%s::timestamp + INTERVAL '5 minutes')
                """,
                    (promo_id, anchor_ts, anchor_ts),
                )
                result = cursor.fetchone()
                return result[0] if result else 0
        finally:
            conn.close()

    def _calculate_effectiveness(
        self,
        action_type: str,
        sales_before: int,
        sales_after: int,
        old_price: float,
        new_price: float,
    ) -> float:
        try:
            old_price = float(old_price) if old_price is not None else 0.0
            new_price = float(new_price) if new_price is not None else old_price
        except Exception:
            old_price = 0.0
            new_price = 0.0
        if action_type == "stop_promotion":
            if sales_before > 0:
                reduction_rate = (sales_before - sales_after) / sales_before
                return min(100, max(0, reduction_rate * 100))
            return 75.0

        elif action_type == "adjust_price":
            price_increase_ratio = (
                (new_price - old_price) / old_price if old_price > 0 else 0
            )
            sales_change_ratio = (
                (sales_after - sales_before) / sales_before if sales_before > 0 else 0
            )

            if price_increase_ratio > 0 and sales_change_ratio > -0.3:
                effectiveness = 80.0 + (20.0 * (1 - abs(sales_change_ratio)))
            else:
                effectiveness = 50.0 + (sales_change_ratio * 50)

            return min(100, max(0, effectiveness))

        return 60.0

    def _process_stop_promotion(self, action_data: Dict):
        promo_id = action_data["promo_id"]
        action_id = action_data["action_id"]
        alert_id = action_data.get("alert_id")
        anchor_ts = datetime.now(timezone.utc)
        if alert_id:
            ctx = self._get_alert_context(alert_id)
            if ctx.get("alert_timestamp"):
                try:
                    at = ctx["alert_timestamp"]
                    if at.tzinfo is None:
                        at = at.replace(tzinfo=timezone.utc)
                    anchor_ts = at
                except Exception:
                    pass
        ts_query = anchor_ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"Monitoring feedback for stopped promotion: {promo_id}")

        time.sleep(8)

        promo_data = self._get_promotion_data(promo_id)
        if not promo_data:
            return

        sales_before = self._get_sales_before_action(promo_id, ts_query)
        sales_after = self._get_sales_after_action(promo_id, ts_query)

        old_price = promo_data["promo_price"]
        new_price = promo_data["original_price"]

        effectiveness = self._calculate_effectiveness(
            "stop_promotion", sales_before, sales_after, old_price, new_price
        )

        insufficient = sales_after < 2
        # If very low data, soften the score to avoid perfect 100s
        if insufficient:
            effectiveness = max(20.0, min(70.0, effectiveness * 0.7))
        else:
            effectiveness = min(90.0, effectiveness)

        self._store_feedback(
            action_id=action_id,
            promo_id=promo_id,
            old_price=old_price,
            new_price=new_price,
            sales_before=sales_before,
            sales_after=sales_after,
            effectiveness_score=effectiveness,
        )
        if alert_id:
            self._cache_feedback(
                alert_id,
                effectiveness,
                sales_before,
                sales_after,
                old_price,
                new_price,
                insufficient,
            )

        logger.info(
            f"Feedback recorded: Promotion {promo_id} stopped. "
            f"Sales: {sales_before} → {sales_after}, Effectiveness: {effectiveness:.1f}%"
        )

    def _process_adjust_price(self, action_data: Dict):
        promo_id = action_data["promo_id"]
        action_id = action_data["action_id"]
        alert_id = action_data.get("alert_id")
        anchor_ts = datetime.now(timezone.utc)
        if alert_id:
            ctx = self._get_alert_context(alert_id)
            if ctx.get("alert_timestamp"):
                try:
                    at = ctx["alert_timestamp"]
                    if at.tzinfo is None:
                        at = at.replace(tzinfo=timezone.utc)
                    anchor_ts = at
                except Exception:
                    pass
        ts_query = anchor_ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"Monitoring feedback for price adjustment: {promo_id}")

        promo_data = self._get_promotion_data(promo_id)
        if not promo_data:
            return

        try:
            old_price = float(promo_data.get("promo_price") or 0.0)
        except Exception:
            old_price = 0.0

        raw_new_price = action_data.get("new_price") or old_price
        try:
            new_price = float(raw_new_price)
        except Exception:
            new_price = old_price

        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE promotions 
                    SET promo_price = %s, updated_at = %s 
                    WHERE promo_id = %s
                """,
                    (new_price, datetime.utcnow(), promo_id),
                )
                conn.commit()
        finally:
            conn.close()

        time.sleep(8)

        sales_before = self._get_sales_before_action(promo_id, ts_query)
        sales_after = self._get_sales_after_action(promo_id, ts_query)
        price_delta_pct = ((new_price - old_price) / old_price) if old_price else 0.0
        sales_delta = (
            ((sales_after - sales_before) / sales_before) if sales_before > 0 else 0.0
        )
        effectiveness = 50 + (price_delta_pct * 30) + (sales_delta * 40)
        effectiveness = min(90.0, max(10.0, effectiveness))
        insufficient = sales_after < 2
        if insufficient:
            effectiveness = max(20.0, min(80.0, 50 + price_delta_pct * 20))
        else:
            effectiveness = min(90.0, effectiveness)

        self._store_feedback(
            action_id=action_id,
            promo_id=promo_id,
            old_price=old_price,
            new_price=new_price,
            sales_before=sales_before,
            sales_after=sales_after,
            effectiveness_score=effectiveness,
        )
        if alert_id:
            self._cache_feedback(
                alert_id,
                effectiveness,
                sales_before,
                sales_after,
                old_price,
                new_price,
                insufficient,
            )

        logger.info(
            f"Feedback recorded: Price adjusted for {promo_id}. "
            f"${old_price:.2f} → ${new_price:.2f}, Effectiveness: {effectiveness:.1f}%"
        )

    def _store_feedback(
        self,
        action_id: str,
        promo_id: str,
        old_price: float,
        new_price: float,
        sales_before: int,
        sales_after: int,
        effectiveness_score: float,
    ):
        feedback_id = f"FEEDBACK-{uuid.uuid4().hex[:12]}"

        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO feedback_loop 
                    (feedback_id, action_id, promo_id, old_price, new_price, 
                     sales_before, sales_after, effectiveness_score, feedback_timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        feedback_id,
                        action_id,
                        promo_id,
                        old_price,
                        new_price,
                        sales_before,
                        sales_after,
                        effectiveness_score,
                        datetime.utcnow(),
                    ),
                )
                conn.commit()
        finally:
            conn.close()

    def _mark_alert_resolved(self, alert_id: str):
        if not alert_id:
            return
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE cannibalization_alerts
                    SET status = 'resolved'
                    WHERE alert_id = %s
                """,
                    (alert_id,),
                )
                conn.commit()
        finally:
            conn.close()

    def _cache_feedback(
        self,
        alert_id: str,
        effectiveness: float,
        sales_before: int,
        sales_after: int,
        old_price: float,
        new_price: float,
        insufficient: bool = False,
    ):
        try:
            payload_data = {
                "effectiveness_score": float(effectiveness),
                "sales_before": int(sales_before),
                "sales_after": int(sales_after),
                "old_price": float(old_price) if old_price is not None else None,
                "new_price": float(new_price) if new_price is not None else None,
                "insufficient_data": bool(insufficient),
            }
            payload = {k: v for k, v in payload_data.items()}
            self.redis_client.setex(f"feedback:{alert_id}", 1800, json.dumps(payload))
            # Broadcast to backend so UI can flip from pending → measured without polling
            try:
                requests.post(
                    f"{self.backend_url}/internal/broadcast-feedback",
                    json={"alert_id": alert_id, "status": "resolved", **payload},
                    timeout=self.http_timeout,
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast feedback for {alert_id}: {e}")
            # Mark DB status as resolved so subsequent fetches reflect it
            self._mark_alert_resolved(alert_id)
        except Exception as e:
            logger.warning(f"Failed to cache feedback for {alert_id}: {e}")

    def process_actions(self):
        logger.info("Starting Feedback Loop Processor...")

        for message in self.consumer:
            action_data = message.value
            action_type = action_data.get("action_type")

            logger.info(
                f"Processing user action: {action_type} for {action_data['promo_id']}"
            )

            try:
                if action_type == "stop_promotion":
                    self._process_stop_promotion(action_data)
                elif action_type == "adjust_price":
                    self._process_adjust_price(action_data)
                else:
                    logger.warning(f"Unknown action type: {action_type}")
            except Exception as e:
                logger.error(f"Error processing action: {e}")

    def run(self):
        # Start health check server in background thread
        health_thread = threading.Thread(target=run_health_check_server, daemon=True)
        health_thread.start()

        try:
            self.process_actions()
        except KeyboardInterrupt:
            logger.info("Shutting down Feedback Loop Processor...")
            self.consumer.close()
        except Exception as e:
            logger.error(f"Error in Feedback Loop Processor: {e}")
            raise


if __name__ == "__main__":
    processor = FeedbackLoopProcessor()
    processor.run()
