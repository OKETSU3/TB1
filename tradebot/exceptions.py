"""
Custom exceptions for the tradebot package.

This module defines all custom exceptions used throughout the application
for consistent error handling and meaningful error messages.
"""


class TradebotError(Exception):
    """Base exception for all tradebot-related errors."""
    pass


class DataFetchError(TradebotError):
    """Raised when data fetching from external APIs fails."""
    pass


class InvalidSymbolError(TradebotError):
    """Raised when an invalid stock symbol is provided."""
    pass


class ValidationError(TradebotError):
    """Raised when data validation fails."""
    pass


class QuotaExceededError(TradebotError):
    """Raised when API quota limits are exceeded."""
    pass


class ConfigurationError(TradebotError):
    """Raised when configuration loading or validation fails."""
    pass


class CacheError(TradebotError):
    """Raised when cache operations fail."""
    pass