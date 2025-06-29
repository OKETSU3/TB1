"""
Custom exceptions for the tradebot package.

This module defines basic custom exceptions for the initial project structure.
Additional exceptions will be added as features are implemented.
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