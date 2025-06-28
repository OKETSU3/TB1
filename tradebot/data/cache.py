"""
Data caching module for the tradebot package.

This module provides efficient local database caching to reduce API calls:
- DataCache class for storing and retrieving historical market data
- Cache metadata tracking for management and invalidation
- Database-backed storage with SQLite for persistence
- Cache freshness validation based on configurable thresholds
"""

import pandas as pd
import logging
import pickle
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from peewee import DoesNotExist, IntegrityError

from .models import StockData, CacheMetadata, database, create_tables

logger = logging.getLogger(__name__)


class DataCache:
    """
    Local database cache for stock market data.
    
    This class provides efficient caching capabilities:
    - Store and retrieve pandas DataFrames with OHLCV data
    - Metadata tracking for cache management
    - Freshness validation based on configurable time thresholds
    - Database persistence using Peewee ORM
    """
    
    def __init__(self, database_path: Optional[str] = None):
        """
        Initialize DataCache with database connection.
        
        Args:
            database_path: Optional path to SQLite database file
        """
        if database_path:
            # Override default database path if provided
            database.init(database_path, pragmas={
                'journal_mode': 'wal',
                'cache_size': -64 * 1000,  # 64MB cache
                'foreign_keys': 1,
                'ignore_check_constraints': 0,
                'synchronous': 0
            })
        
        # Ensure database tables exist
        create_tables()
        
        logger.info(f"DataCache initialized with database: {database.database}")
    
    def store(self, symbol: str, start_date: str, end_date: str, data: pd.DataFrame) -> None:
        """
        Store OHLCV data in cache with metadata tracking.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            data: Pandas DataFrame with OHLCV data
            
        Raises:
            ValueError: If data format is invalid
            IntegrityError: If duplicate records exist
        """
        if data.empty:
            logger.warning(f"Attempted to store empty data for {symbol}")
            return
        
        # Validate required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"Data missing required columns: {missing_columns}")
        
        try:
            with database.atomic():
                # Store individual records
                records_stored = 0
                for date_index, row in data.iterrows():
                    try:
                        StockData.create(
                            symbol=symbol,
                            date=date_index.date() if hasattr(date_index, 'date') else date_index,
                            open_price=float(row['open']),
                            high_price=float(row['high']),
                            low_price=float(row['low']),
                            close_price=float(row['close']),
                            volume=int(row['volume'])
                        )
                        records_stored += 1
                    except IntegrityError:
                        # Record already exists, update it
                        StockData.update(
                            open_price=float(row['open']),
                            high_price=float(row['high']),
                            low_price=float(row['low']),
                            close_price=float(row['close']),
                            volume=int(row['volume'])
                        ).where(
                            (StockData.symbol == symbol) & 
                            (StockData.date == (date_index.date() if hasattr(date_index, 'date') else date_index))
                        ).execute()
                        records_stored += 1
                
                # Store cache metadata
                cache_key = CacheMetadata.generate_cache_key(symbol, start_date, end_date)
                data_size = len(pickle.dumps(data))
                
                try:
                    CacheMetadata.create(
                        cache_key=cache_key,
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        record_count=records_stored,
                        data_size_bytes=data_size
                    )
                except IntegrityError:
                    # Update existing metadata
                    CacheMetadata.update(
                        record_count=records_stored,
                        data_size_bytes=data_size,
                        last_accessed=datetime.now()
                    ).where(CacheMetadata.cache_key == cache_key).execute()
                
                logger.info(f"Stored {records_stored} records for {symbol} ({start_date} to {end_date})")
                
        except Exception as e:
            logger.error(f"Failed to store cache data for {symbol}: {e}")
            raise
    
    def get(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Retrieve OHLCV data from cache.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Pandas DataFrame with OHLCV data, or None if not cached
        """
        try:
            # Update metadata access time
            cache_key = CacheMetadata.generate_cache_key(symbol, start_date, end_date)
            try:
                metadata = CacheMetadata.get(CacheMetadata.cache_key == cache_key)
                metadata.update_access_time()
            except DoesNotExist:
                # No metadata found, data not cached
                logger.debug(f"Cache miss: No metadata for {symbol} ({start_date} to {end_date})")
                return None
            
            # Retrieve data records
            query = StockData.select().where(
                (StockData.symbol == symbol) &
                (StockData.date >= start_date) &
                (StockData.date <= end_date)
            ).order_by(StockData.date)
            
            records = list(query)
            if not records:
                logger.debug(f"Cache miss: No data records for {symbol} ({start_date} to {end_date})")
                return None
            
            # Convert to DataFrame
            data_dict = {
                'open': [float(r.open_price) for r in records],
                'high': [float(r.high_price) for r in records],
                'low': [float(r.low_price) for r in records],
                'close': [float(r.close_price) for r in records],
                'volume': [r.volume for r in records]
            }
            
            dates = [r.date for r in records]
            df = pd.DataFrame(data_dict, index=pd.to_datetime(dates))
            
            logger.debug(f"Cache hit: Retrieved {len(df)} records for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to retrieve cache data for {symbol}: {e}")
            return None
    
    def is_fresh(self, symbol: str, start_date: str, end_date: str, hours: int = 24) -> bool:
        """
        Check if cached data is fresh (within specified time threshold).
        
        Args:
            symbol: Stock symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            hours: Freshness threshold in hours
            
        Returns:
            True if data is fresh, False otherwise
        """
        try:
            cache_key = CacheMetadata.generate_cache_key(symbol, start_date, end_date)
            metadata = CacheMetadata.get(CacheMetadata.cache_key == cache_key)
            
            # Check if data is within freshness threshold
            age = datetime.now() - metadata.created_at
            is_fresh = age <= timedelta(hours=hours)
            
            logger.debug(f"Cache freshness check for {symbol}: {age} <= {timedelta(hours=hours)} = {is_fresh}")
            return is_fresh
            
        except DoesNotExist:
            logger.debug(f"Cache freshness check: No metadata for {symbol}")
            return False
        except Exception as e:
            logger.error(f"Failed to check cache freshness for {symbol}: {e}")
            return False
    
    def get_metadata(self, symbol: str, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """
        Get cache metadata for a data segment.
        
        Args:
            symbol: Stock symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary with metadata information, or None if not found
        """
        try:
            cache_key = CacheMetadata.generate_cache_key(symbol, start_date, end_date)
            metadata = CacheMetadata.get(CacheMetadata.cache_key == cache_key)
            
            return {
                'cache_key': metadata.cache_key,
                'symbol': metadata.symbol,
                'start_date': metadata.start_date.isoformat(),
                'end_date': metadata.end_date.isoformat(),
                'record_count': metadata.record_count,
                'data_size_bytes': metadata.data_size_bytes,
                'created_at': metadata.created_at.isoformat(),
                'last_accessed': metadata.last_accessed.isoformat()
            }
            
        except DoesNotExist:
            logger.debug(f"No metadata found for {symbol} ({start_date} to {end_date})")
            return None
        except Exception as e:
            logger.error(f"Failed to get metadata for {symbol}: {e}")
            return None
    
    def clear_cache(self, symbol: Optional[str] = None, older_than_days: Optional[int] = None) -> int:
        """
        Clear cache data based on specified criteria.
        
        Args:
            symbol: Optional symbol to clear (clears all if None)
            older_than_days: Optional age threshold in days
            
        Returns:
            Number of records deleted
        """
        try:
            with database.atomic():
                # Build delete query
                stock_query = StockData.delete()
                metadata_query = CacheMetadata.delete()
                
                if symbol:
                    stock_query = stock_query.where(StockData.symbol == symbol)
                    metadata_query = metadata_query.where(CacheMetadata.symbol == symbol)
                
                if older_than_days:
                    cutoff_date = datetime.now() - timedelta(days=older_than_days)
                    stock_query = stock_query.where(StockData.created_at < cutoff_date)
                    metadata_query = metadata_query.where(CacheMetadata.created_at < cutoff_date)
                
                # Execute deletions
                stock_deleted = stock_query.execute()
                metadata_deleted = metadata_query.execute()
                
                total_deleted = stock_deleted + metadata_deleted
                logger.info(f"Cache cleared: {total_deleted} records deleted")
                return total_deleted
                
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics and information.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            with database:
                stock_count = StockData.select().count()
                metadata_count = CacheMetadata.select().count()
                
                # Get symbols count
                symbols = StockData.select(StockData.symbol).distinct().count()
                
                # Get oldest and newest data
                oldest_record = StockData.select().order_by(StockData.date.asc()).first()
                newest_record = StockData.select().order_by(StockData.date.desc()).first()
                
                return {
                    'total_records': stock_count,
                    'cache_entries': metadata_count,
                    'unique_symbols': symbols,
                    'oldest_data': oldest_record.date.isoformat() if oldest_record else None,
                    'newest_data': newest_record.date.isoformat() if newest_record else None,
                    'database_path': database.database
                }
                
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                'total_records': 0,
                'cache_entries': 0,
                'unique_symbols': 0,
                'oldest_data': None,
                'newest_data': None,
                'database_path': database.database
            }