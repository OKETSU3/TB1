# Trade-Bot: US Stock Market Algorithmic Trading Analysis Platform

A comprehensive platform for researching and backtesting multiple algorithmic trading strategies including momentum strategies for US equity markets.

## Project Status

🔄 **In Development** - Currently implementing Phase 1: Foundation Setup

### Phase Progress
- **Phase 1**: Foundation Setup (In Progress)
  - ✅ Task 1.1: Project Structure Creation
  - 🔄 Task 1.2: Core Data Fetcher Implementation
  - 📋 Task 1.3: Basic Error Handling
  - 📋 Task 1.4: Data Validation Framework

## Features

- **Data Collection**: Integration with Twelve Data API for historical market data
- **Rate Limiting**: Built-in API quota management (800 requests/day free tier)
- **Caching**: Local SQLite-based data caching for efficiency
- **Validation**: Comprehensive OHLCV data validation
- **Error Handling**: Robust error handling for network and data issues

## Technology Stack

- **Python 3.13+**: Core language
- **Twelve Data API**: Market data source
- **SQLite**: Local data storage and caching
- **Pandas**: Data manipulation and analysis
- **Pytest**: Testing framework with TDD approach

## Development Approach

This project follows **Test-Driven Development (TDD)** with a Red-Green-Refactor cycle:
1. Write failing tests first (Red)
2. Implement minimal code to pass tests (Green)
3. Refactor for quality while maintaining tests (Refactor)

## API Quota Protection

⚠️ **Critical**: All unit tests use **0 API requests** through comprehensive mocking to protect the Twelve Data free tier limit of 800 requests/day.

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd trade-bot

# Create virtual environment
python -m venv trade-env
source trade-env/bin/activate  # On Windows: trade-env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=tradebot --cov-report=html

# Run specific phase tests
pytest tests/unit/test_phase1_foundation.py -v
```

## Configuration

Set up your Twelve Data API key:

```bash
export TWELVE_DATA_API_KEY="your_api_key_here"
```

## Project Structure

```
trade-bot/
├── tradebot/                 # Main package
│   ├── data/                 # Data handling modules
│   ├── config/               # Configuration management
│   ├── utils/                # Utility functions
│   └── exceptions.py         # Custom exceptions
├── tests/                    # Test suite
│   └── unit/                 # Unit tests
├── .claude/                  # AI development docs
└── docs/                     # Documentation
```

## License

This project is for educational and research purposes.

## Contributing

This project follows structured development phases. Please see `.claude/tasks.md` for current development roadmap.