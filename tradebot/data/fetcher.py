"""
Data fetcher module for retrieving market data from Twelve Data API.

This module provides the DataFetcher class which handles:
- API authentication and key management
- Historical data retrieval with caching
- Error handling and quota management
- Data validation and formatting
"""

import os
import pandas as pd
from twelvedata import TDClient
from typing import Optional, Dict, Any
import logging

from tradebot.exceptions import DataFetchError, InvalidSymbolError, QuotaExceededError

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Fetches market data from Twelve Data API with caching and quota management.
    
    This class handles all aspects of data retrieval including:
    - API key management from environment variables
    - Rate limiting to respect API quotas
    - Local caching to minimize API calls
    - Error handling for network and API issues
    """
    
    def __init__(self, config_manager, rate_limiter, cache):
        """
        Initialize DataFetcher with required dependencies.
        
        Args:
            config_manager: Configuration management instance
            rate_limiter: Rate limiting instance for API quota management
            cache: Data caching instance for local storage
            
        Raises:
            ValueError: If TWELVE_DATA_API_KEY environment variable is not set
        """
        self.config = config_manager
        self.rate_limiter = rate_limiter
        self.cache = cache
        
        # Load API key from environment variable
        self.api_key = os.getenv('TWELVE_DATA_API_KEY')
        if not self.api_key:
            raise ValueError("TWELVE_DATA_API_KEY environment variable not set")
            
        logger.info("DataFetcher initialized successfully")
    
    def fetch_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a given symbol and date range.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            
        Returns:
            pandas.DataFrame: OHLCV data with columns [open, high, low, close, volume]
            
        Raises:
            DataFetchError: If data fetching fails
            QuotaExceededError: If API quota is exceeded
        """
        # Check cache first (critical for quota management)
        cached_data = self.cache.get(symbol, start_date, end_date)
        if cached_data is not None and self._is_fresh(cached_data):
            logger.info(f"Using cached data for {symbol}")
            return cached_data
        
        # Check quota before API call (CRITICAL)
        if not self.rate_limiter.can_make_request():
            raise QuotaExceededError("Daily API quota exceeded")
        
        # Fetch from Twelve Data API
        try:
            logger.info(f"Fetching data for {symbol} from {start_date} to {end_date}")
            
            td = TDClient(apikey=self.api_key)
            data = td.time_series(
                symbol=symbol,
                interval="1day",
                start_date=start_date,
                end_date=end_date,
                outputsize=5000
            ).as_pandas()
            
            # Track API usage
            self.rate_limiter.record_request()
            
            # Validate and store in cache
            validated_data = self._validate_data(data)
            self.cache.store(symbol, start_date, end_date, validated_data)
            
            logger.info(f"Successfully fetched {len(validated_data)} records for {symbol}")
            return validated_data
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            
            # Propagate specific exceptions without wrapping
            if isinstance(e, InvalidSymbolError):
                raise e
                
            # Wrap other exceptions in DataFetchError
            raise DataFetchError(f"Unable to fetch data for {symbol}")
    
    def _is_fresh(self, cached_data) -> bool:
        """Check if cached data is still fresh."""
        # For now, assume cached data is fresh
        # This will be implemented properly in Phase 3
        return True
    
    def _validate_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate fetched data format and integrity."""
        if data is None or data.empty:
            raise ValueError("Empty data received from API")
        
        # Use DataValidator for comprehensive validation
        from tradebot.data.validator import DataValidator
        validator = DataValidator()
        return validator.validate(data)