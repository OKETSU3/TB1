"""
Database models for the tradebot package.

This module provides Peewee ORM models for:
- StockData: Historical OHLCV data storage
- CacheMetadata: Cache management and metadata tracking
- Database schema design with proper indexing for query performance
"""

from peewee import (
    Model, 
    CharField, 
    DateField, 
    DecimalField, 
    IntegerField,
    DateTimeField,
    TextField,
    CompositeKey,
    SqliteDatabase
)
from datetime import datetime
import os


# Database connection
database = SqliteDatabase(
    os.getenv('DATABASE_PATH', 'tradebot_data.db'),
    pragmas={
        'journal_mode': 'wal',
        'cache_size': -64 * 1000,  # 64MB cache
        'foreign_keys': 1,
        'ignore_check_constraints': 0,
        'synchronous': 0
    }
)


class BaseModel(Model):
    """Base model with common configuration."""
    
    class Meta:
        database = database


class StockData(BaseModel):
    """
    Model for storing historical stock OHLCV data.
    
    This model stores daily stock market data with:
    - Composite primary key on symbol + date for uniqueness
    - Decimal fields for price data to maintain precision
    - Proper indexing for query performance
    """
    
    symbol = CharField(max_length=10, index=True)
    date = DateField(index=True)
    open_price = DecimalField(max_digits=12, decimal_places=4)
    high_price = DecimalField(max_digits=12, decimal_places=4)
    low_price = DecimalField(max_digits=12, decimal_places=4)
    close_price = DecimalField(max_digits=12, decimal_places=4)
    volume = IntegerField()
    created_at = DateTimeField(default=datetime.now)
    
    class Meta:
        # Composite primary key ensures uniqueness of symbol+date combinations
        primary_key = CompositeKey('symbol', 'date')
        # Additional indexes for common query patterns
        indexes = (
            # Index for querying by symbol
            (('symbol',), False),
            # Index for querying by date range
            (('date',), False),
            # Composite index for symbol + date range queries
            (('symbol', 'date'), False),
        )
        table_name = 'stock_data'
    
    def __repr__(self):
        return f"<StockData: {self.symbol} {self.date} ${self.close_price}>"


class CacheMetadata(BaseModel):
    """
    Model for storing cache metadata and management information.
    
    This model tracks cached data segments with:
    - Cache key generation for efficient lookups
    - Size tracking for cache management
    - Date range tracking for cache invalidation
    """
    
    cache_key = CharField(max_length=255, primary_key=True)
    symbol = CharField(max_length=10, index=True)
    start_date = DateField()
    end_date = DateField()
    record_count = IntegerField()
    data_size_bytes = IntegerField()
    created_at = DateTimeField(default=datetime.now)
    last_accessed = DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = (
            # Index for querying by symbol
            (('symbol',), False),
            # Index for date range queries
            (('start_date', 'end_date'), False),
            # Index for cache cleanup operations
            (('last_accessed',), False),
        )
        table_name = 'cache_metadata'
    
    def __repr__(self):
        return f"<CacheMetadata: {self.symbol} {self.start_date}-{self.end_date} ({self.record_count} records)>"
    
    @classmethod
    def generate_cache_key(cls, symbol: str, start_date: str, end_date: str) -> str:
        """
        Generate a standardized cache key for data segments.
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            
        Returns:
            Standardized cache key string
        """
        return f"{symbol}_{start_date}_{end_date}"
    
    def update_access_time(self):
        """Update the last accessed timestamp."""
        self.last_accessed = datetime.now()
        self.save()


def create_tables():
    """
    Create all database tables if they don't exist.
    
    This function should be called during application initialization
    to ensure all required tables are present.
    """
    database.create_tables([StockData, CacheMetadata], safe=True)


def drop_tables():
    """
    Drop all database tables.
    
    WARNING: This will permanently delete all data.
    Should only be used for testing or database resets.
    """
    database.drop_tables([StockData, CacheMetadata], safe=True)


def get_database_info():
    """
    Get database connection and table information.
    
    Returns:
        Dictionary with database statistics and information
    """
    with database:
        stock_count = StockData.select().count()
        cache_count = CacheMetadata.select().count()
        
    return {
        'database_path': database.database,
        'stock_records': stock_count,
        'cache_records': cache_count,
        'tables': ['stock_data', 'cache_metadata']
    }