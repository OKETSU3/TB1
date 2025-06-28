"""
Rate limiting module for API quota management.

This module provides the RateLimiter class which handles:
- Daily quota enforcement (800 requests/day for free tier)
- Request spacing with minimum intervals
- Persistent quota storage using SQLite
- Quota reset at daily boundaries
- Critical quota protection to prevent API limit exceeded errors
"""

import sqlite3
import time
import threading
import tempfile
from datetime import datetime, date
from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Manages API request rate limiting with persistent quota tracking.
    
    This class is CRITICAL for protecting against API quota exceeded errors:
    - Enforces daily request limits (default: 800 requests/day)
    - Implements request spacing to avoid burst requests
    - Stores quota usage persistently across application restarts
    - Provides quota reset functionality at daily boundaries
    """
    
    def __init__(self, daily_limit: int = 800, min_interval: float = 7.5, storage_path: Optional[str] = None):
        """
        Initialize RateLimiter with quota parameters.
        
        Args:
            daily_limit: Maximum requests allowed per day
            min_interval: Minimum seconds between requests (default 7.5s = 8 req/min)
            storage_path: Path to SQLite database for persistent storage
            
        Raises:
            RuntimeError: If database initialization fails
        """
        self.daily_limit = daily_limit
        self.min_interval = min_interval
        self.storage_path = storage_path or os.path.join(tempfile.gettempdir(), "quota_tracking.db")
        
        # Thread safety
        self._lock = threading.Lock()
        self._last_request_time = 0.0
        
        # Initialize persistent storage
        self._init_database()
        
        # Load current quota usage
        self._current_usage = self._load_daily_usage()
        
        logger.info(f"RateLimiter initialized: {daily_limit} requests/day, {min_interval}s min interval")
    
    def _init_database(self) -> None:
        """Initialize SQLite database for quota tracking."""
        try:
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS quota_tracking (
                        date TEXT PRIMARY KEY,
                        requests_used INTEGER NOT NULL DEFAULT 0,
                        last_request_time REAL NOT NULL DEFAULT 0.0,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
            
            logger.info(f"Quota database initialized: {self.storage_path}")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize quota database: {e}")
            raise RuntimeError(f"Quota database initialization failed: {e}") from e
    
    def _load_daily_usage(self) -> Dict[str, Any]:
        """Load current day's quota usage from database."""
        today = date.today().isoformat()
        
        try:
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT requests_used, last_request_time FROM quota_tracking WHERE date = ?',
                    (today,)
                )
                row = cursor.fetchone()
                
                if row:
                    requests_used, last_request_time = row
                    logger.info(f"Loaded quota usage for {today}: {requests_used}/{self.daily_limit}")
                    return {
                        'date': today,
                        'used': requests_used,
                        'last_request_time': last_request_time
                    }
                else:
                    # No record for today, start fresh
                    logger.info(f"Starting fresh quota tracking for {today}")
                    return {
                        'date': today,
                        'used': 0,
                        'last_request_time': 0.0
                    }
                    
        except sqlite3.Error as e:
            logger.error(f"Failed to load quota usage: {e}")
            # Return safe defaults if database fails
            return {
                'date': today,
                'used': 0,
                'last_request_time': 0.0
            }
    
    def _save_daily_usage(self) -> None:
        """Save current quota usage to database."""
        try:
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO quota_tracking 
                    (date, requests_used, last_request_time)
                    VALUES (?, ?, ?)
                ''', (
                    self._current_usage['date'],
                    self._current_usage['used'],
                    self._current_usage['last_request_time']
                ))
                conn.commit()
                
        except sqlite3.Error as e:
            logger.error(f"Failed to save quota usage: {e}")
            raise
    
    def can_make_request(self) -> bool:
        """
        Check if a request can be made within quota limits.
        
        Returns:
            True if request is allowed, False if quota exceeded
        """
        # Check if we need to reset quota for new day
        today = date.today().isoformat()
        if self._current_usage['date'] != today:
            self._reset_daily_quota()
        
        # Check daily quota
        if self._current_usage['used'] >= self.daily_limit:
            logger.warning(f"Daily quota exceeded: {self._current_usage['used']}/{self.daily_limit}")
            return False
        
        return True
    
    def record_request(self) -> None:
        """
        Record that a request was made (increment quota usage).
        
        This should be called after successful API requests.
        """
        # Check if we need to reset quota for new day
        today = date.today().isoformat()
        if self._current_usage['date'] != today:
            self._reset_daily_quota()
        
        # Increment usage
        self._current_usage['used'] += 1
        self._current_usage['last_request_time'] = time.time()
        
        # Save to database
        self._save_daily_usage()
        
        logger.info(f"Request recorded: {self._current_usage['used']}/{self.daily_limit}")
    
    def acquire(self) -> None:
        """
        Acquire permission to make a request with rate limiting.
        
        This method:
        1. Checks quota availability
        2. Enforces minimum request spacing
        3. Records the request
        
        Raises:
            QuotaExceededError: If daily quota is exceeded
        """
        with self._lock:
            # Check quota
            if not self.can_make_request():
                from tradebot.exceptions import QuotaExceededError
                raise QuotaExceededError(
                    f"Daily API quota exceeded: {self._current_usage['used']}/{self.daily_limit} requests used"
                )
            
            # Enforce minimum request spacing
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping {sleep_time:.3f}s")
                time.sleep(sleep_time)
            
            # Update last request time
            self._last_request_time = time.time()
            
            # Record the request
            self.record_request()
    
    def get_usage(self) -> Dict[str, Any]:
        """
        Get current quota usage statistics.
        
        Returns:
            Dictionary with quota usage information
        """
        with self._lock:
            # Check if we need to reset quota for new day
            today = date.today().isoformat()
            if self._current_usage['date'] != today:
                self._reset_daily_quota()
            
            return {
                'date': self._current_usage['date'],
                'used': self._current_usage['used'],
                'limit': self.daily_limit,
                'remaining': self.daily_limit - self._current_usage['used'],
                'percentage': (self._current_usage['used'] / self.daily_limit) * 100
            }
    
    def _reset_daily_quota(self) -> None:
        """Reset quota usage for a new day."""
        today = date.today().isoformat()
        old_date = self._current_usage['date']
        
        self._current_usage = {
            'date': today,
            'used': 0,
            'last_request_time': 0.0
        }
        
        # Save the reset state
        self._save_daily_usage()
        
        logger.info(f"Daily quota reset: {old_date} -> {today}")
    
    def reset_quota(self, force: bool = False) -> None:
        """
        Manually reset quota (for testing purposes).
        
        WARNING: This should only be used in testing environments.
        
        Args:
            force (bool): Must be True to proceed with quota reset.
                         This is a safety measure to prevent accidental usage.
        
        Raises:
            ValueError: If force parameter is not True
            RuntimeError: If ENVIRONMENT is set to 'production'
        """
        # Safety check: force parameter must be explicitly True
        if force is not True:
            raise ValueError("reset_quota requires force=True parameter to prevent accidental usage")
        
        # Safety check: prevent usage in production environments
        import os
        environment = os.getenv('ENVIRONMENT', '').lower()
        if environment == 'production':
            raise RuntimeError("reset_quota is disabled in production environments")
        
        with self._lock:
            today = date.today().isoformat()
            self._current_usage = {
                'date': today,
                'used': 0,
                'last_request_time': 0.0
            }
            
            # Clear database entry for today
            try:
                with sqlite3.connect(self.storage_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM quota_tracking WHERE date = ?', (today,))
                    conn.commit()
                
                logger.warning("Quota manually reset (testing only)")
                
            except sqlite3.Error as e:
                logger.error(f"Failed to reset quota: {e}")
    
    def get_quota_status(self) -> str:
        """
        Get human-readable quota status.
        
        Returns:
            Formatted quota status string
        """
        usage = self.get_usage()
        
        if usage['percentage'] >= 100:
            status = "EXCEEDED"
        elif usage['percentage'] >= 90:
            status = "CRITICAL"
        elif usage['percentage'] >= 80:
            status = "HIGH"
        elif usage['percentage'] >= 50:
            status = "MODERATE"
        else:
            status = "LOW"
        
        return (f"Quota Status: {status} - "
                f"{usage['used']}/{usage['limit']} requests "
                f"({usage['percentage']:.1f}%) used today")
    
    def close(self) -> None:
        """Close database connections and cleanup resources."""
        # Save final state
        self._save_daily_usage()
        logger.info("RateLimiter closed")


class QuotaMonitor:
    """
    Monitor and report quota usage across multiple RateLimiter instances.
    
    This class provides centralized quota monitoring capabilities.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize QuotaMonitor.
        
        Args:
            storage_path: Path to quota database
        """
        self.storage_path = storage_path or "quota_tracking.db"
    
    def get_historical_usage(self, days: int = 7) -> Dict[str, Dict[str, Any]]:
        """
        Get historical quota usage for the last N days.
        
        Args:
            days: Number of days to retrieve
            
        Returns:
            Dictionary mapping dates to usage statistics
        """
        try:
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT date, requests_used, created_at
                    FROM quota_tracking
                    ORDER BY date DESC
                    LIMIT ?
                ''', (days,))
                
                results = {}
                for row in cursor.fetchall():
                    date_str, requests_used, created_at = row
                    results[date_str] = {
                        'requests_used': requests_used,
                        'created_at': created_at
                    }
                
                return results
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get historical usage: {e}")
            return {}
    
    def cleanup_old_records(self, keep_days: int = 30) -> int:
        """
        Clean up old quota tracking records.
        
        Args:
            keep_days: Number of days to keep
            
        Returns:
            Number of records deleted
        """
        cutoff_date = date.today().isoformat()
        # This is a simplified implementation - in production,
        # you would calculate the actual cutoff date
        
        try:
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM quota_tracking
                    WHERE date < date('now', '-' || ? || ' days')
                ''', (keep_days,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} old quota records")
                return deleted_count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to cleanup old records: {e}")
            return 0