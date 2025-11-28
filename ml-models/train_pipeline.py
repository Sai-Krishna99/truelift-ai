import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bigquery_integration import BigQueryExporter
from vertex_ai_integration import VertexAITrainer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Phase 1: Vertex AI Training Pipeline ===")
    
    project_id = os.getenv('GCP_PROJECT_ID')
    if not project_id:
        logger.error("GCP_PROJECT_ID environment variable not set")
        return
    
    trainer = VertexAITrainer()
    
    logger.info("Step 1: Preparing training data from BigQuery...")
    dataset_table = f"{project_id}.truelift_data.sales_events"
    training_data_path = trainer.prepare_training_data(dataset_table)
    
    logger.info("Step 2: Training AutoML model...")
    model = trainer.train_automl_model(
        dataset_display_name="truelift-sales-prediction",
        target_column="actual_sales"
    )
    
    logger.info(f"Step 3: Model trained successfully: {model.resource_name}")
    
    logger.info("Step 4: Registering model in Vertex AI Model Registry...")
    registered_model = trainer.register_model(model.resource_name, "v1")
    
    logger.info(f"Step 5: Deploying model to endpoint...")
    endpoint = trainer.deploy_to_endpoint(registered_model.resource_name)
    
    logger.info("=== Training Pipeline Complete ===")
    logger.info(f"Endpoint ID: {endpoint.resource_name}")
    logger.info(f"Add this to your .env file:")
    logger.info(f"VERTEX_ENDPOINT_ID={endpoint.resource_name}")


if __name__ == "__main__":
    main()
