from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import json
import os
import logging
from kafka import KafkaProducer
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TrueLift API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'database': os.getenv('POSTGRES_DB', 'truelift'),
    'user': os.getenv('POSTGRES_USER', 'truelift_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'truelift_pass')
}

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

kafka_producer = KafkaProducer(
    bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9094'),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


class AlertResponse(BaseModel):
    alert_id: str
    promo_id: str
    product_name: str
    actual_sales: int
    predicted_sales: int
    loss_percentage: float
    loss_amount: float
    severity: str
    status: str
    alert_timestamp: str
    burst_id: Optional[str] = None
    demo_queued_at: Optional[str] = None
    burst_event_count: Optional[int] = None
    strategy: Optional[Dict] = None
    burst_id: Optional[str] = None
    demo_queued_at: Optional[str] = None


class UserActionRequest(BaseModel):
    alert_id: str
    promo_id: str
    action_type: str
    action_details: Optional[Dict] = None
    performed_by: str = "manager"

class DemoTriggerRequest(BaseModel):
    burst_size: int = 6


class PromotionResponse(BaseModel):
    promo_id: str
    product_name: str
    original_price: float
    promo_price: float
    discount_percentage: float
    is_active: bool
    predicted_sales: int


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def _iso_with_z(dt_obj):
    if not dt_obj:
        return None
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    else:
        dt_obj = dt_obj.astimezone(timezone.utc)
    return dt_obj.isoformat().replace("+00:00", "Z")


@app.get("/")
async def root():
    return {
        "service": "TrueLift API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    try:
        conn = get_db_connection()
        conn.close()
        redis_client.ping()
        return {"status": "healthy", "database": "connected", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(status: Optional[str] = None, limit: int = 50):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            if status:
                cursor.execute("""
                    SELECT * FROM cannibalization_alerts 
                    WHERE status = %s 
                    ORDER BY alert_timestamp DESC 
                    LIMIT %s
                """, (status, limit))
            else:
                # Prioritize showing alerts with strategies, then pending
                cursor.execute("""
                    SELECT * FROM cannibalization_alerts 
                    ORDER BY 
                        CASE 
                            WHEN status = 'strategy_generated' THEN 1
                            WHEN status = 'pending' THEN 2
                            WHEN status = 'action_taken' THEN 3
                            ELSE 4
                        END,
                        alert_timestamp DESC 
                    LIMIT %s
                """, (limit,))
            
            alerts = cursor.fetchall()
            
            for alert in alerts:
                if 'alert_timestamp' in alert and alert['alert_timestamp']:
                    alert['alert_timestamp'] = _iso_with_z(alert['alert_timestamp'])
                
                strategy_json = redis_client.get(f"strategy:{alert['alert_id']}")
                if strategy_json:
                    alert['strategy'] = json.loads(strategy_json)

                demo_json = redis_client.get(f"alert_demo:{alert['alert_id']}")
                if demo_json:
                    try:
                        demo_data = json.loads(demo_json)
                        alert['burst_id'] = demo_data.get('burst_id')
                        alert['demo_queued_at'] = demo_data.get('demo_queued_at')
                        alert['burst_event_count'] = demo_data.get('burst_event_count')
                    except Exception:
                        pass
            
            return [dict(alert) for alert in alerts]
    finally:
        conn.close()


@app.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT ca.*, s.explanation, s.recommended_action, s.alternative_actions, s.confidence_score
                FROM cannibalization_alerts ca
                LEFT JOIN ai_strategies s ON ca.alert_id = s.alert_id
                WHERE ca.alert_id = %s
            """, (alert_id,))
            
            alert = cursor.fetchone()
            if not alert:
                raise HTTPException(status_code=404, detail="Alert not found")
            
            alert_dict = dict(alert)
            
            # Convert datetime to ISO string
            if 'alert_timestamp' in alert_dict and alert_dict['alert_timestamp']:
                alert_dict['alert_timestamp'] = _iso_with_z(alert_dict['alert_timestamp'])
            
            if alert_dict.get('recommended_action'):
                recommended = alert_dict.pop('recommended_action')
                alternatives = alert_dict.pop('alternative_actions')
                alert_dict['strategy'] = {
                    'explanation': alert_dict.pop('explanation'),
                    'primary_recommendation': recommended if isinstance(recommended, dict) else json.loads(recommended),
                    'alternatives': alternatives if isinstance(alternatives, list) else json.loads(alternatives),
                    'confidence_score': float(alert_dict.pop('confidence_score'))
                }

            demo_json = redis_client.get(f"alert_demo:{alert_id}")
            if demo_json:
                try:
                    demo_data = json.loads(demo_json)
                    alert_dict['burst_id'] = demo_data.get('burst_id')
                    alert_dict['demo_queued_at'] = demo_data.get('demo_queued_at')
                    alert_dict['burst_event_count'] = demo_data.get('burst_event_count')
                except Exception:
                    pass
            
            return alert_dict
    finally:
        conn.close()


@app.get("/promotions", response_model=List[PromotionResponse])
async def get_promotions(is_active: Optional[bool] = None):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            if is_active is not None:
                cursor.execute("""
                    SELECT * FROM promotions 
                    WHERE is_active = %s 
                    ORDER BY created_at DESC
                """, (is_active,))
            else:
                cursor.execute("""
                    SELECT * FROM promotions 
                    ORDER BY created_at DESC
                """)
            
            return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@app.post("/actions")
async def create_user_action(action: UserActionRequest):
    action_id = f"ACTION-{uuid.uuid4().hex[:12]}"
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_actions 
                (action_id, alert_id, promo_id, action_type, action_details, performed_by, action_timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                action_id,
                action.alert_id,
                action.promo_id,
                action.action_type,
                json.dumps(action.action_details) if action.action_details else None,
                action.performed_by,
                datetime.utcnow()
            ))
            
            if action.action_type == "stop_promotion":
                cursor.execute("""
                    UPDATE promotions 
                    SET is_active = false, updated_at = %s 
                    WHERE promo_id = %s
                """, (datetime.utcnow(), action.promo_id))
            
            cursor.execute("""
                UPDATE cannibalization_alerts 
                SET status = 'action_taken' 
                WHERE alert_id = %s
            """, (action.alert_id,))
            
            conn.commit()
        
        feedback_data = {
            'action_id': action_id,
            'alert_id': action.alert_id,
            'promo_id': action.promo_id,
            'action_type': action.action_type,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'resolved'
        }
        kafka_producer.send('user-actions', value=feedback_data)
        
        await manager.broadcast({
            'type': 'action_taken',
            'data': feedback_data
        })
        
        return {
            "action_id": action_id,
            "status": "success",
            "message": f"Action '{action.action_type}' executed successfully"
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/dashboard/stats")
async def get_dashboard_stats():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_alerts,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_alerts,
                    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_alerts,
                    SUM(loss_amount) as total_loss,
                    AVG(loss_percentage) as avg_loss_percentage
                FROM cannibalization_alerts
                WHERE DATE(alert_timestamp) = CURRENT_DATE
            """)
            alerts_stats = dict(cursor.fetchone())
            
            cursor.execute("""
                SELECT COUNT(*) as active_promotions
                FROM promotions
                WHERE is_active = true
            """)
            promo_stats = dict(cursor.fetchone())
            
            cursor.execute("""
                SELECT COUNT(*) as total_actions
                FROM user_actions
                WHERE DATE(action_timestamp) = CURRENT_DATE
            """)
            action_stats = dict(cursor.fetchone())
            
            return {
                **alerts_stats,
                **promo_stats,
                **action_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
    finally:
        conn.close()


@app.get("/feedback")
async def get_feedback(limit: int = 20):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT f.*, ua.action_type, p.product_name
                FROM feedback_loop f
                JOIN user_actions ua ON f.action_id = ua.action_id
                JOIN promotions p ON f.promo_id = p.promo_id
                ORDER BY f.feedback_timestamp DESC
                LIMIT %s
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@app.get("/actions/recent")
async def get_recent_actions(limit: int = 10):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT ua.*, ca.product_name, p.promo_price, p.original_price
                FROM user_actions ua
                JOIN cannibalization_alerts ca ON ua.alert_id = ca.alert_id
                LEFT JOIN promotions p ON ua.promo_id = p.promo_id
                ORDER BY ua.action_timestamp DESC
                LIMIT %s
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/internal/broadcast-alert")
async def broadcast_alert(alert_data: dict):
    """Internal endpoint for services to broadcast new alerts to WebSocket clients"""
    try:
        await manager.broadcast({
            'type': 'new_alert',
            'data': alert_data
        })
        logger.info(f"Broadcasted alert {alert_data.get('alert_id')} to {len(manager.active_connections)} clients")
        return {"status": "broadcasted", "clients": len(manager.active_connections)}
    except Exception as e:
        logger.error(f"Error broadcasting alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/demo/trigger")
async def trigger_demo(burst: DemoTriggerRequest):
    """Queue a small demo burst for the simulator (only active when DEMO_MODE=true)."""
    try:
        burst_size = max(1, min(20, burst.burst_size))
        queued_at = _iso_with_z(datetime.utcnow().replace(tzinfo=timezone.utc))
        burst_id = f"DEMO-{uuid.uuid4().hex[:10]}"
        redis_client.rpush("demo:burst", json.dumps({
            "burst_id": burst_id,
            "burst_size": burst_size,
            "queued_at": queued_at
        }))
        return {"status": "queued", "burst_size": burst_size, "queued_at": queued_at, "burst_id": burst_id}
    except Exception as e:
        logger.error(f"Error queuing demo burst: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
