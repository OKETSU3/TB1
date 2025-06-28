"""
Logging utilities for the tradebot package.

This module provides specialized logging functionality including:
- Structured logging for data operations
- API usage tracking and monitoring
- Performance metrics logging
- Configurable log levels and rotation
"""

import logging
import logging.handlers
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import time


class APIUsageLogger:
    """
    Specialized logger for API usage tracking and structured logging.
    
    This class provides comprehensive logging capabilities:
    - Structured log messages for all operations
    - API usage tracking with quota monitoring
    - Performance metrics logging
    - Configurable log levels and output
    """
    
    def __init__(self, name: str = "tradebot", level: str = "INFO", log_file: Optional[str] = None):
        """
        Initialize APIUsageLogger with configurable options.
        
        Args:
            name: Logger name
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional log file path for file output
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Remove existing handlers to avoid duplication
        self.logger.handlers.clear()
        
        # Create formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler with rotation if log_file specified
        if log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=5
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Initialize API usage tracking
        self._daily_requests = 0
        self._last_reset_date = datetime.now().date()
        
        self.logger.info("APIUsageLogger initialized")
    
    def log_operation(self, operation: str, symbol: str, metadata: Dict[str, Any]) -> None:
        """
        Log a structured data operation with metadata.
        
        Args:
            operation: Type of operation (e.g., 'fetch_data', 'cache_hit')
            symbol: Stock symbol being processed
            metadata: Additional operation metadata
        """
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "symbol": symbol,
            "metadata": metadata
        }
        
        self.logger.info(f"OPERATION: {json.dumps(log_data, separators=(',', ':'))}")
    
    def log_api_usage(self, symbol: str, operation: str, requests_used: int, daily_limit: int) -> None:
        """
        Log API usage with quota tracking.
        
        Args:
            symbol: Stock symbol for the request
            operation: Type of API operation
            requests_used: Number of requests used for this operation
            daily_limit: Daily API request limit
        """
        # Update daily request counter
        current_date = datetime.now().date()
        if current_date != self._last_reset_date:
            self._daily_requests = 0
            self._last_reset_date = current_date
        
        self._daily_requests += requests_used
        
        usage_data = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "operation": operation,
            "requests_used": requests_used,
            "daily_total": self._daily_requests,
            "daily_limit": daily_limit,
            "remaining": daily_limit - self._daily_requests,
            "usage_percentage": (self._daily_requests / daily_limit) * 100
        }
        
        # Use WARNING level if approaching quota (>80%)
        log_level = "WARNING" if usage_data["usage_percentage"] > 80 else "INFO"
        log_method = getattr(self.logger, log_level.lower())
        
        log_method(f"API_USAGE: {json.dumps(usage_data, separators=(',', ':'))}")
        
        # Log critical warning if quota exceeded
        if self._daily_requests >= daily_limit:
            self.logger.critical(f"QUOTA_EXCEEDED: Daily API limit of {daily_limit} requests reached!")
    
    def log_performance_metrics(self, symbol: str, metrics: Dict[str, Any]) -> None:
        """
        Log performance metrics for operations.
        
        Args:
            symbol: Stock symbol being processed
            metrics: Performance metrics dictionary
        """
        perf_data = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "metrics": metrics
        }
        
        self.logger.info(f"PERFORMANCE: {json.dumps(perf_data, separators=(',', ':'))}")
    
    def log_cache_operation(self, symbol: str, operation: str, hit: bool, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log cache operation (hit/miss) with metadata.
        
        Args:
            symbol: Stock symbol
            operation: Cache operation type
            hit: Whether it was a cache hit (True) or miss (False)
            metadata: Additional cache metadata
        """
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "operation": operation,
            "cache_hit": hit,
            "metadata": metadata or {}
        }
        
        self.logger.info(f"CACHE: {json.dumps(cache_data, separators=(',', ':'))}")
    
    def log_error(self, operation: str, symbol: str, error: Exception, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log error with structured format.
        
        Args:
            operation: Operation that failed
            symbol: Stock symbol being processed
            error: Exception that occurred
            metadata: Additional error context
        """
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "symbol": symbol,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "metadata": metadata or {}
        }
        
        self.logger.error(f"ERROR: {json.dumps(error_data, separators=(',', ':'))}")
    
    def get_daily_usage(self) -> Dict[str, int]:
        """
        Get current daily API usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        current_date = datetime.now().date()
        if current_date != self._last_reset_date:
            self._daily_requests = 0
            self._last_reset_date = current_date
        
        return {
            "date": current_date.isoformat(),
            "requests_used": self._daily_requests,
            "last_reset": self._last_reset_date.isoformat()
        }
    
    def reset_daily_usage(self) -> None:
        """Reset daily usage counter (for testing purposes)."""
        self._daily_requests = 0
        self._last_reset_date = datetime.now().date()
        self.logger.info("Daily usage counter reset")


class PerformanceTimer:
    """
    Context manager for timing operations and automatic logging.
    
    Usage:
        logger = APIUsageLogger()
        with PerformanceTimer(logger, "AAPL", "fetch_data"):
            # Operation to time
            data = fetch_data()
    """
    
    def __init__(self, logger: APIUsageLogger, symbol: str, operation: str):
        """
        Initialize performance timer.
        
        Args:
            logger: APIUsageLogger instance
            symbol: Stock symbol being processed
            operation: Operation name
        """
        self.logger = logger
        self.symbol = symbol
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log results."""
        if self.start_time is not None:
            elapsed_ms = (time.time() - self.start_time) * 1000
            
            metrics = {
                "operation": self.operation,
                "elapsed_ms": round(elapsed_ms, 2),
                "success": exc_type is None
            }
            
            if exc_type is not None:
                metrics["error_type"] = exc_type.__name__
            
            self.logger.log_performance_metrics(self.symbol, metrics)