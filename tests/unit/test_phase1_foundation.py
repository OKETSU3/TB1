import pytest
import os
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

class TestProjectStructure:
    """T1.1 Project Structure Verification Test"""
    
    def test_t1_1_directory_structure_exists(self):
        """Verify all required directories are created"""
        required_dirs = [
            "tradebot",
            "tradebot/data", 
            "tradebot/config",
            "tradebot/utils"
        ]
        for dir_path in required_dirs:
            assert os.path.exists(dir_path), f"Directory {dir_path} does not exist"
            
    def test_t1_1_init_files_present(self):
        """Verify __init__.py files exist for package structure"""
        required_init_files = [
            "tradebot/__init__.py",
            "tradebot/data/__init__.py",
            "tradebot/config/__init__.py", 
            "tradebot/utils/__init__.py"
        ]
        for init_file in required_init_files:
            assert os.path.exists(init_file), f"__init__.py missing: {init_file}"
    
    def test_t1_1_package_imports_work(self):
        """Verify Python package imports function correctly"""
        try:
            import tradebot
            import tradebot.data
            import tradebot.config
            import tradebot.utils
        except ImportError as e:
            pytest.fail(f"Package import failed: {e}")


class TestDataFetcher:
    """T1.2 Core Data Fetcher Testing"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Setup mock dependencies for DataFetcher"""
        return {
            'config_manager': Mock(),
            'rate_limiter': Mock(),
            'cache': Mock()
        }
    
    @pytest.fixture 
    def sample_ohlcv_data(self):
        """Provide sample OHLCV data for testing"""
        dates = pd.date_range('2024-01-01', periods=3, freq='D')
        return pd.DataFrame({
            'open': [150.0, 151.0, 152.0],
            'high': [155.0, 156.0, 157.0], 
            'low': [149.0, 150.0, 151.0],
            'close': [154.0, 155.0, 156.0],
            'volume': [1000000, 1100000, 1200000]
        }, index=dates)
    
    def test_t1_2_datafetcher_initialization_success(self, mock_dependencies, monkeypatch):
        """Test successful DataFetcher initialization with API key"""
        monkeypatch.setenv("TWELVE_DATA_API_KEY", "test_api_key")
        
        from tradebot.data.fetcher import DataFetcher
        fetcher = DataFetcher(**mock_dependencies)
        
        assert fetcher.api_key == "test_api_key"
        assert fetcher.config == mock_dependencies['config_manager']
        assert fetcher.rate_limiter == mock_dependencies['rate_limiter']
        assert fetcher.cache == mock_dependencies['cache']
    
    def test_t1_2_api_key_missing_error(self, mock_dependencies, monkeypatch):
        """Test error handling when API key is missing"""
        monkeypatch.delenv("TWELVE_DATA_API_KEY", raising=False)
        
        from tradebot.data.fetcher import DataFetcher
        with pytest.raises(ValueError) as exc_info:
            DataFetcher(**mock_dependencies)
        
        assert "TWELVE_DATA_API_KEY" in str(exc_info.value)
        assert "environment variable not set" in str(exc_info.value)
    
    @patch('tradebot.data.fetcher.TDClient')
    def test_t1_2_fetch_historical_data_success(self, mock_td_client, mock_dependencies, 
                                               sample_ohlcv_data, monkeypatch):
        """Test successful data fetching with mocked API"""
        monkeypatch.setenv("TWELVE_DATA_API_KEY", "test_api_key")
        
        # Setup mock TDClient
        mock_client_instance = Mock()
        mock_td_client.return_value = mock_client_instance
        mock_time_series = Mock()
        mock_time_series.as_pandas.return_value = sample_ohlcv_data
        mock_client_instance.time_series.return_value = mock_time_series
        
        # Setup cache to return None (no cached data)
        mock_dependencies['cache'].get.return_value = None
        mock_dependencies['rate_limiter'].can_make_request.return_value = True
        
        from tradebot.data.fetcher import DataFetcher
        fetcher = DataFetcher(**mock_dependencies)
        result = fetcher.fetch_historical_data("AAPL", "2024-01-01", "2024-01-03")
        
        # Verify result format
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert len(result) == 3
        assert result['open'].dtype in [float, 'float64']
        assert result['volume'].dtype in [int, 'int64']
        
        # Verify API was called correctly
        mock_td_client.assert_called_once_with(apikey="test_api_key")
        mock_client_instance.time_series.assert_called_once_with(
            symbol="AAPL",
            interval="1day", 
            start_date="2024-01-01",
            end_date="2024-01-03",
            outputsize=5000
        )


class TestErrorHandling:
    """T1.3 Error Handling Validation"""
    
    @pytest.fixture
    def setup_fetcher(self, monkeypatch):
        """Setup DataFetcher with mocked dependencies"""
        monkeypatch.setenv("TWELVE_DATA_API_KEY", "test_api_key")
        mock_deps = {
            'config_manager': Mock(),
            'rate_limiter': Mock(),
            'cache': Mock()
        }
        mock_deps['cache'].get.return_value = None
        mock_deps['rate_limiter'].can_make_request.return_value = True
        
        from tradebot.data.fetcher import DataFetcher
        return DataFetcher(**mock_deps)
    
    @patch('tradebot.data.fetcher.TDClient')
    def test_t1_3_network_failure_handling(self, mock_td_client, setup_fetcher):
        """Test graceful handling of network connectivity issues"""
        mock_client_instance = Mock()
        mock_td_client.return_value = mock_client_instance
        mock_client_instance.time_series.side_effect = ConnectionError("Network unreachable")
        
        from tradebot.exceptions import DataFetchError
        with pytest.raises(DataFetchError) as exc_info:
            setup_fetcher.fetch_historical_data("AAPL", "2024-01-01", "2024-01-03")
        
        assert "Unable to fetch data for AAPL" in str(exc_info.value)
    
    @patch('tradebot.data.fetcher.TDClient')
    def test_t1_3_invalid_symbol_handling(self, mock_td_client, setup_fetcher):
        """Test proper handling of invalid stock symbols"""
        mock_client_instance = Mock()
        mock_td_client.return_value = mock_client_instance
        
        from tradebot.exceptions import InvalidSymbolError
        mock_client_instance.time_series.side_effect = InvalidSymbolError("Symbol not found")
        
        with pytest.raises(InvalidSymbolError) as exc_info:
            setup_fetcher.fetch_historical_data("INVALID_XYZ", "2024-01-01", "2024-01-03")
        
        assert "Symbol not found" in str(exc_info.value)
    
    @patch('tradebot.data.fetcher.TDClient')
    def test_t1_3_timeout_error_handling(self, mock_td_client, setup_fetcher):
        """Test timeout handling for slow API responses"""
        mock_client_instance = Mock()
        mock_td_client.return_value = mock_client_instance
        mock_client_instance.time_series.side_effect = TimeoutError("Request timeout")
        
        from tradebot.exceptions import DataFetchError
        with pytest.raises(DataFetchError) as exc_info:
            setup_fetcher.fetch_historical_data("AAPL", "2024-01-01", "2024-01-03")
        
        assert "Unable to fetch data for AAPL" in str(exc_info.value)


class TestDataValidation:
    """T1.4 Data Validation Testing"""
    
    @pytest.fixture
    def validator(self):
        from tradebot.data.validator import DataValidator
        return DataValidator()
    
    @pytest.fixture
    def valid_ohlcv_data(self):
        """Provide valid OHLCV test data"""
        dates = pd.date_range('2024-01-01', periods=3, freq='D')
        return pd.DataFrame({
            'open': [150.0, 151.0, 152.0],
            'high': [155.0, 156.0, 157.0],
            'low': [149.0, 150.0, 151.0], 
            'close': [154.0, 155.0, 156.0],
            'volume': [1000000, 1100000, 1200000]
        }, index=dates)
    
    def test_t1_4_valid_ohlcv_passes_validation(self, validator, valid_ohlcv_data):
        """Test that valid OHLCV data passes validation"""
        try:
            result = validator.validate(valid_ohlcv_data)
            assert result is not None
        except Exception:
            pytest.fail("Valid OHLCV data should pass validation")
    
    def test_t1_4_missing_volume_column_fails(self, validator, valid_ohlcv_data):
        """Test validation failure when volume column is missing"""
        invalid_data = valid_ohlcv_data.drop('volume', axis=1)
        
        from tradebot.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(invalid_data)
        
        assert "volume" in str(exc_info.value).lower()
    
    def test_t1_4_non_chronological_dates_fail(self, validator):
        """Test validation failure for non-chronological date ordering"""
        # Create data with out-of-order dates
        invalid_dates = [
            pd.Timestamp('2024-01-03'),
            pd.Timestamp('2024-01-01'), 
            pd.Timestamp('2024-01-02')
        ]
        invalid_data = pd.DataFrame({
            'open': [150.0, 151.0, 152.0],
            'high': [155.0, 156.0, 157.0],
            'low': [149.0, 150.0, 151.0],
            'close': [154.0, 155.0, 156.0], 
            'volume': [1000000, 1100000, 1200000]
        }, index=invalid_dates)
        
        from tradebot.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(invalid_data)
        
        error_msg = str(exc_info.value).lower()
        assert "chronological" in error_msg or "order" in error_msg
    
    def test_t1_4_invalid_numeric_types_fail(self, validator):
        """Test validation failure for invalid numeric data types"""
        dates = pd.date_range('2024-01-01', periods=2, freq='D')
        invalid_data = pd.DataFrame({
            'open': ['invalid_string', 151.0],  # String in numeric column
            'high': [155.0, 156.0],
            'low': [149.0, 150.0],
            'close': [154.0, 155.0],
            'volume': [1000000, 1100000]
        }, index=dates)
        
        from tradebot.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(invalid_data)
        
        error_msg = str(exc_info.value).lower() 
        assert "open" in error_msg or "numeric" in error_msg