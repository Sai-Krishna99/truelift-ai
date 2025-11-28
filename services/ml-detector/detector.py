import json
import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List
from kafka import KafkaConsumer, KafkaProducer
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
from sklearn.ensemble import IsolationForest
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        
        self.consumer = KafkaConsumer(
            'shopping-events',
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='ml-detector-group',
            auto_offset_reset='latest'
        )
        
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
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
        
        predicted_sales_per_minute = promo_data['predicted_sales'] / (7 * 24 * 60)
        
        threshold = 0.7
        is_cannibalized = actual_sales < (predicted_sales_per_minute * threshold)
        
        events = aggregated_data.get('events', [])
        if events:
            cannibalized_events = [e for e in events if e.get('is_cannibalized', False)]
            cannibalization_rate = len(cannibalized_events) / len(events)
            is_cannibalized = is_cannibalized or cannibalization_rate > 0.3
        
        return is_cannibalized

    def _calculate_loss(self, promo_id: str, actual_sales: int) -> Dict:
        promo_data = self._fetch_promotion_data(promo_id)
        if not promo_data:
            return {}
        
        predicted_sales_per_minute = promo_data['predicted_sales'] / (7 * 24 * 60)
        sales_difference = int(predicted_sales_per_minute - actual_sales)
        loss_percentage = (sales_difference / predicted_sales_per_minute * 100) if predicted_sales_per_minute > 0 else 0
        loss_amount = sales_difference * promo_data['promo_price']
        
        return {
            'actual_sales': actual_sales,
            'predicted_sales': int(predicted_sales_per_minute),
            'sales_difference': sales_difference,
            'loss_percentage': round(loss_percentage, 2),
            'loss_amount': round(loss_amount, 2)
        }

    def _trigger_alert(self, promo_id: str, loss_data: Dict):
        promo_data = self._fetch_promotion_data(promo_id)
        if not promo_data:
            return
        
        alert_data = {
            'alert_id': f"ALERT-{promo_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            'promo_id': promo_id,
            'product_id': promo_data['product_id'],
            'product_name': promo_data['product_name'],
            'alert_timestamp': datetime.utcnow().isoformat(),
            'severity': 'high' if loss_data['loss_percentage'] > 40 else 'medium',
            **loss_data
        }
        
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO cannibalization_alerts 
                    (alert_id, promo_id, product_id, product_name, actual_sales, predicted_sales, 
                     sales_difference, loss_percentage, loss_amount, alert_timestamp, severity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    alert_data['alert_id'],
                    alert_data['promo_id'],
                    alert_data['product_id'],
                    alert_data['product_name'],
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
        
        self.producer.send('cannibalization-alerts', value=alert_data)
        logger.warning(f"🚨 CANNIBALIZATION DETECTED: {alert_data['product_name']} - "
                      f"Loss: {alert_data['loss_percentage']}% (${alert_data['loss_amount']})")

    def process_events(self):
        logger.info("Starting ML Cannibalization Detector...")
        
        for message in self.consumer:
            event = message.value
            
            self._store_sales_event(event)
            
            self.aggregator.add_event(event)
            
            if self.aggregator.should_aggregate():
                aggregated_data = self.aggregator.get_aggregated_data()
                
                for promo_id, sales_info in aggregated_data.items():
                    actual_sales = sales_info['count']
                    
                    is_cannibalized = self._detect_cannibalization(
                        promo_id, actual_sales, sales_info
                    )
                    
                    if is_cannibalized:
                        loss_data = self._calculate_loss(promo_id, actual_sales)
                        if loss_data:
                            self._trigger_alert(promo_id, loss_data)
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
