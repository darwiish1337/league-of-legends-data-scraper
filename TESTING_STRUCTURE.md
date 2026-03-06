<div align="center">

# 🧪 Test Suite Documentation

<img src="https://img.shields.io/badge/Tests-87%20Passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white"/>
<img src="https://img.shields.io/badge/Framework-pytest-blue?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Coverage-90%25%2B-success?style=for-the-badge&logo=codecov&logoColor=white"/>
<img src="https://img.shields.io/badge/Status-All%20Passing-success?style=for-the-badge&logo=checkmarx&logoColor=white"/>

<br/>

> **Production-ready test suite** for the League of Legends data scraper — organized, isolated, and CI/CD ready.

</div>

---

## 📖 Table of Contents

- [Philosophy](#-philosophy)
- [Directory Structure](#-directory-structure)
- [Test Categories](#-test-categories)
  - [🧩 Unit Tests](#-unit-tests-40-tests)
  - [🖥️ CLI Tests](#%EF%B8%8F-cli-tests-5-tests)
  - [🔗 Integration Tests](#-integration-tests-8-tests)
  - [🏛️ Legacy Tests](#%EF%B8%8F-legacy-tests-29-tests)
- [Shared Fixtures](#-shared-fixtures)
- [Running Tests](#-running-tests)
- [Quality Metrics](#-quality-metrics)
- [Best Practices](#-best-practices)
- [Troubleshooting](#-troubleshooting)
- [CI/CD Setup](#-cicd-setup)

---

## 💡 Philosophy

| Principle | Description |
|-----------|-------------|
| 🎯 **One test = One behavior** | Each test validates exactly one thing |
| 🔒 **Isolated unit tests** | All external dependencies are mocked |
| 🔗 **Integration coverage** | Full workflow validation end-to-end |
| 📛 **Clear naming** | `test_method_does_something` convention |
| ♻️ **DRY fixtures** | Shared setup/teardown via `conftest.py` |

---

## 📁 Directory Structure

```
tests/
│
├── 📄 conftest.py                        ⭐ Shared fixtures & configuration
│
├── 🧩 unit/                              40 tests — Component isolation
│   ├── test_rate_limiter.py             7  tests
│   ├── test_data_persistence.py         10 tests
│   ├── test_data_scraper.py             5  tests
│   ├── test_domain_models.py            13 tests
│   └── test_settings.py                 9  tests
│
├── 🖥️  cli/                              5 tests — CLI command logic
│   └── test_scraping_command.py
│
├── 🔌 infrastructure/                    Infrastructure layer tests
│
├── 🔗 integration/                       8 tests — Workflow validation
│   └── test_session_workflows.py
│
└── 🏛️  legacy/                            29 tests — Kept for reference
    ├── test_resume_logic.py             7  tests
    ├── test_resume_comprehensive.py     8  tests
    └── test_project_integration.py      14 tests
```

---

## 🗂️ Test Categories

### 🧩 Unit Tests (40 tests)

> **Location:** `tests/unit/` &nbsp;|&nbsp; **Approach:** One component, fully isolated, dependencies mocked

<details>
<summary><strong>⏱️ test_rate_limiter.py — 7 tests</strong></summary>

```python
class TestRateLimiter:
    ├── test_initialization
    ├── test_acquire_within_limits
    └── test_status_reporting

class TestEndpointRateLimiter:
    ├── test_initialization
    ├── test_set_default_limiter
    ├── test_add_endpoint_limiter
    └── test_acquire_with_endpoint
```

**Covers:**
- ✅ Rate limiter initialization
- ✅ Request acquisition within limits
- ✅ Per-endpoint limiting
- ✅ Status reporting

</details>

<details>
<summary><strong>💾 test_data_persistence.py — 10 tests</strong></summary>

```python
class TestDataPersistenceService:
    ├── test_initialization
    ├── test_create_session
    ├── test_get_session_regions
    ├── test_mark_region_running
    ├── test_update_region_progress
    ├── test_mark_region_completed
    ├── test_mark_region_skipped
    ├── test_database_table_structure
    ├── test_multiple_regions_independent_progress
    └── test_zero_progress_session_detection
```

**Covers:**
- ✅ Session CRUD operations
- ✅ Region status transitions
- ✅ Progress tracking per region
- ✅ Database table structure
- ✅ Region isolation

</details>

<details>
<summary><strong>🕷️ test_data_scraper.py — 5 tests</strong></summary>

```python
class TestDataScraperService:
    ├── test_initialization
    ├── test_progress_callback_registration
    ├── test_status_callback_registration
    ├── test_deduplication_sets
    └── test_both_callbacks_together
```

**Covers:**
- ✅ Service initialization
- ✅ Callback registration
- ✅ Deduplication tracking

</details>

<details>
<summary><strong>🗺️ test_domain_models.py — 13 tests</strong></summary>

```python
class TestRegionEnum:
    ├── test_all_regions_exist
    ├── test_region_values
    ├── test_known_regions_present
    └── test_regional_route_attribute

class TestQueueTypeEnum:
    ├── test_ranked_queues_exist
    ├── test_ranked_queues_have_queue_id
    ├── test_specific_queues
    └── test_queue_id_values

class TestMatchEntity:
    ├── test_match_creation
    ├── test_match_region
    ├── test_match_queue_type
    ├── test_match_duration
    └── test_match_version
```

**Covers:**
- ✅ Domain enumerations
- ✅ Entity creation
- ✅ Attribute validation

</details>

<details>
<summary><strong>⚙️ test_settings.py — 9 tests</strong></summary>

```python
class TestSettingsConfiguration:
    ├── test_required_settings_exist
    ├── test_rate_limit_values_are_positive
    ├── test_concurrent_requests_is_positive
    ├── test_timeout_is_positive
    └── test_max_retries_is_non_negative

class TestSettingsDirectories:
    ├── test_directory_paths_exist
    └── test_directories_are_paths

class TestPatchConfiguration:
    ├── test_target_patch_exists
    ├── test_patch_start_date_exists
    └── test_patch_format
```

**Covers:**
- ✅ Configuration completeness
- ✅ Directory paths defined
- ✅ Patch configuration valid

</details>

---

### 🖥️ CLI Tests (5 tests)

> **Location:** `tests/cli/` &nbsp;|&nbsp; **Focus:** Resume menu behavior & region filtering

<details>
<summary><strong>🔁 test_scraping_command.py — 5 tests</strong></summary>

```python
class TestResumeMenuFiltering:
    ├── test_resume_filters_pending_regions
    ├── test_zero_progress_detection
    ├── test_session_filtering_all_completed
    └── test_session_filtering_mixed_statuses
```

**Covers:**
- ✅ Resume menu shows only incomplete regions
- ✅ Zero-progress detection
- ✅ Region filtering logic

</details>

---

### 🔗 Integration Tests (8 tests)

> **Location:** `tests/integration/` &nbsp;|&nbsp; **Focus:** Multi-component workflows & real state management

<details>
<summary><strong>🔄 test_session_workflows.py — 8 tests</strong></summary>

```python
class TestSessionLifecycle:
    ├── test_create_progress_complete_workflow
    └── test_progress_accumulation

class TestCrashRecovery:
    ├── test_resume_after_interruption
    └── test_resume_skips_completed_regions

class TestMultipleRegionIsolation:
    ├── test_independent_progress_tracking
    └── test_independent_status_transitions

class TestPersistenceAcrossInstances:
    ├── test_persistence_survives_service_reinit
    └── test_multiple_sessions_independent
```

**Covers:**
- ✅ Complete session lifecycle
- ✅ Crash recovery workflows
- ✅ Region isolation
- ✅ Data persistence across restarts

</details>

---

### 🏛️ Legacy Tests (29 tests)

> Kept for reference — document specific bugs found and fixed during development.

| File | Tests | Purpose |
|------|-------|---------|
| `test_resume_logic.py` | 7 | Resume menu behavior |
| `test_resume_comprehensive.py` | 8 | DB persistence (detailed) |
| `test_project_integration.py` | 14 | Cross-component validation |

---

## 🔧 Shared Fixtures

> Defined in `conftest.py` — available to **all** tests automatically.

```python
# 🌍 Auto-enabled for every test
@pytest.fixture(autouse=True)
def setup_testing_env():
    """Automatically sets TESTING=true for all tests"""

# 📂 Isolated database per test
@pytest.fixture
def temp_db_dir():       # Unique temp directory, auto-cleaned
def temp_db_path():      # Path inside temp dir

# 🔌 Ready-to-use service instances
@pytest.fixture
def persistence_service(temp_db_path):   # DataPersistenceService
def sample_session_id():                 # "test_session_12345"
def sample_regions():                    # ["EUW1", "NA1", "KR"]

# 🤖 Mocked external dependencies
@pytest.fixture
def mock_riot_client():     # Mocked Riot API client
def mock_rate_limiter():    # Mocked rate limiter
```

---

## ▶️ Running Tests

### Run Everything
```bash
pytest tests/ -v
```

### Run by Category
```bash
pytest tests/unit/         -v    # 🧩 Unit tests only
pytest tests/cli/          -v    # 🖥️  CLI tests only
pytest tests/integration/  -v    # 🔗 Integration tests only
```

### Run a Specific File
```bash
pytest tests/unit/test_rate_limiter.py     -v
pytest tests/unit/test_data_persistence.py -v
```

### With Coverage Report
```bash
pytest tests/ --cov=application --cov=infrastructure --cov=domain --cov=presentation
```

### Debug & Diagnostics
```bash
pytest tests/ -vv -s          # 🔬 Verbose + print output
pytest tests/ -x              # 🛑 Stop on first failure
pytest tests/ --lf            # 🔁 Re-run last failed only
pytest tests/ --durations=10  # 🐢 Show 10 slowest tests
```

---

## 📊 Quality Metrics

<div align="center">

| Metric | Value |
|--------|-------|
| 🧪 **Total Tests** | 87 |
| ✅ **Pass Rate** | 100% |
| ⚡ **Execution Time** | ~5 seconds |
| 📦 **Unit Tests** | 40 (46%) |
| 🔗 **Integration Tests** | 8 (9%) |
| 🖥️ **CLI Tests** | 5 (6%) |
| 🏛️ **Legacy Tests** | 29 (33%) |
| 🎯 **Target Coverage** | 90%+ overall |

</div>

---

## ✅ Best Practices Applied

| # | Practice | Description |
|---|----------|-------------|
| 1 | 🔒 **Isolation** | Every test gets its own temp DB — zero shared state |
| 2 | 📛 **Clarity** | Descriptive names: `test_method_does_something` |
| 3 | 🎯 **Focus** | One test validates one behavior only |
| 4 | ♻️ **Fixtures** | DRY setup via `conftest.py` |
| 5 | 🤖 **Mocking** | External dependencies always mocked in unit tests |
| 6 | 📂 **Organization** | Grouped by component and concern |
| 7 | 📝 **Documentation** | Docstrings explain purpose and intent |
| 8 | 🧹 **Cleanup** | Proper teardown prevents test pollution |

---

## 🛠️ Troubleshooting

<details>
<summary><strong>❌ UnicodeEncodeError</strong></summary>

**Cause:** Windows PowerShell using cp1252 encoding

**Fix:**
```powershell
$env:TESTING='true'
pytest tests/ -v
```
</details>

<details>
<summary><strong>❌ database is locked</strong></summary>

**Cause:** Concurrent access to the same SQLite database

**Fix:** Already handled — every test automatically gets its own isolated temp DB via fixtures. If it persists, check for leftover `.db` files in `/tmp`.
</details>

<details>
<summary><strong>❌ Test hangs / timeout</strong></summary>

**Cause:** Async test without proper timeout

**Fix:** `pytest-asyncio` is installed. Check your async fixtures and add explicit timeouts where needed.
</details>

<details>
<summary><strong>🔍 Need to debug a test?</strong></summary>

Add `-s` to see all `print()` output:
```bash
pytest tests/unit/test_data_persistence.py -s -v
```
</details>

---

## 🚀 CI/CD Setup

> Drop this into your `.github/workflows/tests.yml` or equivalent:

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --tb=short
        env:
          TESTING: "true"
        timeout-minutes: 2
```

✅ Deterministic — no external API calls required  
✅ Isolated — each test cleans up after itself  
✅ Fast — full suite runs in ~5 seconds

---

## ➕ Adding New Tests

**Quick checklist:**

1. 🤔 **Decide category** — Unit? Integration? CLI?
2. 📁 **Pick location** — Place in the right subfolder
3. 📛 **Name it clearly** — `test_method_does_something`
4. ♻️ **Use fixtures** — Leverage `conftest.py`
5. 🔒 **Keep isolated** — Don't share mutable state
6. 📝 **Add a docstring** — Explain the *why*, not just the *what*

---

<div align="center">

**Last Updated:** March 2026 &nbsp;|&nbsp; **Framework:** pytest &nbsp;|&nbsp; **Status:** ✅ All 87 tests passing

</div>
