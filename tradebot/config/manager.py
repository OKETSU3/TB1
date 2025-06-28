"""
Configuration manager module for handling YAML configuration files and environment overrides.

This module provides the ConfigManager class which handles:
- YAML configuration file loading and parsing
- Environment variable overrides
- Default value management
- Configuration validation
"""

import yaml
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages application configuration from YAML files with environment variable overrides.
    
    This class provides centralized configuration management:
    - Loads configuration from YAML files
    - Supports environment variable overrides
    - Provides default values for missing configuration
    - Validates configuration format and values
    """
    
    DEFAULT_CONFIG = {
        'api': {
            'timeout': 30,
            'retry_count': 3,
            'daily_limit': 800
        },
        'cache': {
            'freshness_hours': 24,
            'max_size_mb': 100
        }
    }
    
    ENV_MAPPING = {
        'TWELVE_DATA_TIMEOUT': ('api', 'timeout'),
        'TWELVE_DATA_RETRY_COUNT': ('api', 'retry_count'),
        'TWELVE_DATA_DAILY_LIMIT': ('api', 'daily_limit'),
        'CACHE_FRESHNESS_HOURS': ('cache', 'freshness_hours'),
        'CACHE_MAX_SIZE_MB': ('cache', 'max_size_mb')
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize ConfigManager with optional configuration file path.
        
        Args:
            config_path: Path to YAML configuration file
            
        Raises:
            ConfigurationError: If configuration file cannot be loaded or parsed
        """
        self.config_path = config_path
        self.config = self._load_config()
        logger.info("ConfigManager initialized successfully")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file and apply environment overrides."""
        # Start with default configuration
        config = self._deep_copy_dict(self.DEFAULT_CONFIG)
        
        # Load from file if provided
        if self.config_path:
            file_config = self._load_config_file()
            config = self._merge_configs(config, file_config)
        
        # Apply environment variable overrides
        config = self._apply_env_overrides(config)
        
        # Validate final configuration
        self._validate_config(config)
        
        return config
    
    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            from tradebot.exceptions import ConfigurationError
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if config is None:
                config = {}
            
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
            
        except yaml.YAMLError as e:
            from tradebot.exceptions import ConfigurationError
            raise ConfigurationError(f"Invalid YAML format in {self.config_path}: {e}")
        except Exception as e:
            from tradebot.exceptions import ConfigurationError
            raise ConfigurationError(f"Failed to load configuration from {self.config_path}: {e}")
    
    def _merge_configs(self, base_config: Dict[str, Any], file_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge file configuration into base configuration."""
        merged = self._deep_copy_dict(base_config)
        
        for section, values in file_config.items():
            if section in merged and isinstance(values, dict):
                merged[section].update(values)
            else:
                merged[section] = values
        
        return merged
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        for env_var, (section, key) in self.ENV_MAPPING.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Try to convert to appropriate type
                    if key in ['timeout', 'retry_count', 'daily_limit', 'freshness_hours', 'max_size_mb']:
                        env_value = int(env_value)
                    
                    if section not in config:
                        config[section] = {}
                    
                    config[section][key] = env_value
                    logger.info(f"Applied environment override: {env_var} -> {section}.{key} = {env_value}")
                    
                except ValueError as e:
                    from tradebot.exceptions import ConfigurationError
                    raise ConfigurationError(f"Invalid value for environment variable {env_var}: {env_value}")
        
        return config
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration values."""
        # Validate API section
        if 'api' in config:
            api_config = config['api']
            
            if 'timeout' in api_config and api_config['timeout'] <= 0:
                from tradebot.exceptions import ConfigurationError
                raise ConfigurationError("API timeout must be positive")
            
            if 'retry_count' in api_config and api_config['retry_count'] < 0:
                from tradebot.exceptions import ConfigurationError
                raise ConfigurationError("API retry_count must be non-negative")
            
            if 'daily_limit' in api_config and api_config['daily_limit'] <= 0:
                from tradebot.exceptions import ConfigurationError
                raise ConfigurationError("API daily_limit must be positive")
        
        # Validate cache section
        if 'cache' in config:
            cache_config = config['cache']
            
            if 'freshness_hours' in cache_config and cache_config['freshness_hours'] <= 0:
                from tradebot.exceptions import ConfigurationError
                raise ConfigurationError("Cache freshness_hours must be positive")
            
            if 'max_size_mb' in cache_config and cache_config['max_size_mb'] <= 0:
                from tradebot.exceptions import ConfigurationError
                raise ConfigurationError("Cache max_size_mb must be positive")
    
    def _deep_copy_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deep copy of a dictionary."""
        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = self._deep_copy_dict(value)
            else:
                result[key] = value
        return result
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the complete configuration dictionary.
        
        Returns:
            Dict containing all configuration values
        """
        return self.config
    
    def get_api_config(self) -> Dict[str, Any]:
        """
        Get API-specific configuration.
        
        Returns:
            Dict containing API configuration values
        """
        return self.config.get('api', {})
    
    def get_cache_config(self) -> Dict[str, Any]:
        """
        Get cache-specific configuration.
        
        Returns:
            Dict containing cache configuration values
        """
        return self.config.get('cache', {})
    
    def get_daily_limit(self) -> int:
        """
        Get the daily API request limit.
        
        Returns:
            Daily API request limit
        """
        return self.config.get('api', {}).get('daily_limit', 800)
    
    def get_timeout(self) -> int:
        """
        Get the API timeout value.
        
        Returns:
            API timeout in seconds
        """
        return self.config.get('api', {}).get('timeout', 30)