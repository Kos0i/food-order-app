from flask import Flask, render_template, request, jsonify
import requests
import os
import logging
import time

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация API
API_URL = os.getenv('API_URL', 'http://api:8000')

def wait_for_api(timeout=60):
    """Ждем пока API станет доступным"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f'{API_URL}/api/health', timeout=5)
            if response.status_code == 200:
                logger.info("API is ready!")
                return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"Waiting for API... ({e})")
            time.sleep(5)
    logger.error("API did not become ready in time")
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/orders')
def orders():
    try:
        logger.info(f"Fetching orders from: {API_URL}/api/orders")
        response = requests.get(f'{API_URL}/api/orders', timeout=10)
        
        if response.status_code == 200:
            orders_data = response.json()
            logger.info(f"Successfully received {len(orders_data.get('data', []))} orders")
            
            orders_list = orders_data.get('data', [])
            if not isinstance(orders_list, list):
                orders_list = []
                
            return render_template('orders.html', orders=orders_list)
        else:
            logger.error(f"API returned status: {response.status_code}")
            return render_template('orders.html', orders=[])
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to API: {e}")
        return render_template('orders.html', orders=[], error="Cannot connect to API service")
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout connecting to API: {e}")
        return render_template('orders.html', orders=[], error="API timeout")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return render_template('orders.html', orders=[], error=str(e))

@app.route('/create-order', methods=['POST'])
def create_order():
    try:
        order_data = {
            'customer_name': request.form['customer_name'],
            'items': [item.strip() for item in request.form['items'].split(',')],
            'total': float(request.form['total'])
        }
        
        logger.info(f"Creating order: {order_data}")
        response = requests.post(f'{API_URL}/api/orders', json=order_data, timeout=10)
        
        if response.status_code == 201:
            return '''
            <script>
                alert('Order created successfully!');
                window.location.href = '/orders';
            </script>
            '''
        else:
            logger.error(f"Failed to create order: {response.status_code}")
            return '''
            <script>
                alert('Error creating order!');
                window.location.href = '/';
            </script>
            '''
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Cannot connect to API: {e}")
        return '''
        <script>
            alert('Cannot connect to server. Please try again.');
            window.location.href = '/';
        </script>
        '''
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return f"Error: {e}", 500

@app.route('/api/health')
def api_health():
    """Health check для frontend"""
    try:
        # Пробуем подключиться к API
        api_response = requests.get(f'{API_URL}/api/health', timeout=5)
        api_status = api_response.json() if api_response.status_code == 200 else {'status': 'unreachable'}
        
        return jsonify({
            'frontend': 'healthy',
            'api': api_status,
            'api_url': API_URL,
            'api_accessible': api_response.status_code == 200
        })
    except requests.exceptions.ConnectionError:
        return jsonify({
            'frontend': 'healthy',
            'api': {'status': 'unreachable', 'error': 'Connection failed'},
            'api_url': API_URL,
            'api_accessible': False
        }), 503
    except Exception as e:
        return jsonify({
            'frontend': 'healthy', 
            'api': {'status': 'error', 'error': str(e)},
            'api_url': API_URL,
            'api_accessible': False
        }), 500

@app.route('/health')
def health():
    """Простой health check"""
    return jsonify({'status': 'healthy', 'service': 'frontend'})

if __name__ == '__main__':
    # Ждем API перед запуском
    wait_for_api()
    app.run(host='0.0.0.0', port=5000, debug=True)