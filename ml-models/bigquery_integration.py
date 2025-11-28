import os
from google.cloud import bigquery
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BigQueryExporter:
    def __init__(self):
        self.project_id = os.getenv('GCP_PROJECT_ID')
        self.dataset_id = os.getenv('BIGQUERY_DATASET', 'truelift_data')
        self.client = bigquery.Client(project=self.project_id)
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        tables_schema = {
            'sales_events': [
                bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("promo_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("shopper_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("quantity", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("price", "FLOAT", mode="REQUIRED"),
                bigquery.SchemaField("total_amount", "FLOAT", mode="REQUIRED"),
                bigquery.SchemaField("event_timestamp", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("is_cannibalized", "BOOLEAN", mode="NULLABLE"),
            ],
            'historical_sales': [
                bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
                bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("total_sales", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("revenue", "FLOAT", mode="REQUIRED"),
                bigquery.SchemaField("avg_price", "FLOAT", mode="REQUIRED"),
            ],
        }

        for table_name, schema in tables_schema.items():
            table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
            try:
                self.client.get_table(table_id)
                logger.info(f"Table {table_id} already exists")
            except Exception:
                table = bigquery.Table(table_id, schema=schema)
                table = self.client.create_table(table)
                logger.info(f"Created table {table_id}")

    def export_sales_event(self, event_data: dict):
        table_id = f"{self.project_id}.{self.dataset_id}.sales_events"
        
        rows_to_insert = [{
            "event_id": event_data['event_id'],
            "promo_id": event_data['promo_id'],
            "product_id": event_data['product_id'],
            "shopper_id": event_data['shopper_id'],
            "quantity": event_data['quantity'],
            "price": event_data['price'],
            "total_amount": event_data['total_amount'],
            "event_timestamp": event_data['event_timestamp'],
            "is_cannibalized": event_data.get('is_cannibalized', False),
        }]
        
        errors = self.client.insert_rows_json(table_id, rows_to_insert)
        if errors:
            logger.error(f"BigQuery insert errors: {errors}")
        else:
            logger.debug(f"Exported event {event_data['event_id']} to BigQuery")

    def get_historical_sales(self, product_id: str, days: int = 30):
        query = f"""
            SELECT 
                DATE(event_timestamp) as date,
                product_id,
                COUNT(*) as total_sales,
                SUM(total_amount) as revenue,
                AVG(price) as avg_price
            FROM `{self.project_id}.{self.dataset_id}.sales_events`
            WHERE product_id = @product_id
                AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
            GROUP BY date, product_id
            ORDER BY date DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("days", "INT64", days),
            ]
        )
        
        query_job = self.client.query(query, job_config=job_config)
        results = query_job.result()
        
        return [dict(row) for row in results]
