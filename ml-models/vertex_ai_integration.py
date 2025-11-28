import os
from google.cloud import aiplatform
from google.cloud.aiplatform import gapic as aip
import pandas as pd
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VertexAITrainer:
    def __init__(self):
        self.project_id = os.getenv('GCP_PROJECT_ID')
        self.region = os.getenv('GCP_REGION', 'us-central1')
        self.bucket_name = os.getenv('GCS_BUCKET')
        
        aiplatform.init(project=self.project_id, location=self.region)

    def prepare_training_data(self, bigquery_table: str):
        from google.cloud import bigquery
        
        client = bigquery.Client(project=self.project_id)
        
        query = f"""
            SELECT 
                product_id,
                promo_id,
                DATE(event_timestamp) as date,
                COUNT(*) as actual_sales,
                AVG(price) as avg_price,
                SUM(total_amount) as revenue,
                COUNTIF(is_cannibalized) as cannibalized_count
            FROM `{bigquery_table}`
            WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
            GROUP BY product_id, promo_id, date
            ORDER BY date DESC
        """
        
        df = client.query(query).to_dataframe()
        
        gcs_path = f"gs://{self.bucket_name}/training_data/sales_data_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(gcs_path, index=False)
        
        logger.info(f"Training data prepared: {len(df)} rows saved to {gcs_path}")
        return gcs_path

    def train_automl_model(self, dataset_display_name: str, target_column: str = "actual_sales"):
        dataset = aiplatform.TabularDataset.create(
            display_name=dataset_display_name,
            gcs_source=f"gs://{self.bucket_name}/training_data/*.csv",
        )
        
        logger.info(f"Created dataset: {dataset.display_name}")
        
        job = aiplatform.AutoMLTabularTrainingJob(
            display_name=f"cannibalization-automl-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            optimization_prediction_type="regression",
            optimization_objective="minimize-rmse",
        )
        
        model = job.run(
            dataset=dataset,
            target_column=target_column,
            training_fraction_split=0.8,
            validation_fraction_split=0.1,
            test_fraction_split=0.1,
            model_display_name=f"cannibalization-model-{datetime.now().strftime('%Y%m%d')}",
            budget_milli_node_hours=1000,
        )
        
        logger.info(f"Model trained: {model.display_name}")
        return model

    def register_model(self, model_id: str, model_version: str = "v1"):
        model = aiplatform.Model(model_id)
        
        model_registry_name = f"cannibalization-detector-{model_version}"
        
        registered_model = aiplatform.Model.upload(
            display_name=model_registry_name,
            artifact_uri=model.uri,
            serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-6:latest",
        )
        
        logger.info(f"Model registered: {registered_model.display_name}")
        return registered_model

    def deploy_to_endpoint(self, model_id: str, endpoint_display_name: str = "cannibalization-endpoint"):
        model = aiplatform.Model(model_id)
        
        try:
            endpoints = aiplatform.Endpoint.list(
                filter=f'display_name="{endpoint_display_name}"'
            )
            endpoint = endpoints[0] if endpoints else None
        except:
            endpoint = None
        
        if not endpoint:
            endpoint = aiplatform.Endpoint.create(
                display_name=endpoint_display_name,
            )
        
        model.deploy(
            endpoint=endpoint,
            deployed_model_display_name=f"deployed-{datetime.now().strftime('%Y%m%d')}",
            machine_type="n1-standard-4",
            min_replica_count=1,
            max_replica_count=3,
        )
        
        logger.info(f"Model deployed to endpoint: {endpoint.display_name}")
        return endpoint

    def predict(self, endpoint_id: str, instances: list):
        endpoint = aiplatform.Endpoint(endpoint_id)
        
        predictions = endpoint.predict(instances=instances)
        
        return predictions.predictions


class VertexAIInferenceService:
    def __init__(self, endpoint_id: str):
        self.project_id = os.getenv('GCP_PROJECT_ID')
        self.region = os.getenv('GCP_REGION', 'us-central1')
        self.endpoint_id = endpoint_id
        
        aiplatform.init(project=self.project_id, location=self.region)
        self.endpoint = aiplatform.Endpoint(endpoint_id)

    def predict_sales(self, product_id: str, promo_id: str, historical_avg: float):
        instances = [{
            "product_id": product_id,
            "promo_id": promo_id,
            "historical_avg_sales": historical_avg,
        }]
        
        predictions = self.endpoint.predict(instances=instances)
        
        predicted_sales = predictions.predictions[0]
        
        logger.info(f"Predicted sales for {product_id}: {predicted_sales}")
        return predicted_sales

    def batch_predict(self, instances: list):
        predictions = self.endpoint.predict(instances=instances)
        return predictions.predictions
