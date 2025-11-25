import time
import psycopg2
import redis
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DATABASE_HOST', 'database'),
    'database': os.getenv('DATABASE_NAME', 'food_orders'),
    'user': os.getenv('DATABASE_USER', 'user'),
    'password': os.getenv('DATABASE_PASSWORD', 'password'),
    'port': 5432
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_redis_connection():
    return redis.Redis(
        host=os.getenv('REDIS_HOST', 'cache'),
        port=6379,
        decode_responses=True,
        socket_connect_timeout=5
    )

def wait_for_services():
    """Ожидание готовности сервисов"""
    max_retries = 30
    for i in range(max_retries):
        try:
            # Проверяем базу данных
            conn = get_db_connection()
            conn.close()
            
            # Проверяем Redis
            redis_conn = get_redis_connection()
            redis_conn.ping()
            
            logger.info("All services are ready!")
            return True
        except Exception as e:
            logger.warning(f"Services not ready (attempt {i+1}/{max_retries}): {e}")
            if i < max_retries - 1:
                time.sleep(5)
    
    logger.error("Failed to connect to services after multiple attempts")
    return False

def process_orders():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Process pending orders
        cur.execute("SELECT id FROM orders WHERE status = 'pending' LIMIT 5;")
        pending_orders = cur.fetchall()
        
        for order_tuple in pending_orders:
            order_id = order_tuple[0]
            logger.info(f"Processing order {order_id}")
            
            # Simulate order processing
            time.sleep(2)
            
            # Update order status to preparing
            cur.execute("UPDATE orders SET status = 'preparing' WHERE id = %s;", (order_id,))
            conn.commit()
            
            logger.info(f"Order {order_id} moved to preparing")
            
            # Simulate cooking time
            time.sleep(3)
            
            # Update order status to completed
            cur.execute("UPDATE orders SET status = 'completed' WHERE id = %s;", (order_id,))
            conn.commit()
            
            # Invalidate cache
            try:
                redis_client = get_redis_connection()
                redis_client.delete('all_orders')
            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {e}")
            
            logger.info(f"Order {order_id} completed")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error processing orders: {e}")

if __name__ == '__main__':
    logger.info("Background worker starting...")
    
    # Ждем готовности сервисов
    if wait_for_services():
        logger.info("Worker started successfully")
        while True:
            process_orders()
            time.sleep(10)  # Check for new orders every 10 seconds
    else:
        logger.error("Worker failed to start due to service unavailability")
        exit(1)