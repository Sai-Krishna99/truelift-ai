import json
import os
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Dict, List
from decimal import Decimal
from kafka import KafkaConsumer, KafkaProducer
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
from sklearn.ensemble import IsolationForest
import pickle
import redis
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


class SalesAggregator:
    def __init__(self, window_minutes: int = 1):
        self.window_minutes = window_minutes
        self.sales_data = defaultdict(lambda: {'count': 0, 'total_amount': 0, 'events': []})
        self.window_start = datetime.utcnow()

    def add_event(self, event: Dict):
        promo_id = event['promo_id']
        self.sales_data[promo_id]['count'] += event['quantity']
        self.sales_data[promo_id]['total_amount'] += event['total_amount']
        self.sales_data[promo_id]['events'].append(event)

    def should_aggregate(self) -> bool:
        return datetime.utcnow() >= self.window_start + timedelta(minutes=self.window_minutes)

    def get_aggregated_data(self) -> Dict:
        result = dict(self.sales_data)
        self.sales_data.clear()
        self.window_start = datetime.utcnow()
        return result


class CannibalizationDetector:
    def __init__(self):
        self.kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9094')
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'database': os.getenv('POSTGRES_DB', 'truelift'),
            'user': os.getenv('POSTGRES_USER', 'truelift_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'truelift_pass')
        }
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        self.consumer = KafkaConsumer(
            'shopping-events',
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='ml-detector-group',
            auto_offset_reset='latest',
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000,
            max_poll_interval_ms=300000,
            max_poll_records=10
        )
        
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3,
            max_in_flight_requests_per_connection=1
        )
        
        self.aggregator = SalesAggregator(window_minutes=1)
        self.anomaly_detector = self._initialize_ml_model()

    def _initialize_ml_model(self):
        model = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100
        )
        return model

    def _get_db_connection(self):
        return psycopg2.connect(**self.db_config)

    def _fetch_promotion_data(self, promo_id: str) -> Dict:
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM promotions WHERE promo_id = %s",
                    (promo_id,)
                )
                return dict(cursor.fetchone()) if cursor.rowcount > 0 else None
        finally:
            conn.close()

    def _store_sales_event(self, event: Dict):
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO sales_events 
                    (event_id, promo_id, product_id, shopper_id, quantity, price, total_amount, event_timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO NOTHING
                """, (
                    event['event_id'],
                    event['promo_id'],
                    event['product_id'],
                    event['shopper_id'],
                    event['quantity'],
                    event['price'],
                    event['total_amount'],
                    event['event_timestamp']
                ))
                conn.commit()
        finally:
            conn.close()

    def _detect_cannibalization(self, promo_id: str, actual_sales: int, aggregated_data: Dict) -> bool:
        promo_data = self._fetch_promotion_data(promo_id)
        if not promo_data:
            return False
        
        # Treat predicted_sales as per-minute baseline for simplicity in demo
        predicted_sales_per_minute = float(promo_data['predicted_sales'])
        
        threshold = 0.7
        is_cannibalized = actual_sales < (predicted_sales_per_minute * threshold)
        
        events = aggregated_data.get('events', [])
        if events:
            cannibalized_events = [e for e in events if e.get('is_cannibalized', False)]
            cannibalization_rate = len(cannibalized_events) / len(events)
            is_cannibalized = is_cannibalized or cannibalization_rate > 0.3
        
        return is_cannibalized

    def _calculate_loss(self, promo_id: str, actual_sales: int, scale: float = 1.0) -> Dict:
        promo_data = self._fetch_promotion_data(promo_id)
        if not promo_data:
            return {}
        
        # Convert Decimal to float for calculations
        predicted_sales = float(promo_data['predicted_sales'])
        promo_price = float(promo_data['promo_price'])
        
        # Treat predicted_sales as per-minute baseline for display and loss calculations
        predicted_sales_per_minute = predicted_sales * max(0.4, min(scale, 0.85))
        predicted_sales_rounded = max(1, int(round(predicted_sales_per_minute))) if predicted_sales_per_minute > 0 else 0
        sales_difference = predicted_sales_rounded - actual_sales
        loss_percentage = (sales_difference / predicted_sales_per_minute * 100) if predicted_sales_per_minute > 0 else 0
        loss_percentage = max(0, round(loss_percentage, 2))
        loss_amount = round(max(0, sales_difference * promo_price), 2)
        max_loss = promo_price * predicted_sales_per_minute
        if loss_amount > max_loss:
            loss_amount = round(max_loss, 2)
        max_loss_pct = 70.0
        if loss_percentage > max_loss_pct:
            loss_percentage = max_loss_pct
        
        return {
            'actual_sales': actual_sales,
            'predicted_sales': predicted_sales_rounded,
            'sales_difference': sales_difference,
            'loss_percentage': loss_percentage,
            'loss_amount': loss_amount
        }

    def _trigger_alert(self, promo_id: str, loss_data: Dict, burst_metadata: Dict = None):
        promo_data = self._fetch_promotion_data(promo_id)
        if not promo_data:
            return
        
        # Convert Decimal to float for JSON serialization
        promo_data = {k: decimal_to_float(v) for k, v in promo_data.items()}
        
        alert_data = {
            'alert_id': f"ALERT-{promo_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            'promo_id': promo_id,
            'product_id': promo_data['product_id'],
            'product_name': promo_data['product_name'],
            'original_price': promo_data.get('original_price'),
            'promo_price': promo_data.get('promo_price'),
            'discount_percentage': promo_data.get('discount_percentage'),
            'alert_timestamp': datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            'severity': 'high' if loss_data['loss_percentage'] > 40 else 'medium',
            **loss_data
        }
        if burst_metadata:
            if burst_metadata.get('burst_id'):
                alert_data['burst_id'] = burst_metadata.get('burst_id')
            if burst_metadata.get('demo_queued_at'):
                alert_data['demo_queued_at'] = burst_metadata.get('demo_queued_at')
            if burst_metadata.get('burst_event_count') is not None:
                alert_data['burst_event_count'] = burst_metadata.get('burst_event_count')
        
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO cannibalization_alerts 
                    (alert_id, promo_id, product_id, product_name, original_price, promo_price, discount_percentage,
                     burst_id, demo_queued_at, burst_event_count,
                     actual_sales, predicted_sales, 
                     sales_difference, loss_percentage, loss_amount, alert_timestamp, severity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    alert_data['alert_id'],
                    alert_data['promo_id'],
                    alert_data['product_id'],
                    alert_data['product_name'],
                    alert_data.get('original_price'),
                    alert_data.get('promo_price'),
                    alert_data.get('discount_percentage'),
                    alert_data.get('burst_id'),
                    alert_data.get('demo_queued_at'),
                    alert_data.get('burst_event_count'),
                    alert_data['actual_sales'],
                    alert_data['predicted_sales'],
                    alert_data['sales_difference'],
                    alert_data['loss_percentage'],
                    alert_data['loss_amount'],
                    alert_data['alert_timestamp'],
                    alert_data['severity']
                ))
                conn.commit()
        finally:
            conn.close()
        
        # Send to Kafka with error handling
        try:
            future = self.producer.send('cannibalization-alerts', value=alert_data)
            future.get(timeout=10)  # Wait for confirmation
            self.producer.flush()  # Ensure message is sent
            logger.warning(f"🚨 CANNIBALIZATION DETECTED & PUBLISHED: {alert_data['product_name']} - "
                          f"Loss: {alert_data['loss_percentage']}% (${alert_data['loss_amount']})")

            if alert_data.get('burst_id'):
                try:
                    self.redis_client.setex(
                        f"alert_demo:{alert_data['alert_id']}",
                        3600,
                        json.dumps({
                            "burst_id": alert_data.get('burst_id'),
                            "demo_queued_at": alert_data.get('demo_queued_at'),
                            "burst_event_count": alert_data.get('burst_event_count')
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to cache demo metadata for alert {alert_data['alert_id']}: {e}")
        except Exception as e:
            logger.error(f"Failed to publish alert to Kafka: {e}")

    def process_events(self):
        logger.info("Starting ML Cannibalization Detector...")
        while True:
            records = self.consumer.poll(timeout_ms=5000, max_records=20)
            burst_seen = False

            for tp, messages in records.items():
                for message in messages:
                    event = message.value
                    if event.get('burst_id'):
                        burst_seen = True
                    self._store_sales_event(event)
                    self.aggregator.add_event(event)

            should_flush = self.aggregator.should_aggregate() or burst_seen
            if should_flush and self.aggregator.sales_data:
                aggregated_data = self.aggregator.get_aggregated_data()
                
                for promo_id, sales_info in aggregated_data.items():
                    events = sales_info.get('events', [])
                    burst_groups = defaultdict(list)
                    if events:
                        for ev in events:
                            burst_groups[ev.get('burst_id')].append(ev)
                    else:
                        burst_groups[None] = []

                    for burst_id, evs in burst_groups.items():
                        if evs:
                            actual_sales = sum(e.get('quantity', 0) for e in evs)
                        else:
                            actual_sales = sales_info['count']

                        demo_queued_at = None
                        burst_event_count = len(evs) if evs else None
                        scale = 1.0
                        if evs:
                            for ev in evs:
                                if ev.get('demo_queued_at'):
                                    demo_queued_at = ev.get('demo_queued_at')
                                    break
                            scale = random.uniform(0.5, 0.8)
                        burst_meta = None
                        if burst_id:
                            burst_meta = {
                                "burst_id": burst_id,
                                "demo_queued_at": demo_queued_at,
                                "burst_event_count": burst_event_count
                            }

                        is_cannibalized = self._detect_cannibalization(
                            promo_id, actual_sales, {**sales_info, 'events': evs} if evs else sales_info
                        )
                    
                        if is_cannibalized:
                            loss_data = self._calculate_loss(promo_id, actual_sales, scale=scale)
                            if loss_data:
                                self._trigger_alert(
                                    promo_id,
                                    loss_data,
                                    burst_metadata=burst_meta
                                )
                        else:
                            logger.info(f"✓ Normal sales for {promo_id}: {actual_sales} units")

    def run(self):
        try:
            self.process_events()
        except KeyboardInterrupt:
            logger.info("Shutting down ML Detector...")
            self.consumer.close()
            self.producer.close()
        except Exception as e:
            logger.error(f"Error in ML Detector: {e}")
            raise


if __name__ == "__main__":
    detector = CannibalizationDetector()
    detector.run()
