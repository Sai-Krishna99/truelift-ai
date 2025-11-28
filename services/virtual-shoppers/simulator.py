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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Product:
    product_id: str
    product_name: str
    original_price: float
    category: str
    base_demand: int


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
        self.kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9094')
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        self.redis_client = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            decode_responses=True
        )
        
        self.products = self._initialize_products()
        self.promotions = self._initialize_promotions()
        self.active_shoppers = set()

    def _initialize_products(self) -> List[Product]:
        return [
            Product("P001", "Premium Coffee Beans", 25.99, "Beverages", 100),
            Product("P002", "Organic Protein Powder", 49.99, "Health", 80),
            Product("P003", "Smart Watch Series X", 299.99, "Electronics", 50),
            Product("P004", "Designer Sunglasses", 149.99, "Fashion", 60),
            Product("P005", "Wireless Earbuds Pro", 179.99, "Electronics", 90),
            Product("P006", "Yoga Mat Premium", 39.99, "Fitness", 70),
            Product("P007", "Ceramic Cookware Set", 199.99, "Home", 40),
            Product("P008", "Running Shoes Elite", 129.99, "Sports", 85),
        ]

    def _initialize_promotions(self) -> List[Promotion]:
        now = datetime.utcnow()
        promotions = []
        
        for i, product in enumerate(self.products[:4]):
            discount = random.choice([20, 30, 40, 50])
            promo_price = product.original_price * (1 - discount / 100)
            predicted_sales = int(product.base_demand * (1 + discount / 20))
            
            promo = Promotion(
                promo_id=f"PROMO{i+1:03d}",
                product_id=product.product_id,
                product_name=product.product_name,
                original_price=product.original_price,
                promo_price=round(promo_price, 2),
                discount_percentage=discount,
                start_date=now,
                end_date=now + timedelta(days=7),
                predicted_sales=predicted_sales
            )
            promotions.append(promo)
            
        return promotions

    def _generate_shopper_id(self) -> str:
        shopper_id = f"SHOPPER{random.randint(1000, 9999)}"
        self.active_shoppers.add(shopper_id)
        return shopper_id

    def _should_cannibalize(self, promotion: Promotion) -> bool:
        return random.random() < 0.35

    def _generate_shopping_event(self, promotion: Promotion) -> ShoppingEvent:
        shopper_id = self._generate_shopper_id()
        is_cannibalized = self._should_cannibalize(promotion)
        
        quantity = random.randint(1, 3)
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
            is_cannibalized=is_cannibalized
        )
        
        return event

    async def simulate_shopping_activity(self):
        logger.info("Starting Virtual Shopper Simulator...")
        
        for promo in self.promotions:
            self.redis_client.hset(
                f"promotion:{promo.promo_id}",
                mapping={
                    'product_id': promo.product_id,
                    'product_name': promo.product_name,
                    'promo_price': promo.promo_price,
                    'predicted_sales': promo.predicted_sales
                }
            )
        
        while True:
            for promotion in self.promotions:
                events_per_minute = random.randint(8, 15)
                
                for _ in range(events_per_minute):
                    event = self._generate_shopping_event(promotion)
                    
                    event_data = asdict(event)
                    
                    self.producer.send('shopping-events', value=event_data)
                    
                    logger.info(f"Event: {event.shopper_id} bought {event.quantity}x {event.product_name} "
                              f"for ${event.total_amount} (Cannibalized: {event.is_cannibalized})")
                    
                    await asyncio.sleep(random.uniform(0.5, 2.0))
            
            await asyncio.sleep(5)

    def run(self):
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
