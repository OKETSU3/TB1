"""
Batch processing module for retrieving market data from multiple symbols efficiently.

This module provides the BatchProcessor class which handles:
- Multi-symbol data fetching with quota management
- Intelligent batch sizing based on remaining API quota
- Sequential processing to avoid quota burst
- Bulk database operations for efficiency
- Error handling for mixed success/failure scenarios
"""

import os
import pandas as pd
from twelvedata import TDClient
from typing import Dict, List, Optional, Tuple
import logging

from tradebot.exceptions import DataFetchError, InvalidSymbolError, QuotaExceededError
from tradebot.data.validator import DataValidator

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Processes multiple stock symbols efficiently with quota management.
    
    This class handles batch operations including:
    - Quota-aware batch sizing to prevent API limit violations
    - Sequential processing to avoid request bursts
    - Error handling for individual symbol failures
    - Bulk database operations for performance
    """
    
    def __init__(self, config, rate_limiter, cache):
        """
        Initialize BatchProcessor with required dependencies.
        
        Args:
            config: Configuration management instance
            rate_limiter: Rate limiting instance for API quota management
            cache: Data caching instance for local storage
            
        Raises:
            ValueError: If TWELVE_DATA_API_KEY environment variable is not set
        """
        self.config = config
        self.rate_limiter = rate_limiter
        self.cache = cache
        
        # Load API key from environment variable
        self.api_key = os.getenv('TWELVE_DATA_API_KEY')
        if not self.api_key:
            raise ValueError("TWELVE_DATA_API_KEY environment variable not set")
        
        # Initialize data validator
        self.validator = DataValidator()
            
        logger.info("BatchProcessor initialized successfully")
    
    def calculate_optimal_batch_size(self, symbols: List[str]) -> int:
        """
        Calculate optimal batch size based on remaining API quota.
        
        Args:
            symbols: List of stock symbols to process
            
        Returns:
            int: Optimal batch size that doesn't exceed quota
        """
        # Get current quota usage
        usage = self.rate_limiter.get_usage()
        remaining_quota = usage['remaining']
        
        # Calculate requests needed for all symbols
        total_requests_needed = len(symbols)
        
        # Ensure we don't exceed remaining quota
        optimal_size = min(total_requests_needed, remaining_quota)
        
        # Ensure we return at least 1 if there's any quota available
        if remaining_quota > 0 and optimal_size == 0:
            optimal_size = 1
            
        logger.info(f"Calculated optimal batch size: {optimal_size} (requested: {total_requests_needed}, remaining quota: {remaining_quota})")
        return optimal_size
    
    def calculate_total_requests_needed(self, symbols: List[str]) -> int:
        """
        Calculate total API requests needed for the given symbols.
        
        Args:
            symbols: List of stock symbols to process
            
        Returns:
            int: Total number of API requests needed
        """
        # Each symbol requires exactly 1 API request
        return len(symbols)
    
    def fetch_multiple_symbols(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical data for multiple symbols with quota management.
        
        Args:
            symbols: List of stock symbols to fetch
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping symbols to their data
            
        Raises:
            QuotaExceededError: If insufficient quota for all symbols
        """
        results = {}
        
        # Calculate optimal batch size
        batch_size = self.calculate_optimal_batch_size(symbols)
        
        if batch_size == 0:
            raise QuotaExceededError("Insufficient API quota for batch processing")
        
        # Process symbols sequentially to avoid quota burst
        symbols_to_process = symbols[:batch_size]
        
        logger.info(f"Processing {len(symbols_to_process)} symbols sequentially")
        
        for symbol in symbols_to_process:
            try:
                # Fetch data for single symbol
                data = self._fetch_single_symbol(symbol, start_date, end_date)
                if data is not None:
                    results[symbol] = data
                    logger.info(f"Successfully fetched data for {symbol}")
                    
            except InvalidSymbolError as e:
                # Log invalid symbol but continue processing others
                logger.warning(f"Invalid symbol {symbol}: {e}")
                continue
                
            except Exception as e:
                # Log other errors but continue processing
                logger.error(f"Failed to fetch data for {symbol}: {e}")
                continue
        
        logger.info(f"Batch processing complete: {len(results)} successful out of {len(symbols_to_process)} requested")
        return results
    
    def _fetch_single_symbol(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Fetch data for a single symbol with caching and validation.
        
        Args:
            symbol: Stock symbol to fetch
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            
        Returns:
            Optional[pd.DataFrame]: OHLCV data or None if failed
            
        Raises:
            InvalidSymbolError: If symbol is invalid
            DataFetchError: If data fetching fails
            QuotaExceededError: If quota is exceeded
        """
        # Check cache first (critical for quota management)
        cached_data = self.cache.get(symbol, start_date, end_date)
        if cached_data is not None:
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
            validated_data = self.validator.validate(data)
            self.cache.store(symbol, start_date, end_date, validated_data)
            
            logger.info(f"Successfully fetched {len(validated_data)} records for {symbol}")
            return validated_data
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            
            # Propagate specific exceptions without wrapping
            if isinstance(e, InvalidSymbolError):
                raise e
                
            # Wrap other exceptions in DataFetchError
            raise DataFetchError(f"Unable to fetch data for {symbol}") from e
    
    def bulk_store_results(self, results: Dict[str, pd.DataFrame], start_date: str, end_date: str) -> int:
        """
        Store multiple symbol results efficiently using bulk operations.
        
        Args:
            results: Dictionary mapping symbols to their data
            start_date: Start date for the data
            end_date: End date for the data
            
        Returns:
            int: Number of symbols successfully stored
        """
        stored_count = 0
        
        for symbol, data in results.items():
            try:
                # Store each symbol's data
                self.cache.store(symbol, start_date, end_date, data)
                stored_count += 1
                logger.debug(f"Stored data for {symbol}")
                
            except Exception as e:
                logger.error(f"Failed to store data for {symbol}: {e}")
                continue
        
        logger.info(f"Bulk storage complete: {stored_count} symbols stored successfully")
        return stored_count