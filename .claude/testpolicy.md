# Test Policy and Guidelines (Twelve Data Collection Module)

## Purpose and Scope

This document establishes comprehensive guidelines for creating and maintaining testtasks.md, which provides phase-by-phase test implementation tasks that run in tandem with the main tasks.md implementation. The goal is to create a unified, manageable testing workflow that ensures quality while protecting API quota usage.

### Policy Objectives
- **Unified Test Management**: Single document combining test cases and implementation
- **Implementation Synchronization**: Seamless coordination between tasks.md and testtasks.md
- **API Quota Protection**: Strict guidelines to prevent exceeding Twelve Data free tier limits
- **Quality Assurance**: Comprehensive testing coverage with consistent quality standards
- **Development Efficiency**: Streamlined test creation and execution processes

### Target Audience
- Development team implementing the data collection module
- QA engineers validating functionality
- Future maintainers understanding test strategy
- AI assistants implementing test tasks

---

## Test Strategy Framework

### Implementation-Test Cycle Approach
The development process follows a strict alternating pattern:

1. **Implementation Phase**: Complete tasks from tasks.md
2. **Validation Phase**: Execute corresponding tests from testtasks.md
3. **Verification Phase**: Confirm all tests pass before proceeding
4. **Integration Phase**: Ensure new functionality integrates properly
5. **Documentation Phase**: Update test results and progress tracking

### Phase-Based Testing Strategy
Each main implementation phase has corresponding test phases:

- **Phase 1 Implementation** → **Phase 1 Test Suite**
- **Phase 2 Implementation** → **Phase 2 Test Suite**
- **Phase 3 Implementation** → **Phase 3 Test Suite**
- **Phase 4 Implementation** → **Phase 4 Test Suite**

### Test Coverage Requirements
- **Unit Tests**: 95%+ code coverage for core functionality
- **Integration Tests**: End-to-end workflow validation with minimal API usage
- **Error Handling**: Comprehensive failure scenario coverage
- **Performance Tests**: Response time and memory usage validation

---

## testtasks.md Structure Guidelines

### Document Format
Follow the established format pattern from tasks.md with test-specific adaptations:

```markdown
# Test Implementation Tasks (Twelve Data Collection Module)

## Purpose and Scope
[Test-specific purpose statement]

### Test Objectives
[Specific testing goals]

### API Quota Management
[Quota protection strategies]

---

## Test Phase Overview
[Mirror the phase structure from tasks.md]

---

## Detailed Test Task Breakdown

### Test Phase X: [Phase Name]

#### TX.X [Test Task Name]
- **Goal**: [What this test validates]
- **Implementation**: [Test setup and execution steps]
- **Verification**: [Success criteria]
- **API Quota Usage**: [Exact number of requests, 0 for mocked tests]
- **Dependencies**: [Required completions from tasks.md]
- **Test Data**: [Required test fixtures and mock data]
- **Time Required**: [Realistic execution time estimate]
```

### Test Task Naming Convention
- **Prefix**: "T" for Test followed by phase number
- **Format**: TX.Y where X = Phase number, Y = Task number
- **Example**: T1.2 = Test Phase 1, Task 2
- **Correlation**: T1.2 tests the implementation from task 1.2

### Test Implementation Requirements
Each test task must include:

1. **Comprehensive Test Code**: Complete, runnable pytest implementation
2. **Mock Setup**: Detailed mock configuration to avoid API usage
3. **Test Data**: Sample datasets and expected responses
4. **Error Scenarios**: Both positive and negative test cases
5. **Performance Benchmarks**: Expected execution times and resource usage

---

## API Quota Management Policy

### Critical Constraints
- **Daily Limit**: 800 requests per day (Twelve Data free tier)
- **Test Budget**: Maximum 50 requests per day for all testing combined
- **Unit Test Budget**: 0 requests (must be fully mocked)
- **Integration Test Budget**: Maximum 10 requests per test run
- **Development Test Budget**: Maximum 40 requests for manual testing

### Quota Protection Strategies

#### Mandatory Mocking
All unit tests MUST use mocks:
```python
@patch('tradebot.data.fetcher.TDClient')
def test_function(mock_td_client):
    # Configure comprehensive mock response
    mock_client_instance = Mock()
    mock_td_client.return_value = mock_client_instance
    # Test implementation with zero API usage
```

#### Integration Test Limits
```python
# Maximum 2-3 real API calls per integration test
class TestIntegration:
    @pytest.mark.integration
    @pytest.mark.quota_usage(requests=2)
    def test_real_api_integration(self):
        # Limited real API testing
```

#### Quota Tracking Implementation
```python
# Mandatory quota tracking in all tests
def test_with_quota_tracking():
    initial_usage = quota_tracker.get_daily_usage()
    # Test execution
    final_usage = quota_tracker.get_daily_usage()
    assert final_usage - initial_usage <= expected_usage
```

---

## Test Quality Standards

### Code Quality Requirements
- **pytest Framework**: All tests use pytest with consistent patterns
- **Type Hints**: All test functions include proper type annotations
- **Docstrings**: Clear documentation for complex test scenarios
- **Error Handling**: Proper exception testing and validation
- **Test Isolation**: Each test is independent and doesn't affect others

### Test Data Standards
```python
# Standardized test data format
SAMPLE_OHLCV_DATA = {
    'symbol': 'AAPL',
    'data': pd.DataFrame({
        'open': [150.0, 151.0, 152.0],
        'high': [155.0, 156.0, 157.0],
        'low': [149.0, 150.0, 151.0],
        'close': [154.0, 155.0, 156.0],
        'volume': [1000000, 1100000, 1200000]
    }),
    'date_range': ('2024-01-01', '2024-01-03')
}
```

### Performance Standards
- **Unit Test Execution**: < 1 second per test
- **Integration Test Execution**: < 10 seconds per test
- **Total Test Suite**: < 5 minutes for complete run
- **Memory Usage**: < 100MB peak usage during testing

---

## Implementation Synchronization Process

### Phase Completion Workflow
1. **Complete Implementation Task**: Finish corresponding task from tasks.md
2. **Update Progress**: Mark implementation task as completed
3. **Execute Test Task**: Run corresponding test from testtasks.md
4. **Validate Results**: Ensure all tests pass with expected coverage
5. **Update Test Status**: Mark test task as completed
6. **Proceed to Next**: Move to next implementation task

### Dependency Management
```markdown
#### T1.2 Basic Data Fetcher Testing
- **Dependencies**: 
  - Task 1.1 (Project Structure) completed ✓
  - Task 1.2 (DataFetcher Implementation) completed ✓
- **Blocks**: Task 1.3 implementation until T1.2 tests pass
```

### Failure Handling Protocol
1. **Test Failure Detection**: Identify failing test cases
2. **Root Cause Analysis**: Determine if issue is implementation or test
3. **Implementation Fix**: Correct implementation if needed
4. **Test Update**: Adjust test if requirements changed
5. **Re-validation**: Run tests until all pass
6. **Documentation**: Record issues and resolutions

---

## Test Environment Guidelines

### Development Environment Setup
```bash
# Required test dependencies
pip install pytest pytest-cov pytest-mock requests-mock freezegun

# Test environment configuration
export TESTING=true
export TWELVE_DATA_API_KEY="test_key_for_development"
export LOG_LEVEL=DEBUG
```

### Test Directory Structure
```
tests/
├── conftest.py                 # Global test configuration
├── unit/                       # Unit tests (0 API usage)
│   ├── test_phase1.py
│   ├── test_phase2.py
│   └── ...
├── integration/                # Integration tests (limited API usage)
│   ├── test_integration.py
│   └── ...
├── fixtures/                   # Test data and mocks
│   ├── sample_data.py
│   ├── mock_responses.py
│   └── ...
└── utils/                      # Test utilities
    ├── quota_tracker.py
    ├── mock_helpers.py
    └── ...
```

### Mock Data Management
```python
# Centralized mock response library
class MockResponses:
    TWELVE_DATA_SUCCESS = {
        "meta": {"symbol": "AAPL", "interval": "1day"},
        "values": [{"datetime": "2024-01-01", "open": "150.00", ...}]
    }
    
    TWELVE_DATA_ERROR = {
        "code": 400,
        "message": "Invalid symbol",
        "status": "error"
    }
```

---

## Continuous Integration Guidelines

### Automated Test Execution
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    steps:
    - name: Run Unit Tests
      run: pytest tests/unit/ --cov=tradebot
    - name: Run Limited Integration Tests
      run: pytest tests/integration/ -m "not quota_heavy"
    - name: Check API Usage
      run: python tests/utils/quota_checker.py
```

### Quality Gates
- **Code Coverage**: Minimum 95% for unit tests
- **Test Execution**: All tests must pass consistently
- **API Usage**: Zero quota usage in CI/CD pipeline
- **Performance**: Test execution within time limits

---

## testtasks.md Creation Template

### Phase Task Template
```markdown
#### TX.Y [Test Task Name] ([Brief Description])
- **Goal**: [Specific validation objective]
- **Implementation**: [Test setup and execution steps]
  - Setup test environment with mocks
  - Configure test data and fixtures
  - Execute test scenarios (positive and negative)
  - Validate results and error handling
- **API Quota Usage**: [0 for unit tests, limited number for integration]
- **Verification**: [How to confirm test success]
- **Test Code**: [Complete pytest implementation]
- **Dependencies**: [Required tasks.md completions]
- **Time Required**: [Execution time estimate]
- **Risks**: [Potential testing challenges]
```

### Test Code Integration
```markdown
```python
# Complete test implementation
import pytest
from unittest.mock import Mock, patch

class TestPhaseX:
    def test_tx_y_feature_validation(self, fixtures):
        # Comprehensive test implementation
        pass
```
```

---

## Progress Tracking and Reporting

### Test Status Management
- **Not Started**: Test task defined but not implemented
- **In Progress**: Test implementation underway
- **Completed**: All tests pass consistently
- **Failed**: Tests identify issues requiring fixes
- **Blocked**: Waiting on implementation dependencies

### Test Metrics Tracking
```markdown
### Test Progress Dashboard
- **Phase 1**: 4/4 tests completed (100%)
- **Phase 2**: 2/5 tests completed (40%)
- **API Quota Used**: 15/800 requests (1.9%)
- **Coverage**: 94% (target: 95%+)
- **Performance**: All tests < 1s (✓)
```

### Issue Resolution Tracking
```markdown
### Test Issues Log
- **Issue T2.3.1**: Rate limiter test failing
  - **Status**: Resolved
  - **Resolution**: Updated mock configuration
  - **Date**: 2024-06-22
```

---

## Best Practices and Anti-Patterns

### Testing Best Practices
1. **Test Independence**: Each test runs in isolation
2. **Clear Naming**: Test names describe exactly what is being validated
3. **Comprehensive Mocking**: Mock all external dependencies completely
4. **Data Consistency**: Use standardized test data across all tests
5. **Error Coverage**: Test both success and failure scenarios

### Anti-Patterns to Avoid
1. **Real API Calls in Unit Tests**: Never use actual API in unit tests
2. **Test Dependencies**: Tests should not depend on each other
3. **Hardcoded Values**: Use fixtures and configuration for test data
4. **Insufficient Mocking**: Partial mocks that might still trigger API calls
5. **Ignored Test Failures**: All test failures must be addressed

### Quota Protection Anti-Patterns
```python
# WRONG: Real API call in unit test
def test_fetch_data():
    fetcher = DataFetcher()
    data = fetcher.fetch_historical_data("AAPL", ...)  # Uses quota!

# CORRECT: Mocked API call
@patch('tradebot.data.fetcher.TDClient')
def test_fetch_data(mock_client):
    mock_client.return_value.time_series.return_value.as_pandas.return_value = mock_data
    # Test implementation with zero quota usage
```

---

## Document Maintenance

### Version Information
- **Document Version**: 1.0
- **Last Updated**: June 22, 2025
- **Next Review Date**: After each major phase completion
- **Document Owner**: Development Team

### Update Triggers
- **tasks.md Changes**: When implementation tasks are modified
- **API Changes**: When Twelve Data API or quota limits change
- **Test Framework Updates**: When testing tools or patterns evolve
- **Quality Standard Changes**: When coverage or performance requirements change

### Maintenance Guidelines
- Keep testtasks.md synchronized with tasks.md structure
- Update quota limits and usage tracking as needed
- Maintain test data fixtures with current API response formats
- Review and update mock configurations regularly
- Document any testing pattern changes or improvements

---

## Conclusion

This policy ensures that testtasks.md provides comprehensive, manageable test coverage while strictly protecting API quota usage. The alternating implementation-test cycle guarantees quality at each phase while maintaining development efficiency. All test implementations must follow these guidelines to ensure consistency, reliability, and quota protection throughout the development process.