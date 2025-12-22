import asyncio
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List
import json
from kafka import KafkaProducer
import redis
from dataclasses import dataclass, asdict
import os
import logging

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


@dataclass
class Product:
    product_id: str
    product_name: str
    original_price: float
    category: str
    base_demand: int
    price_sensitivity: str = "medium"  # high, medium, low


@dataclass
class Promotion:
    promo_id: str
    product_id: str
    product_name: str
    original_price: float
    promo_price: float
    discount_percentage: float
    start_date: datetime
    end_date: datetime
    predicted_sales: int


@dataclass
class ShoppingEvent:
    event_id: str
    shopper_id: str
    product_id: str
    product_name: str
    promo_id: str
    quantity: int
    price: float
    total_amount: float
    event_timestamp: str
    is_cannibalized: bool


class VirtualShopperSimulator:
    def __init__(self):
        self.kafka_bootstrap_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9094"
        )
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        self.simulation_enabled = (
            os.getenv("SIMULATION_ENABLED", "true").lower() == "true"
        )
        self.event_rate = int(
            os.getenv("EVENT_RATE_PER_MINUTE", "15")
        )  # Events per promo per minute
        self.paused = False

        kafka_config = {
            "bootstrap_servers": self.kafka_bootstrap_servers,
            "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
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

        self.producer = KafkaProducer(**kafka_config)

        self.redis_client = redis.Redis(
            host=self.redis_host, port=self.redis_port, decode_responses=True
        )

        self.products = self._initialize_products()
        self.promotions = self._initialize_promotions()
        self.active_shoppers = set()

    def _initialize_products(self) -> List[Product]:
        """Initialize diverse product catalog across 6 major categories"""
        return [
            # FOOD & BEVERAGE - High price sensitivity (elastic demand)
            Product(
                "P001",
                "Premium Coffee Beans 1kg",
                24.99,
                "Food & Beverage",
                120,
                "high",
            ),
            Product(
                "P002", "Energy Drink 12-Pack", 18.99, "Food & Beverage", 200, "high"
            ),
            Product(
                "P003",
                "Artisan Dark Chocolate Bar",
                8.99,
                "Food & Beverage",
                150,
                "high",
            ),
            Product(
                "P004",
                "Organic Protein Bars 12ct",
                29.99,
                "Food & Beverage",
                95,
                "medium",
            ),
            Product(
                "P005", "Gourmet Tea Sampler", 34.99, "Food & Beverage", 85, "medium"
            ),
            # HOME & LIVING - Medium-high price sensitivity
            Product(
                "P006", "Scented Candle Set 3pk", 32.99, "Home & Living", 110, "medium"
            ),
            Product(
                "P007",
                "Kitchen Knife Set Premium",
                79.99,
                "Home & Living",
                65,
                "medium",
            ),
            Product(
                "P008", "Throw Blanket Luxury", 49.99, "Home & Living", 88, "medium"
            ),
            Product("P009", "Coffee Maker 12-Cup", 89.99, "Home & Living", 72, "low"),
            Product("P010", "Wall Art Canvas Set", 119.99, "Home & Living", 45, "low"),
            # FASHION - Medium price sensitivity (brand matters)
            Product("P011", "Designer Sunglasses", 149.99, "Fashion", 58, "low"),
            Product("P012", "Leather Wallet Premium", 69.99, "Fashion", 82, "medium"),
            Product("P013", "Cashmere Scarf", 89.99, "Fashion", 67, "medium"),
            Product("P014", "Designer Watch", 299.99, "Fashion", 38, "low"),
            Product("P015", "Leather Handbag", 189.99, "Fashion", 52, "low"),
            # ELECTRONICS - Low-medium price sensitivity (research-driven)
            Product(
                "P016", "Wireless Earbuds Pro", 129.99, "Electronics", 95, "medium"
            ),
            Product("P017", "Smart Watch Fitness", 199.99, "Electronics", 68, "low"),
            Product(
                "P018",
                "Bluetooth Speaker Portable",
                79.99,
                "Electronics",
                110,
                "medium",
            ),
            Product(
                "P019", "Noise-Cancel Headphones", 249.99, "Electronics", 55, "low"
            ),
            Product("P020", "Tablet 10-inch", 329.99, "Electronics", 48, "low"),
            Product("P021", "Webcam 4K", 149.99, "Electronics", 72, "medium"),
            Product(
                "P022", "Mechanical Keyboard RGB", 99.99, "Electronics", 85, "medium"
            ),
            # HEALTH & BEAUTY - Medium-high price sensitivity
            Product(
                "P023",
                "Skincare Set Anti-Aging",
                89.99,
                "Health & Beauty",
                92,
                "medium",
            ),
            Product(
                "P024",
                "Hair Dryer Professional",
                129.99,
                "Health & Beauty",
                68,
                "medium",
            ),
            Product(
                "P025", "Electric Toothbrush", 79.99, "Health & Beauty", 105, "high"
            ),
            Product(
                "P026",
                "Massage Gun Deep Tissue",
                149.99,
                "Health & Beauty",
                75,
                "medium",
            ),
            Product(
                "P027", "Essential Oils Gift Set", 49.99, "Health & Beauty", 115, "high"
            ),
            # SPORTS & FITNESS - Medium price sensitivity
            Product(
                "P028",
                "Yoga Mat Premium Non-Slip",
                49.99,
                "Sports & Fitness",
                125,
                "high",
            ),
            Product(
                "P029", "Resistance Bands Set", 34.99, "Sports & Fitness", 140, "high"
            ),
            Product(
                "P030", "Dumbbell Set 20lb", 119.99, "Sports & Fitness", 62, "medium"
            ),
            Product(
                "P031", "Running Shoes Pro", 139.99, "Sports & Fitness", 88, "medium"
            ),
            Product("P032", "Gym Bag Large", 59.99, "Sports & Fitness", 95, "high"),
            # PREMIUM ELECTRONICS - Low price sensitivity (brand loyal)
            Product("P033", "Smart Home Hub Bundle", 279.99, "Electronics", 42, "low"),
            Product("P034", "Robot Vacuum Premium", 449.99, "Electronics", 35, "low"),
            Product(
                "P035", "4K Action Camera Waterproof", 349.99, "Electronics", 48, "low"
            ),
        ]

    def _initialize_promotions(self) -> List[Promotion]:
        """Initialize promotions with varied discounts based on price sensitivity"""
        now = datetime.utcnow()
        promotions = []

        # Discount strategies based on price tiers
        # Low-price items: higher discounts (30-70%) to drive volume
        # Mid-price items: moderate discounts (20-50%)
        # High-price items: conservative discounts (15-40%)
        # Premium items: minimal discounts (10-30%)

        discount_ranges = {
            "low": [30, 40, 50, 60, 70],  # $5-$25
            "mid": [20, 30, 40, 50],  # $25-$100
            "high": [15, 25, 30, 40],  # $100-$200
            "premium": [10, 15, 20, 25, 30],  # $200-$500
        }

        for i, product in enumerate(self.products):
            # Determine price tier and discount range
            if product.original_price < 25:
                tier = "low"
                # Higher base demand, more variance
                predicted = int(product.base_demand * random.uniform(0.35, 0.55))
            elif product.original_price < 100:
                tier = "mid"
                predicted = int(product.base_demand * random.uniform(0.40, 0.60))
            elif product.original_price < 200:
                tier = "high"
                predicted = int(product.base_demand * random.uniform(0.45, 0.65))
            else:
                tier = "premium"
                # Lower base demand, less variance
                predicted = int(product.base_demand * random.uniform(0.50, 0.70))

            discount = random.choice(discount_ranges[tier])
            promo_price = product.original_price * (1 - discount / 100)

            promo = Promotion(
                promo_id=f"PROMO{i + 1:03d}",
                product_id=product.product_id,
                product_name=product.product_name,
                original_price=product.original_price,
                promo_price=round(promo_price, 2),
                discount_percentage=discount,
                start_date=now,
                end_date=now + timedelta(days=7),
                predicted_sales=max(10, predicted),  # Ensure minimum of 10
            )
            promotions.append(promo)

        return promotions

    def _generate_shopper_id(self) -> str:
        shopper_id = f"SHOPPER{random.randint(1000, 9999)}"
        self.active_shoppers.add(shopper_id)
        return shopper_id

    def _should_cannibalize(self, promotion: Promotion) -> bool:
        """Determine cannibalization based on price sensitivity and discount depth
        High sensitivity + deep discount = higher cannibalization risk
        Low sensitivity + shallow discount = lower cannibalization risk
        """
        # Find product to get price sensitivity
        product = next(
            (p for p in self.products if p.product_id == promotion.product_id), None
        )
        if not product:
            return random.random() < 0.30  # Default fallback

        # Base cannibalization rates by price sensitivity
        sensitivity_rates = {
            "high": 0.50,  # Food, fitness items - very price elastic
            "medium": 0.35,  # Fashion, home goods - moderately elastic
            "low": 0.20,  # Electronics, premium goods - less elastic
        }

        base_rate = sensitivity_rates.get(product.price_sensitivity, 0.35)

        # Adjust based on discount depth (deeper discounts = more cannibalization)
        discount_multiplier = 1.0
        if promotion.discount_percentage > 40:
            discount_multiplier = 1.3  # Deep discount increases risk
        elif promotion.discount_percentage > 25:
            discount_multiplier = 1.15

        final_rate = min(0.65, base_rate * discount_multiplier)  # Cap at 65%
        return random.random() < final_rate

    def _generate_shopping_event(self, promotion: Promotion) -> ShoppingEvent:
        shopper_id = self._generate_shopper_id()
        is_cannibalized = self._should_cannibalize(promotion)

        quantity = random.randint(1, 3)
        # Refresh promo price/active from Redis cache if present
        try:
            promo_cache = self.redis_client.hgetall(f"promotion:{promotion.promo_id}")
            if promo_cache:
                if promo_cache.get("promo_price"):
                    promotion.promo_price = float(promo_cache["promo_price"])
                if (
                    promo_cache.get("is_active")
                    and promo_cache.get("is_active").lower() == "false"
                ):
                    raise ValueError("inactive")
        except ValueError:
            raise
        except Exception:
            pass

        price = promotion.promo_price

        event = ShoppingEvent(
            event_id=str(uuid.uuid4()),
            shopper_id=shopper_id,
            product_id=promotion.product_id,
            product_name=promotion.product_name,
            promo_id=promotion.promo_id,
            quantity=quantity,
            price=price,
            total_amount=round(price * quantity, 2),
            event_timestamp=datetime.utcnow().isoformat(),
            is_cannibalized=is_cannibalized,
        )

        return event

    async def _run_burst(self, burst_size: int):
        """Send a small burst of events across promos for demo mode."""
        logger.info(f"Starting demo burst with {burst_size} batches")
        for _ in range(burst_size):
            promotion = random.choice(self.promotions)
            events_count = random.randint(2, 4)
            for _ in range(events_count):
                try:
                    event = self._generate_shopping_event(promotion)
                except ValueError:
                    continue
                event_data = asdict(event)
                # Attach demo metadata if present on the simulator instance
                if hasattr(self, "current_burst_id"):
                    event_data["burst_id"] = self.current_burst_id
                if hasattr(self, "current_demo_queued_at"):
                    event_data["demo_queued_at"] = self.current_demo_queued_at
                self.producer.send("shopping-events", value=event_data)
                logger.info(
                    f"[Demo Burst] {event.shopper_id} bought {event.quantity}x {event.product_name} "
                    f"for ${event.total_amount} (Cannibalized: {event.is_cannibalized})"
                )
                await asyncio.sleep(random.uniform(0.1, 0.3))
        self.producer.flush()
        logger.info("Demo burst completed")

    async def simulate_shopping_activity(self):
        logger.info("Starting Virtual Shopper Simulator...")

        for promo in self.promotions:
            self.redis_client.hset(
                f"promotion:{promo.promo_id}",
                mapping={
                    "product_id": promo.product_id,
                    "product_name": promo.product_name,
                    "promo_price": promo.promo_price,
                    "predicted_sales": promo.predicted_sales,
                },
            )

        while True:
            if self.demo_mode:
                burst_request = self.redis_client.lpop("demo:burst")
                if burst_request:
                    burst_size = 5
                    burst_id = f"DEMO-{uuid.uuid4().hex[:10]}"
                    demo_queued_at = datetime.utcnow().isoformat()
                    try:
                        payload = json.loads(burst_request)
                        burst_size = max(
                            1, min(20, int(payload.get("burst_size", burst_size)))
                        )
                        burst_id = payload.get("burst_id", burst_id)
                        demo_queued_at = payload.get("queued_at", demo_queued_at)
                    except Exception:
                        try:
                            burst_size = max(1, min(20, int(burst_request)))
                        except Exception:
                            burst_size = 5
                    self.current_burst_id = burst_id
                    self.current_demo_queued_at = demo_queued_at
                    try:
                        await self._run_burst(burst_size)
                    finally:
                        if hasattr(self, "current_burst_id"):
                            del self.current_burst_id
                        if hasattr(self, "current_demo_queued_at"):
                            del self.current_demo_queued_at
                else:
                    await asyncio.sleep(2)
                continue

            # Check if simulation is enabled (cost control)
            if not self.simulation_enabled:
                logger.info("Simulation paused (SIMULATION_ENABLED=false)")
                await asyncio.sleep(30)  # Check every 30 seconds
                # Reload config from env (allows runtime toggling via Cloud Run env update)
                self.simulation_enabled = (
                    os.getenv("SIMULATION_ENABLED", "true").lower() == "true"
                )
                continue

            for promotion in self.promotions:
                # Use configurable event rate
                events_per_minute = random.randint(
                    max(1, self.event_rate - 5), self.event_rate + 5
                )
                # Occasionally create a dip to trigger cannibalization
                if random.random() < 0.3:
                    events_per_minute = random.randint(
                        1, max(2, events_per_minute // 3)
                    )

                for _ in range(events_per_minute):
                    try:
                        event = self._generate_shopping_event(promotion)
                    except ValueError:
                        continue

                    event_data = asdict(event)

                    self.producer.send("shopping-events", value=event_data)

                    logger.info(
                        f"Event: {event.shopper_id} bought {event.quantity}x {event.product_name} "
                        f"for ${event.total_amount} (Cannibalized: {event.is_cannibalized})"
                    )

                    await asyncio.sleep(random.uniform(0.5, 2.0))

            await asyncio.sleep(5)

    def run(self):
        # Start health check server in background thread
        health_thread = threading.Thread(target=run_health_check_server, daemon=True)
        health_thread.start()

        try:
            asyncio.run(self.simulate_shopping_activity())
        except KeyboardInterrupt:
            logger.info("Shutting down Virtual Shopper Simulator...")
            self.producer.close()
        except Exception as e:
            logger.error(f"Error in Virtual Shopper Simulator: {e}")
            raise


if __name__ == "__main__":
    simulator = VirtualShopperSimulator()
    simulator.run()
