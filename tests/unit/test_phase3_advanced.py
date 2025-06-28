"""
Test Phase 3: Advanced Features Validation

This module contains comprehensive tests for Phase 3 advanced features:
- T3.1: Data freshness testing (Cache invalidation and market hours)
- T3.2: Batch processing validation (Multi-symbol with quota management)
- T3.3: Performance optimization testing (Large dataset handling)
- T3.4: Error recovery validation (Retry mechanisms and fallback)

All tests follow TDD principles with 0 API requests (complete mocking required).
"""

import pytest
import pandas as pd
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from freezegun import freeze_time


class TestDataFreshness:
    """T3.1 Data Freshness Testing (Cache Invalidation and Market Hours)"""
    
    @pytest.fixture
    def test_cache(self, tmp_path):
        """Create test cache with temporary database"""
        cache_db = tmp_path / "test_freshness_cache.db"
        from tradebot.data.cache import DataCache
        return DataCache(database_path=str(cache_db))
    
    @pytest.fixture
    def sample_data(self):
        """Sample OHLCV data for freshness testing"""
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        return pd.DataFrame({
            'open': [150.0, 151.0, 152.0, 153.0, 154.0],
            'high': [155.0, 156.0, 157.0, 158.0, 159.0],
            'low': [149.0, 150.0, 151.0, 152.0, 153.0],
            'close': [154.0, 155.0, 156.0, 157.0, 158.0],
            'volume': [1000000, 1100000, 1200000, 1300000, 1400000]
        }, index=dates)
    
    @pytest.fixture
    def freshness_manager(self, test_cache):
        """Create FreshnessManager instance for testing"""
        from tradebot.data.freshness import FreshnessManager
        return FreshnessManager(cache=test_cache)
    
    def test_t3_1_cache_age_calculation(self, freshness_manager, test_cache, sample_data):
        """Test cache age calculation for freshness validation"""
        # Store data
        test_cache.store("AAPL", "2024-01-01", "2024-01-05", sample_data)
        
        # Check age immediately after storage (should be fresh)
        age_minutes = freshness_manager.get_cache_age("AAPL", "2024-01-01", "2024-01-05")
        assert age_minutes < 1.0  # Less than 1 minute old
        
        # Test age calculation
        assert isinstance(age_minutes, float)
        assert age_minutes >= 0
    
    @freeze_time("2024-01-15 14:30:00")  # Market open time (UTC - EST is UTC-5, so 9:30 AM EST = 14:30 UTC)
    def test_t3_1_market_hours_detection(self, freshness_manager):
        """Test market hours detection for freshness logic"""
        # Test during market hours (Monday 9:30 AM EST)
        is_market_open = freshness_manager.is_market_open()
        assert is_market_open == True
        
        # Test market open time validation
        market_open = freshness_manager.get_market_open_time()
        assert market_open.hour == 9
        assert market_open.minute == 30
    
    @freeze_time("2024-01-15 23:30:00")  # After market close (6:30 PM EST = 23:30 UTC)
    def test_t3_1_after_market_hours_detection(self, freshness_manager):
        """Test after-hours detection"""
        is_market_open = freshness_manager.is_market_open()
        assert is_market_open == False
    
    @freeze_time("2024-01-13 10:00:00")  # Weekend (Saturday)
    def test_t3_1_weekend_detection(self, freshness_manager):
        """Test weekend market closure detection"""
        is_market_open = freshness_manager.is_market_open()
        assert is_market_open == False
        
        is_weekend = freshness_manager.is_weekend()
        assert is_weekend == True
    
    def test_t3_1_configurable_freshness_thresholds(self, freshness_manager, test_cache, sample_data):
        """Test configurable data freshness thresholds"""
        # Store data
        test_cache.store("AAPL", "2024-01-01", "2024-01-05", sample_data)
        
        # Test different freshness thresholds
        is_fresh_1min = freshness_manager.is_data_fresh("AAPL", "2024-01-01", "2024-01-05", threshold_minutes=1)
        is_fresh_1hour = freshness_manager.is_data_fresh("AAPL", "2024-01-01", "2024-01-05", threshold_minutes=60)
        
        # Data should be fresh for both thresholds immediately after storage
        assert is_fresh_1min == True
        assert is_fresh_1hour == True
    
    def test_t3_1_cache_invalidation_logic(self, freshness_manager, test_cache, sample_data):
        """Test cache invalidation based on data age"""
        # Store data
        test_cache.store("AAPL", "2024-01-01", "2024-01-05", sample_data)
        
        # Simulate data aging (mock the cache metadata to appear old)
        with patch.object(test_cache, 'get_metadata') as mock_metadata:
            old_time = datetime.now() - timedelta(hours=25)  # 25 hours old
            mock_metadata.return_value = {
                'cache_key': 'AAPL_2024-01-01_2024-01-05',
                'symbol': 'AAPL',
                'created_at': old_time.isoformat(),
                'record_count': 5,
                'data_size_bytes': 1024
            }
            
            # Check if data should be invalidated (25 hours > 24 hour threshold)
            should_invalidate = freshness_manager.should_invalidate_cache("AAPL", "2024-01-01", "2024-01-05")
            assert should_invalidate == True
    
    def test_t3_1_cache_cleanup_old_data(self, freshness_manager, test_cache, sample_data):
        """Test cache cleanup for old data"""
        # Store data
        test_cache.store("AAPL", "2024-01-01", "2024-01-05", sample_data)
        test_cache.store("MSFT", "2024-01-01", "2024-01-05", sample_data)
        
        # Initial count
        initial_stats = test_cache.get_cache_stats()
        initial_count = initial_stats['total_records']
        
        # Cleanup data older than 0 days (should remove everything)
        cleaned_count = freshness_manager.cleanup_old_cache(days_to_keep=0)
        
        # Verify cleanup occurred
        assert cleaned_count > 0
        
        # Verify data was actually removed
        final_stats = test_cache.get_cache_stats()
        assert final_stats['total_records'] < initial_count


class TestBatchProcessing:
    """T3.2 Batch Processing Validation (Multi-symbol with Quota Management)"""
    
    @pytest.fixture
    def batch_processor(self, tmp_path):
        """Create BatchProcessor instance for testing"""
        from tradebot.data.batch import BatchProcessor
        from tradebot.config.manager import ConfigManager
        from tradebot.utils.rate_limiter import RateLimiter
        from tradebot.data.cache import DataCache
        
        # Create test dependencies
        config = ConfigManager()
        rate_limiter = RateLimiter(daily_limit=10, storage_path=str(tmp_path / "quota.db"))
        cache = DataCache(database_path=str(tmp_path / "cache.db"))
        
        return BatchProcessor(config=config, rate_limiter=rate_limiter, cache=cache)
    
    def test_t3_2_quota_aware_batch_sizing(self, batch_processor):
        """Test intelligent batch sizing based on remaining quota"""
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        
        # Test with limited quota remaining
        with patch.object(batch_processor.rate_limiter, 'get_usage') as mock_usage:
            mock_usage.return_value = {
                'used': 7,
                'limit': 10,
                'remaining': 3
            }
            
            # Calculate optimal batch size
            batch_size = batch_processor.calculate_optimal_batch_size(symbols)
            
            # Should not exceed remaining quota
            assert batch_size <= 3
            assert batch_size > 0
    
    def test_t3_2_sequential_processing_order(self, batch_processor):
        """Test sequential (not parallel) processing to avoid quota burst"""
        symbols = ["AAPL", "MSFT", "GOOGL"]
        
        with patch.object(batch_processor, '_fetch_single_symbol') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame({
                'open': [100.0], 'high': [105.0], 'low': [99.0], 
                'close': [103.0], 'volume': [1000000]
            })
            
            # Process batch
            results = batch_processor.fetch_multiple_symbols(symbols, "2024-01-01", "2024-01-02")
            
            # Verify sequential calls (call count should equal symbol count)
            assert mock_fetch.call_count == len(symbols)
            
            # Verify results structure
            assert isinstance(results, dict)
            assert len(results) == len(symbols)
    
    def test_t3_2_quota_calculation_accuracy(self, batch_processor):
        """Test accurate quota calculation for multiple symbols"""
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        
        # Calculate total requests needed
        total_requests = batch_processor.calculate_total_requests_needed(symbols)
        
        # Each symbol requires 1 request
        assert total_requests == len(symbols)
        assert isinstance(total_requests, int)
    
    def test_t3_2_batch_error_handling(self, batch_processor):
        """Test error handling in batch processing"""
        symbols = ["AAPL", "INVALID_SYMBOL", "MSFT"]
        
        with patch.object(batch_processor, '_fetch_single_symbol') as mock_fetch:
            # First call succeeds, second fails, third succeeds
            def side_effect(symbol, start_date, end_date):
                if symbol == "INVALID_SYMBOL":
                    from tradebot.exceptions import InvalidSymbolError
                    raise InvalidSymbolError(f"Invalid symbol: {symbol}")
                return pd.DataFrame({
                    'open': [100.0], 'high': [105.0], 'low': [99.0], 
                    'close': [103.0], 'volume': [1000000]
                })
            
            mock_fetch.side_effect = side_effect
            
            # Process batch with error handling
            results = batch_processor.fetch_multiple_symbols(symbols, "2024-01-01", "2024-01-02")
            
            # Should return results for successful symbols only
            assert "AAPL" in results
            assert "MSFT" in results
            assert "INVALID_SYMBOL" not in results
    
    def test_t3_2_bulk_database_operations(self, batch_processor):
        """Test optimized bulk database operations"""
        symbols = ["AAPL", "MSFT"]
        sample_data = {
            "AAPL": pd.DataFrame({
                'open': [150.0], 'high': [155.0], 'low': [149.0], 
                'close': [154.0], 'volume': [1000000]
            }),
            "MSFT": pd.DataFrame({
                'open': [300.0], 'high': [305.0], 'low': [299.0], 
                'close': [304.0], 'volume': [2000000]
            })
        }
        
        # Test bulk storage operation
        stored_count = batch_processor.bulk_store_results(sample_data, "2024-01-01", "2024-01-02")
        
        # Verify bulk storage
        assert stored_count == len(symbols)


class TestPerformanceOptimization:
    """T3.3 Performance Optimization Testing (Large Dataset Handling)"""
    
    @pytest.fixture
    def performance_optimizer(self, tmp_path):
        """Create PerformanceOptimizer instance for testing"""
        from tradebot.data.performance import PerformanceOptimizer
        from tradebot.data.cache import DataCache
        
        cache = DataCache(database_path=str(tmp_path / "perf_cache.db"))
        return PerformanceOptimizer(cache=cache)
    
    @pytest.fixture
    def large_dataset(self):
        """Create large dataset for performance testing"""
        # Create 1 year of daily data (252 trading days)
        dates = pd.date_range('2024-01-01', periods=252, freq='D')
        return pd.DataFrame({
            'open': [150.0 + i * 0.1 for i in range(252)],
            'high': [155.0 + i * 0.1 for i in range(252)],
            'low': [149.0 + i * 0.1 for i in range(252)],
            'close': [154.0 + i * 0.1 for i in range(252)],
            'volume': [1000000 + i * 1000 for i in range(252)]
        }, index=dates)
    
    def test_t3_3_query_optimization(self, performance_optimizer):
        """Test database query optimization"""
        # Test optimized query generation
        optimized_query = performance_optimizer.build_optimized_query(
            symbol="AAPL",
            start_date="2024-01-01",
            end_date="2024-12-31"
        )
        
        # Verify query optimization features
        assert optimized_query is not None
        # Query should include proper indexing hints
        assert hasattr(optimized_query, 'use_index') or hasattr(optimized_query, 'where')
    
    def test_t3_3_memory_usage_monitoring(self, performance_optimizer, large_dataset):
        """Test memory usage monitoring during large operations"""
        # Monitor memory during large dataset processing
        memory_stats = performance_optimizer.monitor_memory_usage(
            lambda: performance_optimizer.process_large_dataset(large_dataset)
        )
        
        # Verify memory monitoring
        assert 'peak_memory_mb' in memory_stats
        assert 'avg_memory_mb' in memory_stats
        assert memory_stats['peak_memory_mb'] > 0
    
    def test_t3_3_data_streaming(self, performance_optimizer, large_dataset):
        """Test data streaming for large time ranges"""
        # Test streaming large dataset in chunks
        chunk_size = 50
        chunks = list(performance_optimizer.stream_data_chunks(large_dataset, chunk_size=chunk_size))
        
        # Verify streaming
        assert len(chunks) > 0
        assert all(len(chunk) <= chunk_size for chunk in chunks)
        
        # Verify all data is included
        total_rows = sum(len(chunk) for chunk in chunks)
        assert total_rows == len(large_dataset)
    
    def test_t3_3_performance_benchmarking(self, performance_optimizer, large_dataset):
        """Test performance benchmarking utilities"""
        # Benchmark large dataset operations
        benchmark_results = performance_optimizer.benchmark_operation(
            operation_name="large_dataset_processing",
            operation=lambda: performance_optimizer.process_large_dataset(large_dataset),
            iterations=3
        )
        
        # Verify benchmark results
        assert 'avg_time_ms' in benchmark_results
        assert 'min_time_ms' in benchmark_results
        assert 'max_time_ms' in benchmark_results
        assert benchmark_results['avg_time_ms'] > 0
    
    def test_t3_3_cache_hit_rate_optimization(self, performance_optimizer):
        """Test cache hit rate optimization"""
        # Test cache hit rate calculation
        hit_rate = performance_optimizer.calculate_cache_hit_rate(
            total_requests=100,
            cache_hits=85
        )
        
        assert hit_rate == 85.0
        assert isinstance(hit_rate, float)
        
        # Test hit rate optimization recommendations
        recommendations = performance_optimizer.get_optimization_recommendations(hit_rate)
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0


class TestErrorRecovery:
    """T3.4 Error Recovery Validation (Retry Mechanisms and Fallback)"""
    
    @pytest.fixture
    def error_recovery(self, tmp_path):
        """Create ErrorRecovery instance for testing"""
        from tradebot.data.recovery import ErrorRecovery
        from tradebot.utils.rate_limiter import RateLimiter
        
        rate_limiter = RateLimiter(daily_limit=10, storage_path=str(tmp_path / "quota.db"))
        return ErrorRecovery(rate_limiter=rate_limiter)
    
    def test_t3_4_exponential_backoff(self, error_recovery):
        """Test exponential backoff for API failures"""
        # Test backoff calculation
        backoff_times = []
        for attempt in range(1, 6):
            backoff_time = error_recovery.calculate_backoff_time(attempt)
            backoff_times.append(backoff_time)
        
        # Verify exponential increase
        assert all(backoff_times[i] < backoff_times[i+1] for i in range(len(backoff_times)-1))
        assert backoff_times[0] >= 1.0  # At least 1 second for first retry
        assert backoff_times[-1] <= 60.0  # Max 60 seconds
    
    def test_t3_4_retry_mechanism(self, error_recovery):
        """Test retry mechanism with exponential backoff"""
        call_count = 0
        
        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "Success"
        
        # Test retry mechanism
        result = error_recovery.retry_with_backoff(
            operation=failing_operation,
            max_retries=3,
            exceptions=(ConnectionError,)
        )
        
        assert result == "Success"
        assert call_count == 3  # Should have retried 2 times before success
    
    def test_t3_4_partial_data_recovery(self, error_recovery):
        """Test partial data recovery when some requests fail"""
        symbols = ["AAPL", "MSFT", "INVALID", "GOOGL"]
        
        def fetch_with_failures(symbol):
            if symbol == "INVALID":
                raise ValueError(f"Invalid symbol: {symbol}")
            return pd.DataFrame({
                'open': [100.0], 'high': [105.0], 'low': [99.0], 
                'close': [103.0], 'volume': [1000000]
            })
        
        # Test partial recovery
        results, errors = error_recovery.fetch_with_partial_recovery(
            symbols=symbols,
            fetch_function=fetch_with_failures
        )
        
        # Verify partial recovery
        assert len(results) == 3  # 3 successful symbols
        assert len(errors) == 1   # 1 failed symbol
        assert "AAPL" in results
        assert "MSFT" in results
        assert "GOOGL" in results
        assert "INVALID" in errors
    
    def test_t3_4_circuit_breaker_pattern(self, error_recovery):
        """Test circuit breaker pattern for API health monitoring"""
        # Test circuit breaker states
        assert error_recovery.circuit_breaker.state == "CLOSED"  # Initial state
        
        # Simulate failures to trigger circuit breaker
        for _ in range(5):
            error_recovery.circuit_breaker.record_failure()
        
        # Circuit should be open after multiple failures
        assert error_recovery.circuit_breaker.state == "OPEN"
        
        # Test if circuit breaker prevents calls
        should_allow_call = error_recovery.circuit_breaker.should_allow_call()
        assert should_allow_call == False
    
    def test_t3_4_fallback_cached_data(self, error_recovery, tmp_path):
        """Test fallback to cached data when API fails"""
        from tradebot.data.cache import DataCache
        
        # Setup cache with fallback data
        cache = DataCache(database_path=str(tmp_path / "fallback_cache.db"))
        fallback_data = pd.DataFrame({
            'open': [150.0], 'high': [155.0], 'low': [149.0], 
            'close': [154.0], 'volume': [1000000]
        })
        cache.store("AAPL", "2024-01-01", "2024-01-02", fallback_data)
        
        error_recovery.cache = cache
        
        def failing_api_call():
            raise ConnectionError("API unavailable")
        
        # Test fallback to cached data
        result = error_recovery.get_data_with_fallback(
            symbol="AAPL",
            start_date="2024-01-01",
            end_date="2024-01-02",
            api_function=failing_api_call
        )
        
        # Should return cached data as fallback
        assert result is not None
        assert len(result) == 1
        assert result['close'].iloc[0] == 154.0
    
    def test_t3_4_recovery_strategy_selection(self, error_recovery):
        """Test automatic recovery strategy selection"""
        # Test strategy selection based on error type
        connection_error_strategy = error_recovery.select_recovery_strategy(ConnectionError("Network down"))
        timeout_error_strategy = error_recovery.select_recovery_strategy(TimeoutError("Request timeout"))
        quota_error_strategy = error_recovery.select_recovery_strategy(Exception("Quota exceeded"))
        
        # Verify different strategies for different error types
        assert connection_error_strategy == "retry_with_backoff"
        assert timeout_error_strategy == "retry_with_backoff"
        assert quota_error_strategy == "fallback_to_cache"