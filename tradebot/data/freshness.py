"""
Data freshness management module for the tradebot package.

This module provides intelligent cache invalidation based on data age and market conditions:
- FreshnessManager class for cache age calculation and invalidation
- Market hours awareness for intelligent caching decisions
- Configurable data freshness thresholds
- Cache cleanup for old data
"""

import logging
from datetime import datetime, timedelta, time
from typing import Optional, Dict, Any, List
from zoneinfo import ZoneInfo
from .cache import DataCache

logger = logging.getLogger(__name__)


class FreshnessManager:
    """
    Manages data freshness and cache invalidation logic.
    
    This class provides intelligent cache management:
    - Cache age calculation for freshness validation
    - Market hours detection for appropriate caching behavior
    - Configurable freshness thresholds
    - Automated cache cleanup for old data
    """
    
    def __init__(self, cache: DataCache, timezone: str = "US/Eastern"):
        """
        Initialize FreshnessManager with cache instance.
        
        Args:
            cache: DataCache instance for cache operations
            timezone: Market timezone (default: US/Eastern for NYSE/NASDAQ)
        """
        self.cache = cache
        self.timezone = ZoneInfo(timezone)
        
        # Market hours configuration (US market)
        self.market_open_time = time(9, 30)  # 9:30 AM EST
        self.market_close_time = time(16, 0)  # 4:00 PM EST
        
        # Default freshness thresholds
        self.default_freshness_minutes = {
            'intraday': 5,      # 5 minutes for intraday data
            'daily': 60,        # 1 hour for daily data
            'after_hours': 240, # 4 hours for after-hours data
            'weekend': 1440     # 24 hours for weekend data
        }
        
        logger.info(f"FreshnessManager initialized with timezone: {timezone}")
    
    def get_cache_age(self, symbol: str, start_date: str, end_date: str) -> float:
        """
        Calculate cache age in minutes for given data segment.
        
        Args:
            symbol: Stock symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Age in minutes as float, or 0.0 if no cache found
        """
        try:
            metadata = self.cache.get_metadata(symbol, start_date, end_date)
            if not metadata:
                logger.debug(f"No cache metadata found for {symbol}")
                return float('inf')  # No cache = infinitely old
            
            # Parse creation time
            created_at_str = metadata['created_at']
            if 'Z' in created_at_str:
                created_at_str = created_at_str.replace('Z', '+00:00')
            
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except ValueError:
                # Fallback for basic datetime parsing
                created_at = datetime.fromisoformat(created_at_str.split('.')[0])
            
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=ZoneInfo('UTC'))
            
            # Calculate age
            now = datetime.now(ZoneInfo('UTC'))
            age_delta = now - created_at
            age_minutes = max(0.0, age_delta.total_seconds() / 60.0)  # Ensure non-negative
            
            logger.debug(f"Cache age for {symbol}: {age_minutes:.2f} minutes")
            return age_minutes
            
        except Exception as e:
            logger.error(f"Failed to calculate cache age for {symbol}: {e}")
            return float('inf')
    
    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        """
        Check if the market is currently open.
        
        Args:
            dt: Optional datetime to check (defaults to now)
            
        Returns:
            True if market is open, False otherwise
        """
        if dt is None:
            # For testing compatibility with freezegun, use naive datetime then localize
            dt = datetime.now()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=self.timezone)
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.timezone)
        else:
            dt = dt.astimezone(self.timezone)
        
        # Check if it's a weekend
        if self.is_weekend(dt):
            return False
        
        # Check if within market hours
        current_time = dt.time()
        is_open = self.market_open_time <= current_time <= self.market_close_time
        
        logger.debug(f"Market open check for {dt}: {is_open}")
        return is_open
    
    def is_weekend(self, dt: Optional[datetime] = None) -> bool:
        """
        Check if the given datetime is a weekend.
        
        Args:
            dt: Optional datetime to check (defaults to now)
            
        Returns:
            True if weekend, False otherwise
        """
        if dt is None:
            # For testing compatibility with freezegun, use naive datetime then localize
            dt = datetime.now()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=self.timezone)
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.timezone)
        else:
            dt = dt.astimezone(self.timezone)
        
        # Saturday = 5, Sunday = 6
        is_weekend = dt.weekday() >= 5
        logger.debug(f"Weekend check for {dt}: {is_weekend}")
        return is_weekend
    
    def get_market_open_time(self, dt: Optional[datetime] = None) -> datetime:
        """
        Get the market open time for a given date.
        
        Args:
            dt: Optional datetime for the date (defaults to today)
            
        Returns:
            Datetime representing market open time
        """
        if dt is None:
            # For testing compatibility with freezegun, use naive datetime then localize
            dt = datetime.now()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=self.timezone)
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.timezone)
        else:
            dt = dt.astimezone(self.timezone)
        
        # Create market open datetime for the given date
        market_open = dt.replace(
            hour=self.market_open_time.hour,
            minute=self.market_open_time.minute,
            second=0,
            microsecond=0
        )
        
        return market_open
    
    def is_data_fresh(self, symbol: str, start_date: str, end_date: str, 
                     threshold_minutes: Optional[int] = None) -> bool:
        """
        Check if cached data is fresh based on configurable thresholds.
        
        Args:
            symbol: Stock symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            threshold_minutes: Custom freshness threshold in minutes
            
        Returns:
            True if data is fresh, False otherwise
        """
        age_minutes = self.get_cache_age(symbol, start_date, end_date)
        
        # Determine threshold based on market conditions if not specified
        if threshold_minutes is None:
            threshold_minutes = self._get_adaptive_threshold()
        
        is_fresh = age_minutes <= threshold_minutes
        logger.debug(f"Freshness check for {symbol}: {age_minutes:.2f}min <= {threshold_minutes}min = {is_fresh}")
        return is_fresh
    
    def _get_adaptive_threshold(self) -> int:
        """
        Get adaptive freshness threshold based on current market conditions.
        
        Returns:
            Freshness threshold in minutes
        """
        now = datetime.now(self.timezone)
        
        if self.is_weekend(now):
            return self.default_freshness_minutes['weekend']
        elif self.is_market_open(now):
            return self.default_freshness_minutes['intraday']
        else:
            return self.default_freshness_minutes['after_hours']
    
    def should_invalidate_cache(self, symbol: str, start_date: str, end_date: str) -> bool:
        """
        Determine if cache should be invalidated based on freshness logic.
        
        Args:
            symbol: Stock symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            True if cache should be invalidated, False otherwise
        """
        # Check if data exists
        if not self.cache.get_metadata(symbol, start_date, end_date):
            logger.debug(f"No cache found for {symbol}, invalidation not needed")
            return False
        
        # Check freshness
        is_fresh = self.is_data_fresh(symbol, start_date, end_date)
        should_invalidate = not is_fresh
        
        logger.debug(f"Cache invalidation decision for {symbol}: {should_invalidate}")
        return should_invalidate
    
    def cleanup_old_cache(self, days_to_keep: int = 30) -> int:
        """
        Clean up old cache data beyond the specified retention period.
        
        Args:
            days_to_keep: Number of days to keep in cache
            
        Returns:
            Number of records cleaned up
        """
        try:
            logger.info(f"Starting cache cleanup, keeping {days_to_keep} days")
            
            # Use the cache's built-in cleanup method
            cleaned_count = self.cache.clear_cache(older_than_days=days_to_keep)
            
            logger.info(f"Cache cleanup completed: {cleaned_count} records removed")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old cache: {e}")
            return 0
    
    def invalidate_cache_entry(self, symbol: str, start_date: str, end_date: str) -> bool:
        """
        Manually invalidate a specific cache entry.
        
        Args:
            symbol: Stock symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            True if successfully invalidated, False otherwise
        """
        try:
            # Log the cache entry being invalidated for audit purposes
            logger.info(f"Invalidating cache entry for {symbol} ({start_date} to {end_date})")
            
            # Remove the specific cache entry for the symbol
            deleted_count = self.cache.clear_cache(symbol=symbol)
            
            if deleted_count > 0:
                logger.info(f"Invalidated cache for {symbol}: {deleted_count} records removed")
                return True
            else:
                logger.debug(f"No cache found to invalidate for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to invalidate cache for {symbol}: {e}")
            return False
    
    def get_freshness_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive freshness report for cached data.
        
        Returns:
            Dictionary with freshness statistics and recommendations
        """
        try:
            cache_stats = self.cache.get_cache_stats()
            current_time = datetime.now(ZoneInfo('UTC')).astimezone(self.timezone)
            
            report = {
                'timestamp': current_time.isoformat(),
                'market_status': {
                    'is_open': self.is_market_open(current_time),
                    'is_weekend': self.is_weekend(current_time),
                    'next_open': self._get_next_market_open(current_time).isoformat()
                },
                'cache_statistics': cache_stats,
                'freshness_thresholds': self.default_freshness_minutes,
                'adaptive_threshold_minutes': self._get_adaptive_threshold(),
                'recommendations': self._generate_freshness_recommendations()
            }
            
            logger.info("Generated freshness report")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate freshness report: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_next_market_open(self, dt: datetime) -> datetime:
        """
        Calculate the next market open time.
        
        Args:
            dt: Current datetime
            
        Returns:
            Next market open datetime
        """
        # Simple implementation: next business day at market open time
        next_day = dt + timedelta(days=1)
        while self.is_weekend(next_day):
            next_day += timedelta(days=1)
        
        return next_day.replace(
            hour=self.market_open_time.hour,
            minute=self.market_open_time.minute,
            second=0,
            microsecond=0
        )
    
    def _generate_freshness_recommendations(self) -> List[str]:
        """
        Generate recommendations based on current market conditions.
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        current_time = datetime.now(ZoneInfo('UTC')).astimezone(self.timezone)
        
        if self.is_market_open(current_time):
            recommendations.append("Market is open - consider shorter freshness thresholds for active trading")
            recommendations.append("Intraday data should be refreshed every 5 minutes")
        elif self.is_weekend(current_time):
            recommendations.append("Market is closed for weekend - longer freshness thresholds acceptable")
            recommendations.append("Consider cleanup of old cache data during weekend")
        else:
            recommendations.append("Market is closed - moderate freshness thresholds appropriate")
        
        return recommendations