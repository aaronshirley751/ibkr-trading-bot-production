# Charter & Stone Capital — IBKR Trading Bot

## Project Overview

Automated options trading system for a personal quantitative micro-fund. The bot executes momentum (Strategy A) and mean-reversion (Strategy B) strategies on SPY/QQQ weekly options, with automatic cash preservation (Strategy C) as the default safety mode. Deployed on Raspberry Pi 4 connecting to IBKR Gateway.

## Architecture

- **Source code:** `src/` — broker, strategy, data, execution, and risk layers
- **Tests:** `tests/` — unit, integration, e2e, live_validation (see `tests/conftest.py` for fixtures)
- **Config:** `configs/` — YAML settings files
- **Scripts:** `scripts/` — utility and validation scripts
- **Docs:** `docs/` — blueprints, handoffs, architecture documentation

## Critical Conventions

### IBKR Gateway Rules
- **ALWAYS** use `snapshot=True` for `reqMktData()` calls. NEVER use `snapshot=False`. Persistent streaming subscriptions cause Gateway buffer overflow.
- Historical data requests: max 1-hour RTH-only windows, max 1000 bars. Longer requests cause timeouts.
- Paper trading port: 4002. ALWAYS verify account type is PAPER before any order operations.
- Contract qualification (`reqContractDetails`) is required before historical data or market data requests.

### Code Quality Standards (All Must Pass)
- `poetry run ruff check src/ tests/` — zero errors
- `poetry run black --check src/ tests/` — zero reformats needed
- `poetry run mypy src/` — zero type errors
- `poetry run pytest tests/ -v` — all tests pass

### Python Conventions
- Python 3.12, managed via Poetry
- Full type hints on all function signatures (parameters and return types)
- Docstrings on all public classes and functions
- Import sorting handled by ruff (isort rules)
- Line length: 88 characters (Black default)

### Testing Conventions
- Test files: `tests/unit/test_*.py`, `tests/integration/test_*.py`, etc.
- Fixtures defined in `tests/conftest.py` — use existing fixtures before creating new ones
- Test data builders in `tests/helpers/builders.py` — use fluent builder pattern
- Custom assertions in `tests/helpers/assertions.py`
- IBKR snapshot data in `tests/fixtures/ibkr_snapshots/` — real captured market data for deterministic testing
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.live`

### Risk & Safety Rules
- Risk-critical modules (`test_risk_guards.py`, position sizing, circuit breakers) require 98% test coverage
- All risk guard tests must include: daily loss limit, weekly drawdown governor, PDT compliance, stop-loss enforcement
- `dry_run` mode must be tested and functional — no orders submitted unless explicitly enabled
- Thread-safety required for all shared state (use locks for portfolio state, order tracking)

### File Naming
- Source modules: `snake_case.py`
- Test files: `test_<module_name>.py`
- Fixtures: descriptive JSON filenames with scenario context (e.g., `spy_20260206_0930_normal_vix.json`)
- Handoff documents: `VSC_HANDOFF_<task_id>_<description>.md`

### Git Conventions
- Commit messages: `"Task X.Y.Z Chunk N: [concise description]"`
- Include bullet points of what changed in the commit body
- Push to `main` branch (solo developer workflow)

## Anti-Patterns to Avoid
- NEVER use `reqMktData(snapshot=False)` — causes buffer overflow
- NEVER submit orders without verifying paper trading mode
- NEVER skip type hints on function signatures
- NEVER create test fixtures manually when builders exist in `tests/helpers/builders.py`
- NEVER use `time.sleep()` for async coordination — use proper async/await or threading events
- NEVER hardcode account parameters — reference `configs/settings.yaml`
