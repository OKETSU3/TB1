import pytest
import os
import tempfile
import pandas as pd
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta

@pytest.fixture(scope="session")
def test_api_key():
    """Provide test API key for all tests"""
    return "test_api_key_12345"

@pytest.fixture(scope="function")
def mock_env_with_api_key(test_api_key, monkeypatch):
    """Set up environment with API key for tests"""
    monkeypatch.setenv("TWELVE_DATA_API_KEY", test_api_key)
    monkeypatch.setenv("TESTING", "true")
    yield test_api_key

@pytest.fixture(scope="function")
def mock_env_no_api_key(monkeypatch):
    """Set up environment without API key for error testing"""
    monkeypatch.delenv("TWELVE_DATA_API_KEY", raising=False)
    yield

@pytest.fixture(scope="function")
def sample_ohlcv_data():
    """Provide sample OHLCV data for testing"""
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    return pd.DataFrame({
        'open': [150.0, 151.0, 152.0, 153.0, 154.0],
        'high': [155.0, 156.0, 157.0, 158.0, 159.0],
        'low': [149.0, 150.0, 151.0, 152.0, 153.0],
        'close': [154.0, 155.0, 156.0, 157.0, 158.0],
        'volume': [1000000, 1100000, 1200000, 1300000, 1400000]
    }, index=dates)

@pytest.fixture(scope="function")
def mock_config_manager():
    """Provide mock configuration manager"""
    config = Mock()
    config.get.return_value = {
        'api': {
            'timeout': 30,
            'retry_count': 3,
            'daily_limit': 800
        },
        'cache': {
            'freshness_hours': 24,
            'max_size_mb': 100
        }
    }
    return config

@pytest.fixture(scope="function")
def mock_rate_limiter():
    """Provide mock rate limiter"""
    limiter = Mock()
    limiter.can_make_request.return_value = True
    limiter.record_request.return_value = None
    limiter.get_usage.return_value = {'used': 0, 'limit': 800}
    return limiter

@pytest.fixture(scope="function")
def mock_cache():
    """Provide mock cache implementation"""
    cache = Mock()
    cache.get.return_value = None  # Default: no cached data
    cache.store.return_value = True
    cache.is_fresh.return_value = False
    return cache

@pytest.fixture(scope="function")
def temp_database():
    """Provide temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        yield tmp.name
    os.unlink(tmp.name)