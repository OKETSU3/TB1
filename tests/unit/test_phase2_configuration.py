import pytest
import yaml
import tempfile
from unittest.mock import patch
import os
import time
from freezegun import freeze_time


class TestConfigurationManagement:
    """T2.1 Configuration Management Testing"""
    
    @pytest.fixture
    def sample_config(self):
        return {
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
    
    def test_t2_1_config_file_loading_success(self, sample_config, tmp_path):
        """Test successful configuration file loading"""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config, f)
        
        from tradebot.config.manager import ConfigManager
        config_manager = ConfigManager(config_path=str(config_file))
        loaded_config = config_manager.get_config()
        
        assert loaded_config['api']['timeout'] == 30
        assert loaded_config['api']['daily_limit'] == 800
        assert loaded_config['cache']['freshness_hours'] == 24
    
    def test_t2_1_environment_variable_override(self, sample_config, tmp_path, monkeypatch):
        """Test environment variable override of config values"""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config, f)
        
        # Set environment override
        monkeypatch.setenv("TWELVE_DATA_TIMEOUT", "60")
        
        from tradebot.config.manager import ConfigManager
        config_manager = ConfigManager(config_path=str(config_file))
        loaded_config = config_manager.get_config()
        
        # Environment variable should override config file
        assert loaded_config['api']['timeout'] == 60
        # Other values should remain from config file
        assert loaded_config['api']['retry_count'] == 3
    
    def test_t2_1_config_validation_missing_file(self):
        """Test error handling when config file is missing"""
        from tradebot.config.manager import ConfigManager
        from tradebot.exceptions import ConfigurationError
        
        with pytest.raises(ConfigurationError) as exc_info:
            ConfigManager(config_path="nonexistent_config.yaml")
        
        assert "Configuration file not found" in str(exc_info.value)
    
    def test_t2_1_invalid_yaml_format(self, tmp_path):
        """Test error handling for invalid YAML format"""
        config_file = tmp_path / "invalid_config.yaml"
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        from tradebot.config.manager import ConfigManager
        from tradebot.exceptions import ConfigurationError
        
        with pytest.raises(ConfigurationError) as exc_info:
            ConfigManager(config_path=str(config_file))
        
        assert "Invalid YAML format" in str(exc_info.value)
    
    def test_t2_1_default_config_values(self, tmp_path):
        """Test default configuration values when file is minimal"""
        minimal_config = {'api': {'daily_limit': 800}}
        config_file = tmp_path / "minimal_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(minimal_config, f)
        
        from tradebot.config.manager import ConfigManager
        config_manager = ConfigManager(config_path=str(config_file))
        loaded_config = config_manager.get_config()
        
        # Should have default values for missing keys
        assert loaded_config['api']['timeout'] == 30  # default value
        assert loaded_config['api']['retry_count'] == 3  # default value
        assert loaded_config['api']['daily_limit'] == 800  # from file


class TestLoggingSystem:
    """T2.2 Logging System Validation"""
    
    def test_t2_2_structured_log_creation(self):
        """Test creation of structured log messages"""
        with patch('tradebot.utils.logger.logging') as mock_logging:
            from tradebot.utils.logger import APIUsageLogger
            logger = APIUsageLogger()
            logger.log_operation("fetch_data", "AAPL", {"requests_used": 1})
            
            # Verify logging was called with structured data
            mock_logging.getLogger.return_value.info.assert_called()
    
    def test_t2_2_api_usage_tracking(self):
        """Test API usage tracking in log messages"""
        with patch('tradebot.utils.logger.logging') as mock_logging:
            from tradebot.utils.logger import APIUsageLogger
            logger = APIUsageLogger()
            logger.log_api_usage("AAPL", "fetch", 1, 800)
            
            # Verify usage tracking was logged
            mock_logging.getLogger.return_value.info.assert_called()
    
    def test_t2_2_log_level_configuration(self):
        """Test log level configuration"""
        with patch('tradebot.utils.logger.logging') as mock_logging:
            from tradebot.utils.logger import APIUsageLogger
            logger = APIUsageLogger(level="DEBUG")
            
            # Verify logger was configured with correct level
            mock_logging.getLogger.return_value.setLevel.assert_called()
    
    def test_t2_2_performance_metrics_logging(self):
        """Test performance metrics logging"""
        with patch('tradebot.utils.logger.logging') as mock_logging:
            from tradebot.utils.logger import APIUsageLogger
            logger = APIUsageLogger()
            
            metrics = {
                "fetch_time_ms": 250,
                "data_size_kb": 45,
                "cache_hit": False
            }
            logger.log_performance_metrics("AAPL", metrics)
            
            # Verify performance logging was called
            mock_logging.getLogger.return_value.info.assert_called()
    
    def test_t2_2_quota_tracking_accuracy(self):
        """Test quota usage tracking accuracy"""
        with patch('tradebot.utils.logger.logging') as mock_logging:
            from tradebot.utils.logger import APIUsageLogger
            logger = APIUsageLogger()
            
            # Reset call count after initialization
            mock_logging.getLogger.return_value.info.reset_mock()
            
            # Test quota tracking for multiple operations
            logger.log_api_usage("AAPL", "fetch", 1, 800)
            logger.log_api_usage("MSFT", "fetch", 1, 800)
            
            # Should have logged twice (API usage calls only)
            assert mock_logging.getLogger.return_value.info.call_count == 2


class TestRateLimiting:
    """T2.3 Rate Limiting Verification (CRITICAL)"""
    
    def test_t2_3_daily_quota_enforcement(self, tmp_path):
        """CRITICAL: Test daily API quota enforcement"""
        # Use temporary storage for testing
        storage_path = tmp_path / "test_quota.db"
        
        from tradebot.utils.rate_limiter import RateLimiter
        rate_limiter = RateLimiter(daily_limit=3, storage_path=str(storage_path))
        
        # Test requests within limit
        assert rate_limiter.can_make_request() == True
        rate_limiter.record_request()
        
        assert rate_limiter.can_make_request() == True  
        rate_limiter.record_request()
        
        assert rate_limiter.can_make_request() == True
        rate_limiter.record_request()
        
        # Test quota exceeded
        assert rate_limiter.can_make_request() == False
        
        from tradebot.exceptions import QuotaExceededError
        with pytest.raises(QuotaExceededError):
            rate_limiter.acquire()
    
    @freeze_time("2024-01-01 23:59:59")
    def test_t2_3_quota_reset_functionality(self, tmp_path):
        """Test quota resets correctly at daily boundaries"""
        storage_path = tmp_path / "test_quota.db"
        
        from tradebot.utils.rate_limiter import RateLimiter
        rate_limiter = RateLimiter(daily_limit=5, storage_path=str(storage_path))
        
        # Use up quota
        for i in range(5):
            rate_limiter.record_request()
        
        assert rate_limiter.get_usage()['used'] == 5
        assert rate_limiter.can_make_request() == False
        
        # Advance to next day
        with freeze_time("2024-01-02 00:00:01"):
            assert rate_limiter.get_usage()['used'] == 0
            assert rate_limiter.can_make_request() == True
    
    def test_t2_3_request_spacing(self, tmp_path):
        """Test minimum spacing between requests"""
        storage_path = tmp_path / "test_quota.db"
        from tradebot.utils.rate_limiter import RateLimiter
        rate_limiter = RateLimiter(daily_limit=100, min_interval=0.05, storage_path=str(storage_path))  # Very short interval for testing
        
        start_time = time.time()
        rate_limiter.acquire()
        rate_limiter.acquire()  # Should be delayed
        end_time = time.time()
        
        elapsed = end_time - start_time
        assert elapsed >= 0.05, f"Request spacing was {elapsed}s, expected >= 0.05s"
    
    def test_t2_3_persistent_quota_storage(self, tmp_path):
        """Test quota storage persists across RateLimiter instances"""
        storage_path = tmp_path / "test_quota.db"
        
        from tradebot.utils.rate_limiter import RateLimiter
        
        # First instance - use some quota
        limiter1 = RateLimiter(daily_limit=10, storage_path=str(storage_path))
        limiter1.record_request()
        limiter1.record_request()
        limiter1.record_request()
        
        # Second instance - should remember previous usage
        limiter2 = RateLimiter(daily_limit=10, storage_path=str(storage_path))
        usage = limiter2.get_usage()
        
        assert usage['used'] == 3
    
    def test_t2_3_quota_exceeded_error_details(self, tmp_path):
        """Test QuotaExceededError contains useful information"""
        storage_path = tmp_path / "test_quota.db"
        
        from tradebot.utils.rate_limiter import RateLimiter
        from tradebot.exceptions import QuotaExceededError
        
        rate_limiter = RateLimiter(daily_limit=2, storage_path=str(storage_path))
        
        # Use up quota
        rate_limiter.record_request()
        rate_limiter.record_request()
        
        # Try to exceed quota
        with pytest.raises(QuotaExceededError) as exc_info:
            rate_limiter.acquire()
        
        error_msg = str(exc_info.value)
        assert "quota" in error_msg.lower() or "limit" in error_msg.lower()


class TestDatabaseSchema:
    """T2.4 Database Schema Testing (Peewee Model Validation)"""
    
    @pytest.fixture
    def test_db(self):
        """Create temporary test database"""
        from peewee import SqliteDatabase
        from tradebot.data.models import StockData, CacheMetadata
        
        db = SqliteDatabase(':memory:')
        StockData._meta.database = db
        CacheMetadata._meta.database = db
        db.create_tables([StockData, CacheMetadata])
        return db
    
    def test_t2_4_stock_data_model_creation(self, test_db):
        """Test StockData model creation and basic operations"""
        from tradebot.data.models import StockData
        
        # Create test record
        stock_record = StockData.create(
            symbol='AAPL',
            date='2024-01-01',
            open_price=150.0,
            high_price=155.0,
            low_price=149.0,
            close_price=154.0,
            volume=1000000
        )
        
        # Verify record was created
        assert stock_record.symbol == 'AAPL'
        assert stock_record.open_price == 150.0
        
        # Test retrieval
        retrieved = StockData.get(StockData.symbol == 'AAPL')
        assert retrieved.close_price == 154.0
    
    def test_t2_4_cache_metadata_model(self, test_db):
        """Test CacheMetadata model functionality"""
        from tradebot.data.models import CacheMetadata
        
        # Create test metadata record
        metadata = CacheMetadata.create(
            cache_key='AAPL_2024-01-01_2024-01-03',
            symbol='AAPL',
            start_date='2024-01-01',
            end_date='2024-01-03',
            record_count=3,
            data_size_bytes=1024
        )
        
        # Verify metadata record
        assert metadata.symbol == 'AAPL'
        assert metadata.record_count == 3
        assert metadata.data_size_bytes == 1024
        
        # Test retrieval by symbol
        retrieved = CacheMetadata.get(CacheMetadata.symbol == 'AAPL')
        assert retrieved.cache_key == 'AAPL_2024-01-01_2024-01-03'
    
    def test_t2_4_data_type_constraints(self, test_db):
        """Test data type constraints and validation"""
        from tradebot.data.models import StockData
        
        # Test with valid data
        valid_record = StockData.create(
            symbol='MSFT',
            date='2024-01-02',
            open_price=200.50,
            high_price=205.75,
            low_price=199.25,
            close_price=203.80,
            volume=2500000
        )
        
        assert valid_record.open_price == 200.50
        assert valid_record.volume == 2500000
    
    def test_t2_4_unique_constraints(self, test_db):
        """Test unique constraints on symbol+date combination"""
        from tradebot.data.models import StockData
        from peewee import IntegrityError
        
        # Create first record
        StockData.create(
            symbol='GOOGL',
            date='2024-01-01',
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=103.0,
            volume=1000000
        )
        
        # Try to create duplicate (should fail)
        with pytest.raises(IntegrityError):
            StockData.create(
                symbol='GOOGL',
                date='2024-01-01',  # Same symbol+date
                open_price=101.0,
                high_price=106.0,
                low_price=100.0,
                close_price=104.0,
                volume=1100000
            )
    
    def test_t2_4_database_indexing(self, test_db):
        """Test database indexes for query performance"""
        from tradebot.data.models import StockData
        
        # Create multiple records for different symbols and dates
        test_data = [
            ('AAPL', '2024-01-01', 150.0),
            ('AAPL', '2024-01-02', 151.0),
            ('MSFT', '2024-01-01', 300.0),
            ('MSFT', '2024-01-02', 301.0),
        ]
        
        for symbol, date, price in test_data:
            StockData.create(
                symbol=symbol,
                date=date,
                open_price=price,
                high_price=price + 5,
                low_price=price - 1,
                close_price=price + 2,
                volume=1000000
            )
        
        # Test queries that should use indexes
        aapl_records = list(StockData.select().where(StockData.symbol == 'AAPL'))
        assert len(aapl_records) == 2
        
        date_records = list(StockData.select().where(StockData.date == '2024-01-01'))
        assert len(date_records) == 2


class TestCachingFunctionality:
    """T2.5 Caching Functionality Validation (Storage and Retrieval Testing)"""
    
    @pytest.fixture
    def test_cache(self, tmp_path):
        """Create test cache with temporary database"""
        cache_db = tmp_path / "test_cache.db"
        from tradebot.data.cache import DataCache
        return DataCache(database_path=str(cache_db))
    
    @pytest.fixture
    def sample_data(self):
        """Sample OHLCV data for caching tests"""
        import pandas as pd
        dates = pd.date_range('2024-01-01', periods=2, freq='D')
        return pd.DataFrame({
            'open': [150.0, 151.0],
            'high': [155.0, 156.0],
            'low': [149.0, 150.0],
            'close': [154.0, 155.0],
            'volume': [1000000, 1100000]
        }, index=dates)
    
    def test_t2_5_cache_storage_and_retrieval(self, test_cache, sample_data):
        """Test cache storage and retrieval functionality"""
        # Store data in cache
        test_cache.store("AAPL", "2024-01-01", "2024-01-02", sample_data)
        
        # Retrieve data from cache
        cached_data = test_cache.get("AAPL", "2024-01-01", "2024-01-02")
        
        assert cached_data is not None
        assert len(cached_data) == 2
        assert cached_data['open'].iloc[0] == 150.0
        assert cached_data['close'].iloc[1] == 155.0
    
    def test_t2_5_cache_miss_scenario(self, test_cache):
        """Test cache miss when data not present"""
        cached_data = test_cache.get("MSFT", "2024-01-01", "2024-01-02")
        assert cached_data is None
    
    def test_t2_5_cache_freshness_checking(self, test_cache, sample_data):
        """Test cache freshness validation"""
        # Store data
        test_cache.store("AAPL", "2024-01-01", "2024-01-02", sample_data)
        
        # Check if data is fresh (should be fresh immediately after storage)
        is_fresh = test_cache.is_fresh("AAPL", "2024-01-01", "2024-01-02", hours=24)
        assert is_fresh == True
    
    def test_t2_5_cache_hit_miss_tracking(self, test_cache, sample_data):
        """Test cache hit/miss tracking functionality"""
        # Use unique symbol to avoid test interference
        symbol = "UNIQUE"
        
        # First access should be a miss
        cached_data = test_cache.get(symbol, "2024-01-01", "2024-01-02")
        assert cached_data is None
        
        # Store data
        test_cache.store(symbol, "2024-01-01", "2024-01-02", sample_data)
        
        # Second access should be a hit
        cached_data = test_cache.get(symbol, "2024-01-01", "2024-01-02")
        assert cached_data is not None
        assert len(cached_data) == 2
    
    def test_t2_5_cache_metadata_tracking(self, test_cache, sample_data):
        """Test cache metadata creation and tracking"""
        # Store data with metadata tracking
        test_cache.store("AAPL", "2024-01-01", "2024-01-02", sample_data)
        
        # Verify metadata was created
        metadata = test_cache.get_metadata("AAPL", "2024-01-01", "2024-01-02")
        assert metadata is not None
        assert metadata['symbol'] == "AAPL"
        assert metadata['record_count'] == 2
        assert metadata['data_size_bytes'] > 0