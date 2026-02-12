# Riot Games LoL Data Scraper

Professional-grade data scraping tool for League of Legends ranked matches (Solo/Duo & Flex 5v5) using clean architecture and SOLID principles.

## 🎯 Features

- **Complete Match Data Collection**: Scrapes ranked matches (Solo/Duo & Flex 5v5)
- **Multi-Region Support**: Covers all LoL servers (EUW, EUNE, NA, KR, etc.)
- **Structured Storage**:
  - Saves to SQLite database
  - Exports tables to CSV (matches, teams, participants, items, champions, spells, links)
- **Progress & Logging**:
  - CLI progress bar with endpoint status
  - Per-module log files under data/logs/
- **Static Seeding**:
  - Seeds full champions, items (with names), and summoner spells via Data Dragon
- **Clean Output**:
  - Suppresses noisy HTTP and rate limiter logs in terminal

- **Clean Architecture**: Domain → Infrastructure → Application → Presentation
- **SOLID Principles**: Interface-based design, dependency injection
- **Rate Limiting**: Smart rate limiting for all Riot API endpoints
- **Async Processing**: Fast concurrent data fetching
- **Type Safety**: Full type hints throughout the codebase

## 📁 Project Structure

```
riot_data_scraper/
├── config/                 # Configuration and environment variables
│   ├── settings.py
│   └── .env.example
├── domain/                 # Business entities and rules
│   ├── entities/          # Match, Participant, Team, Summoner
│   ├── enums/             # Region, QueueType, Rank, Role
│   └── interfaces/        # Repository interfaces
├── infrastructure/         # External systems and data access
│   ├── api/               # Riot API client & rate limiter
│   └── repositories/      # Match & Summoner repositories
├── application/            # Application business logic
│   ├── services/           # Data scraper service
│   └── use_cases/          # Scrape matches use case
├── presentation/           # User interfaces
│   └── cli.py              # Command-line interface
├── data/                   # Data storage
│   ├── db/                 # SQLite database files
│   ├── csv/                # Exported CSV tables
│   └── logs/               # Per-module log files
└── main.py                 # Application entry point
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- Riot Games API Key ([Get it here](https://developer.riotgames.com/))

### 2. Installation

```bash
# Clone or download the project
cd riot_data_scraper

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the `config/` directory:

```bash
# Copy the example file
cp config/.env.example config/.env

# Edit and add your API key
RIOT_API_KEY=RGAPI-your-key-here

# Optional: Rate limits and concurrency
RATE_LIMIT_PER_10_SEC=20
RATE_LIMIT_PER_10_MIN=100
MAX_CONCURRENT_REQUESTS=5
```

### 4. Run the Scraper

```bash
python main.py
```

The CLI will guide you through:
1. Selecting regions to scrape
2. Choosing queue types (Solo/Duo, Flex 5v5, or both)
3. Setting the number of matches per region
4. Confirming and starting the scrape

## 📊 Output Data (DB & CSV)

Tables are saved to SQLite and exported to CSV under `data/csv/`:

- matches.csv: includes match_date_simple (e.g., 2/2/2026) and duration_mmss (e.g., 30:00)
- teams.csv
- participants.csv: roles use TOP/JUNGLE/MIDDLE/BOTTOM/SUPPORT; ranks show tier and division
- champions.csv: champion_roles column lists likely lanes (e.g., Top, Middle)
- items.csv: item_id and item_name
- summoner_spells.csv: spell_id and spell_name
- participant_items.csv and participant_summoner_spells.csv: link tables

## 🏗️ Architecture Highlights

### Clean Architecture Layers

1. **Domain Layer** (innermost)
   - Pure business entities
   - No external dependencies
   - Business rules and interfaces

2. **Infrastructure Layer**
   - Riot API client implementation
   - Rate limiting logic
   - Data persistence (SQLite + CSV export)

3. **Application Layer**
   - Use cases orchestration
   - Business logic services (scraper)

4. **Presentation Layer** (outermost)
   - CLI interface
   - User interaction

### SOLID Principles

- **Single Responsibility**: Each class has one clear purpose
- **Open/Closed**: Extensible via interfaces
- **Liskov Substitution**: Interface-based design
- **Interface Segregation**: Focused interfaces (IMatchRepository, ISummonerRepository)
- **Dependency Inversion**: Depends on abstractions, not concretions

## ⚙️ Advanced Configuration

### Rate Limiting

Adjust rate limits in `.env` based on your API key tier:

```env
# Development Key
RATE_LIMIT_PER_10_SEC=20
RATE_LIMIT_PER_10_MIN=100

# Personal Key (example)
RATE_LIMIT_PER_10_SEC=100
RATE_LIMIT_PER_10_MIN=1000
```

### Concurrent Requests

Control parallelism:

```env
MAX_CONCURRENT_REQUESTS=10
```

### Patch Date Range

Override patch date range:

```env
PATCH_START_DATE=2026-02-01
PATCH_END_DATE=2026-01-23
```

## 📈 Performance

- **Async I/O**: Concurrent API requests
- **Smart Rate Limiting**: Per-endpoint rate limiters
- **Efficient Caching**: Avoids duplicate API calls
- **Progressive Collection**: Spreads through player network

## 🔍 Data Quality

- **Patch Filtering**: Filter matches within configured date range and patch version if set
- **Ranked Only**: Filters out non-ranked games
- **Complete Data**: All objectives, items, summoner spells tracked
- **Validation**: Type-safe entities ensure data integrity

## 🛠️ Development

### Running Tests (Optional)

```bash
pip install pytest pytest-asyncio
pytest
```

### Code Formatting

```bash
pip install black
black riot_data_scraper/
```

### Type Checking

```bash
pip install mypy
mypy riot_data_scraper/
```

## 📝 Notes

- **API Key**: Required for all operations
- **Rate Limits**: Respects Riot API rate limits automatically
- **Match Spread**: Uses high-ELO seeding and network propagation
- **Storage**: SQLite DB and CSV exports

## 🤝 Contributing

This is a clean, production-ready codebase following best practices:
- Type hints throughout
- Comprehensive error handling
- Structured logging
- Separation of concerns
- Testable design

## 📄 License

For educational and data engineering purposes.

## 🎮 Patch Notes

Current LoL patch versions are reflected from match data (e.g., 16.3). You can configure a target patch or set it to `any` for broader collection.

---

**Happy Scraping! 🚀**
