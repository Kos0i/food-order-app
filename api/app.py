from flask import Flask, jsonify, request
import psycopg2
import redis
import json
import os
import logging
import time
from datetime import datetime

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DATABASE_HOST', 'database'),
    'database': os.getenv('DATABASE_NAME', 'food_orders'),
    'user': os.getenv('DATABASE_USER', 'user'),
    'password': os.getenv('DATABASE_PASSWORD', 'password'),
    'port': 5432
}

def wait_for_database(max_retries=30, retry_interval=5):
    """Ожидание готовности базы данных"""
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.close()
            logger.info("Database is ready!")
            return True
        except Exception as e:
            logger.warning(f"Database not ready (attempt {i+1}/{max_retries}): {e}")
            if i < max_retries - 1:
                time.sleep(retry_interval)
    return False

def wait_for_redis(max_retries=30, retry_interval=5):
    """Ожидание готовности Redis"""
    for i in range(max_retries):
        try:
            r = redis.Redis(
                host=os.getenv('REDIS_HOST', 'cache'),
                port=6379,
                decode_responses=True,
                socket_connect_timeout=5
            )
            r.ping()
            logger.info("Redis is ready!")
            return True
        except Exception as e:
            logger.warning(f"Redis not ready (attempt {i+1}/{max_retries}): {e}")
            if i < max_retries - 1:
                time.sleep(retry_interval)
    return False

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_redis_connection():
    return redis.Redis(
        host=os.getenv('REDIS_HOST', 'cache'),
        port=6379,
        decode_responses=True,
        socket_connect_timeout=5
    )

# Инициализация при старте
def initialize_services():
    logger.info("Initializing services...")
    
    if not wait_for_database():
        logger.error("Failed to connect to database after multiple attempts")
        return False
        
    if not wait_for_redis():
        logger.error("Failed to connect to Redis after multiple attempts")
        return False
        
    logger.info("All services are ready!")
    return True

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        # Проверяем подключение к БД
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1;')
        cur.close()
        conn.close()
        
        # Проверяем подключение к Redis
        redis_client = get_redis_connection()
        redis_client.ping()
        
        return jsonify({
            'status': 'healthy', 
            'service': 'api',
            'database': 'connected',
            'redis': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'api', 
            'error': str(e)
        }), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        redis_client = get_redis_connection()
        
        # Try cache first
        cached_orders = redis_client.get('all_orders')
        if cached_orders:
            logger.info("Returning orders from cache")
            orders_data = json.loads(cached_orders)
            return jsonify({
                'source': 'cache', 
                'data': orders_data,
                'count': len(orders_data)
            })
        
        # Database query
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, customer_name, items, total, status, created_at FROM orders ORDER BY created_at DESC;')
        orders = cur.fetchall()
        cur.close()
        conn.close()
        
        # Format response
        orders_list = []
        for order in orders:
            try:
                items = order[2]
                if isinstance(items, str):
                    items = json.loads(items)
                
                orders_list.append({
                    'id': order[0],
                    'customer_name': order[1],
                    'items': items,
                    'total': float(order[3]),
                    'status': order[4],
                    'created_at': order[5].isoformat() if order[5] else None
                })
            except Exception as e:
                logger.error(f"Error formatting order {order[0]}: {e}")
                continue
        
        # Cache for 30 seconds
        try:
            redis_client.setex('all_orders', 30, json.dumps(orders_list))
        except Exception as e:
            logger.warning(f"Failed to cache orders: {e}")
            
        logger.info(f"Returning {len(orders_list)} orders from database")
        
        return jsonify({
            'source': 'database', 
            'data': orders_list,
            'count': len(orders_list)
        })
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return jsonify({'error': str(e), 'data': []}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            'INSERT INTO orders (customer_name, items, total, status) VALUES (%s, %s, %s, %s) RETURNING id;',
            (data.get('customer_name'), json.dumps(data.get('items', [])), data.get('total'), 'pending')
        )
        
        order_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        # Invalidate cache
        try:
            redis_client = get_redis_connection()
            redis_client.delete('all_orders')
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")
        
        return jsonify({'message': 'Order created', 'order_id': order_id}), 201
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order_status(order_id):
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
            
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            'UPDATE orders SET status = %s WHERE id = %s;',
            (data['status'], order_id)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Invalidate cache
        try:
            redis_client = get_redis_connection()
            redis_client.delete('all_orders')
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")
        
        return jsonify({'message': 'Order updated'})
    except Exception as e:
        logger.error(f"Error updating order: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Ждем готовности сервисов перед запуском
    if initialize_services():
        logger.info("Starting Flask application...")
        app.run(host='0.0.0.0', port=8000, debug=False)
    else:
        logger.error("Failed to initialize services. Exiting.")
        exit(1)