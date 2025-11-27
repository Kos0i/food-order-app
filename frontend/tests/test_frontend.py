import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_page(client):
    """Test main page loads"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Food Order System' in response.data

def test_orders_page(client):
    """Test orders page loads"""
    response = client.get('/orders')
    assert response.status_code == 200

def test_health_check(client):
    """Test frontend health check"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'

def test_api_health_endpoint(client):
    """Test API health check through frontend"""
    response = client.get('/api/health')
    # Should work or handle API unavailability gracefully
    assert response.status_code in [200, 503]