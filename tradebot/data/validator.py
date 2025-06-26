"""
Data validator module for OHLCV market data validation.

This module provides the DataValidator class which handles:
- OHLCV data format validation
- Column presence verification
- Data type checking
- Chronological ordering validation
- Data integrity checks
"""

import pandas as pd
import numpy as np
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Validates OHLCV market data for format and integrity.
    
    This class ensures that market data meets required standards:
    - Contains all required OHLCV columns
    - Has proper numeric data types
    - Maintains chronological date ordering
    - Passes basic integrity checks
    """
    
    REQUIRED_COLUMNS = ['open', 'high', 'low', 'close', 'volume']
    NUMERIC_COLUMNS = ['open', 'high', 'low', 'close', 'volume']
    
    def __init__(self):
        """Initialize DataValidator."""
        logger.info("DataValidator initialized")
    
    def validate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Validate OHLCV data format and integrity.
        
        Args:
            data: DataFrame containing OHLCV data
            
        Returns:
            pd.DataFrame: Validated data (same as input if valid)
            
        Raises:
            ValidationError: If data fails any validation checks
        """
        if data is None or data.empty:
            from tradebot.exceptions import ValidationError
            raise ValidationError("Data is empty or None")
        
        # Check required columns
        self._validate_columns(data)
        
        # Check data types
        self._validate_data_types(data)
        
        # Check chronological ordering
        self._validate_chronological_order(data)
        
        logger.info(f"Successfully validated {len(data)} records")
        return data
    
    def _validate_columns(self, data: pd.DataFrame) -> None:
        """Validate that all required columns are present."""
        missing_columns = []
        for col in self.REQUIRED_COLUMNS:
            if col not in data.columns:
                missing_columns.append(col)
        
        if missing_columns:
            from tradebot.exceptions import ValidationError
            raise ValidationError(f"Missing required columns: {missing_columns}")
    
    def _validate_data_types(self, data: pd.DataFrame) -> None:
        """Validate that numeric columns contain valid numeric data."""
        for col in self.NUMERIC_COLUMNS:
            if col in data.columns:
                # Check if column can be converted to numeric
                try:
                    pd.to_numeric(data[col], errors='raise')
                except (ValueError, TypeError) as e:
                    from tradebot.exceptions import ValidationError
                    raise ValidationError(f"Column '{col}' contains non-numeric data: {e}")
    
    def _validate_chronological_order(self, data: pd.DataFrame) -> None:
        """Validate that data is in chronological order."""
        if not isinstance(data.index, pd.DatetimeIndex):
            # Try to convert index to datetime if possible
            try:
                data.index = pd.to_datetime(data.index)
            except (ValueError, TypeError):
                from tradebot.exceptions import ValidationError
                raise ValidationError("Index is not a valid datetime index")
        
        # Check if dates are in chronological order
        if not data.index.is_monotonic_increasing:
            from tradebot.exceptions import ValidationError
            raise ValidationError("Data is not in chronological order")