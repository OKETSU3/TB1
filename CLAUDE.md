# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

### Project Identity
- **Project Name**: US Stock Market Algorithmic Trading Analysis Platform
- **Project Type**: Python Financial Analysis and Trading Strategy Research Platform
- **Primary Purpose**: Research and backtesting platform for multiple algorithmic trading strategies including momentum strategies for US equity markets
- **Development Stage**: Phase 3 Advanced Features (In Progress) - TDD-driven development with comprehensive test coverage

### Key Features
- **Momentum Strategy Analysis**: Implement and backtest various momentum-based trading strategies
- **Multi-Strategy Framework**: Support for multiple algorithmic trading strategies (momentum, mean reversion, etc.)
- **US Stock Market Data**: Real-time and historical data analysis for US equity markets
- **Performance Analytics**: Comprehensive backtesting with risk metrics and performance visualization
- **Strategy Comparison**: Side-by-side comparison of different algorithmic approaches

### Project Constraints
- **Paper Trading Only**: All strategies must default to paper trading mode for safety
- **US Market Focus**: Primarily focused on US equity markets (NYSE, NASDAQ)
- **Data Dependencies**: Relies on external data providers (Twelve Data API)
- **Real-time Limitations**: Subject to API rate limits and market data availability

---

## Technology Stack

### Programming Languages
- **Primary**: Python (3.13.5) - All algorithmic trading logic, data analysis, and backtesting
- **Configuration**: JSON/YAML - Strategy parameters and system configuration

### Frameworks and Key Dependencies
- **pandas**: Core data manipulation and time-series analysis for financial data (OHLCV format)
- **twelvedata**: Professional-grade financial API for US stock market data (800 requests/day free tier)
- **pytest**: Test framework with comprehensive TDD implementation
- **peewee**: Lightweight ORM for data caching and storage
- **PyYAML**: Configuration file support for project settings
- **black, flake8, mypy**: Code formatting and quality tools
- **freezegun, requests-mock**: Testing utilities for time and HTTP mocking

### Architecture Pattern
- **Pattern**: Phase-based TDD Development with comprehensive test-first implementation
- **Key Principles**: Test-driven development, API quota protection, modular data fetching architecture
- **Data Flow**: TDClient API → DataFetcher → DataValidator → Cache Storage

### Platform and Infrastructure
- **Target Platform**: Command-line Python application with potential for web interface
- **Build System**: Python virtual environment with pip dependency management
- **Development Environment**: Virtual environment at `trade-env/` with pre-configured dependencies

---

## Development Commands

```bash
# Activate virtual environment
source trade-env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Run specific test phase
python -m pytest tests/unit/test_phase1_foundation.py -v

# Run tests with coverage
python -m pytest tests/ --cov=tradebot --cov-report=html

# Run specific test class
python -m pytest tests/unit/test_phase1_foundation.py::TestDataFetcher -v

# Run single test method
python -m pytest tests/unit/test_phase1_foundation.py::TestDataFetcher::test_t1_2_fetch_historical_data_success -v

# Verify API quota protection (should show 0 requests)
python -m pytest tests/unit/ -v | grep -E "(API|quota|requests)"

# Code quality checks
black tradebot/ tests/
flake8 tradebot/ tests/
mypy tradebot/
```

---

## Architecture Overview

### Current Implementation (Phases 1-2 Complete, Phase 3 In Progress)
- **Data Layer**: `tradebot/data/` - DataFetcher, DataValidator, Cache, and Freshness management implemented
- **Configuration Layer**: `tradebot/config/` - ConfigManager with YAML support implemented
- **Utilities**: `tradebot/utils/` - Logger and RateLimiter implemented
- **Database Models**: `tradebot/data/models.py` - Peewee ORM models for data storage
- **Exception Handling**: `tradebot/exceptions.py` - Custom exception hierarchy for proper error propagation
- **Testing Framework**: `tests/unit/` - Comprehensive TDD implementation with 100% API quota protection

### Key Architectural Decisions
- **TDD-First Development**: All code developed with comprehensive test coverage
- **API Quota Protection**: Complete mocking strategy ensures 0 API usage in unit tests
- **Exception Hierarchy**: Selective exception propagation (InvalidSymbolError passthrough, others wrapped)
- **Modular Design**: Clean separation between data fetching, validation, caching, and configuration layers
- **Configuration-Driven**: YAML-based configuration with environment variable overrides
- **Database Abstraction**: Peewee ORM for SQLite-based local data storage

---

## AI Assistant Guidelines

### Development Methodology
- **TDD Approach**: Always implement tests first using `.claude/testtasks.md`, then implement functionality using `.claude/tasks.md`
- **API Quota Protection**: Ensure 100% mocking in unit tests - never make real API calls during testing
- **Phase-Based Development**: Follow the structured phase approach outlined in `.claude/tasks.md` and `.claude/testtasks.md`
- **Test Coverage**: Maintain comprehensive test coverage for all implemented functionality

### Current Project Context
- **Active Development**: Currently in Phase 3 (Advanced Features) - data freshness in progress
- **TDD Implementation**: Use alternating `.claude/testtasks.md` → `.claude/tasks.md` implementation pattern
- **API Constraints**: Twelve Data free tier (800 requests/day) - strict quota management required
- **Test Status**: Phase 1 & 2 complete, Phase 3 partially complete (1/4 tests), 0 API requests used

### Code Generation Requirements
- **Must**: Follow existing patterns in `tradebot/data/fetcher.py` and `tradebot/data/validator.py`
- **Must**: Use comprehensive mocking with @patch decorators for external API calls
- **Must**: Implement custom exceptions from `tradebot/exceptions.py` hierarchy
- **Must**: Use pandas DataFrame for all OHLCV data handling
- **Must**: Include proper logging and error handling for production readiness
- **Must**: Import exceptions and dependencies at module level for performance
- **Must Not**: Make real API calls in unit tests
- **Must Not**: Hardcode API keys - use environment variables (TWELVE_DATA_API_KEY)
- **Must Not**: Use inline imports inside methods

### Environment Variables
- **Required**: `TWELVE_DATA_API_KEY` - API key for Twelve Data service
- **Optional**: `TWELVE_DATA_TIMEOUT` - Override API timeout (default: 30 seconds)
- **Optional**: `TWELVE_DATA_RETRY_COUNT` - Override retry attempts (default: 3)
- **Optional**: `TWELVE_DATA_DAILY_LIMIT` - Override daily quota (default: 800)
- **Optional**: `CACHE_FRESHNESS_HOURS` - Override cache freshness (default: 24 hours)
- **Optional**: `CACHE_MAX_SIZE_MB` - Override cache size limit (default: 100 MB)

---

## Critical Project Constraints

### API Quota Management (CRITICAL)
- **Free Tier Limit**: 800 requests/day for Twelve Data API
- **Unit Test Requirement**: 0 API requests (100% mocking required)
- **Integration Test Budget**: Maximum 10 requests per complete test run
- **Daily Test Budget**: Maximum 50 requests total for all testing activities
- **Quota Monitoring**: Mandatory tracking of all API usage

### TDD Development Requirements
- **Test-First Development**: Always implement tests from `.claude/testtasks.md` before implementation
- **Phase-Based Progress**: Complete each phase fully before advancing to next
- **Test Coverage Standards**: Maintain comprehensive coverage for all implemented functionality
- **Verification Required**: All tests must pass before proceeding to next development phase

### Current Implementation Status
- **Phase 1 Complete**: Foundation setup with all tests passing
- **Phase 2 Complete**: Configuration and stability with all tests passing  
- **Phase 3 In Progress**: Advanced features - data freshness complete, batch processing pending
- **API Usage**: 0 requests used in development so far (100% quota protection maintained)
- **Test Framework**: Fully established with pytest, comprehensive mocking patterns

---

## Development Workflow Guidelines

### TDD Implementation Workflow
1. **Read `.claude/testtasks.md`**: Understand the specific test requirements for current phase
2. **Implement Tests First**: Create failing tests following the established patterns
3. **Run Tests to Confirm Red**: Verify tests fail as expected (TDD Red phase)
4. **Read `.claude/tasks.md`**: Understand implementation requirements corresponding to test
5. **Implement Functionality**: Write minimal code to make tests pass (TDD Green phase)
6. **Refactor if Needed**: Improve code quality while keeping tests passing
7. **Verify All Tests Pass**: Ensure no regressions in existing functionality

### Critical Success Criteria
- **Zero API Usage in Tests**: All unit tests must use complete mocking
- **Exception Handling**: Follow selective propagation pattern (InvalidSymbolError passthrough)
- **Documentation**: Follow established patterns in `.claude/` directory for guidance
- **Phase Completion**: All tests in a phase must pass before advancing

### File Structure Awareness
- **`.claude/`**: Contains `tasks.md`, `testtasks.md`, `testpolicy.md`, `project-knowledge.md` for guidance
- **`tests/unit/`**: Contains phase-based test implementations
- **`tradebot/`**: Main package with `data/`, `config/`, `utils/` modules
- **`tradebot/exceptions.py`**: Custom exception hierarchy for proper error handling

### Next Development Steps
1. **Phase 3 Focus**: Complete remaining advanced features - batch processing, performance optimization, error recovery
2. **TDD Continuation**: Follow `.claude/testtasks.md` → `.claude/tasks.md` alternating pattern
3. **Quota Protection**: Maintain 0 API usage in unit tests
4. **Test Coverage**: Continue comprehensive test-first development