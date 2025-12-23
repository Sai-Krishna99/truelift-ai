from flask import Flask, request, jsonify
from google.cloud import aiplatform
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

PROJECT_ID = os.getenv('GCP_PROJECT_ID')
REGION = os.getenv('GCP_REGION', 'us-central1')
ENDPOINT_ID = os.getenv('VERTEX_ENDPOINT_ID')

aiplatform.init(project=PROJECT_ID, location=REGION)
endpoint = aiplatform.Endpoint(ENDPOINT_ID)


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "inference-service"}), 200


@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        
        instances = data.get('instances', [])
        
        if not instances:
            return jsonify({"error": "No instances provided"}), 400
        
        predictions = endpoint.predict(instances=instances)
        
        return jsonify({
            "predictions": predictions.predictions,
            "deployed_model_id": predictions.deployed_model_id,
        }), 200
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/predict/sales', methods=['POST'])
def predict_sales():
    try:
        data = request.get_json()
        
        product_id = data.get('product_id')
        promo_id = data.get('promo_id')
        historical_avg = data.get('historical_avg_sales')
        
        if not all([product_id, promo_id, historical_avg]):
            return jsonify({"error": "Missing required fields"}), 400
        
        instances = [{
            "product_id": product_id,
            "promo_id": promo_id,
            "historical_avg_sales": historical_avg,
        }]
        
        predictions = endpoint.predict(instances=instances)
        
        return jsonify({
            "product_id": product_id,
            "promo_id": promo_id,
            "predicted_sales": predictions.predictions[0],
        }), 200
        
    except Exception as e:
        logger.error(f"Sales prediction error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/batch/predict', methods=['POST'])
def batch_predict():
    try:
        data = request.get_json()
        instances = data.get('instances', [])
        
        if not instances or len(instances) > 100:
            return jsonify({"error": "Provide 1-100 instances"}), 400
        
        predictions = endpoint.predict(instances=instances)
        
        results = []
        for i, pred in enumerate(predictions.predictions):
            results.append({
                "instance_index": i,
                "prediction": pred,
                "input": instances[i]
            })
        
        return jsonify({
            "results": results,
            "count": len(results)
        }), 200
        
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
