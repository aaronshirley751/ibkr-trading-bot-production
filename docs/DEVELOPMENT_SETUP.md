# Development Environment Setup

This guide walks you through setting up your local development environment for the IBKR Options Trading Bot project.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+** (This project uses Python 3.12)
- **Poetry 1.7+** (Dependency management and packaging)
- **Git** (Version control)
- **VSCode** (Recommended IDE, configured in `.vscode/`)

### Verify Prerequisites

```bash
# Check Python version
python --version  # Should be 3.10 or higher

# Check Poetry installation
poetry --version  # Should be 1.7.0 or higher

# Check Git installation
git --version
```

### Installing Prerequisites

**Python 3.12:**
- **macOS:** `brew install python@3.12`
- **Ubuntu/Debian:** `sudo apt install python3.12 python3.12-venv`
- **Windows:** Download from [python.org](https://www.python.org/downloads/)

**Poetry:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Add Poetry to your PATH (the installer will show you the command).

### Windows-Specific: Adding Poetry to PATH

**IMPORTANT for Windows users:** Poetry must be added to your PATH to use it from PowerShell/CMD.

**Temporary (current session only):**
```powershell
$env:Path += ";$env:APPDATA\Python\Scripts"
```

**Permanent (all future sessions - recommended):**
```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$env:APPDATA\Python\Scripts", "User")
```

**Verify Poetry is accessible:**
```powershell
poetry --version
```

If this shows the version number, you're set. If not, close and reopen your terminal after adding to PATH permanently.

---

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ibkr-options-bot
```

### 2. Install Dependencies

**⚠️ CRITICAL STEP - Do not skip this!**

```bash
# Install all dependencies (including dev dependencies)
poetry install

# Verify the virtual environment was created
poetry env info
```

Poetry will:
- Create a virtual environment in `~/.cache/pypoetry/virtualenvs/` (Linux/macOS) or `%LOCALAPPDATA%\pypoetry\Cache\virtualenvs\` (Windows)
- Install all production dependencies
- Install all development dependencies (ruff, black, mypy, pytest, etc.)

**Note:** You may see deprecation warnings about `[tool.poetry.*]` configuration. These are cosmetic and will be addressed in Task 0.4 (CI/CD setup). They do not affect functionality.

### 3. Activate the Virtual Environment

**Option A: Use Poetry shell (recommended):**
```bash
poetry shell
```

**Option B: Run commands via Poetry:**
```bash
poetry run python <script.py>
poetry run pytest
```

---

## Environment Verification

Run these commands to verify your development environment is correctly configured:

### 1. Validate Project Configuration
```bash
poetry check
```
**Expected output:** `All set!`

### 2. List Installed Dependencies
```bash
poetry show
```
**Expected output:** List of ~20-30 packages including:
- `ib-insync` (IBKR API)
- `pandas`, `numpy` (Data processing)
- `pytest`, `pytest-asyncio` (Testing)
- `ruff`, `black`, `mypy` (Code quality)

### 3. Verify Code Linter (Ruff)
```bash
poetry run ruff --version
poetry run ruff check .
```
**Expected output:** Ruff version number, then clean check (or fixable issues)

### 4. Verify Code Formatter (Black)
```bash
poetry run black --version
poetry run black --check .
```
**Expected output:** Black version number, confirmation that code is formatted

### 5. Verify Type Checker (Mypy)
```bash
poetry run mypy --version
poetry run mypy src/
```
**Expected output:** Mypy version number, then type check results

### 6. Run Test Suite
```bash
poetry run pytest --version
poetry run pytest
```
**Expected output:** Pytest version number, then test results

**Note:** For a new project with no tests written yet, you may see:
- "collected 0 items" 
- Exit code 1 (this is normal - pytest exits with 1 when no tests are found)

**This is expected and acceptable.** Once test files are created in Phase 1, pytest will collect and run them normally.

---

## IDE Configuration

### VSCode Setup (Recommended)

This project includes pre-configured VSCode settings in `.vscode/`:

**Included configurations:**
- **Python interpreter:** Automatically uses Poetry virtual environment
- **Linting:** Ruff enabled with project rules
- **Formatting:** Black enabled (format on save)
- **Type checking:** Mypy enabled
- **Testing:** Pytest integration
- **Extensions:** Recommended extensions list

**To use these settings:**
1. Open the project folder in VSCode: `code .`
2. VSCode will detect `.vscode/settings.json`
3. Install recommended extensions when prompted
4. Verify Python interpreter is set to Poetry environment: `Cmd/Ctrl + Shift + P` → "Python: Select Interpreter" → Choose the Poetry virtualenv

**Recommended VSCode Extensions:**
- Python (Microsoft)
- Pylance (Microsoft)
- Ruff (Astral Software)
- Even Better TOML (tamasfe)
- GitHub Copilot (if available)

---

## Code Quality Tools

This project enforces strict code quality standards:

### Linting with Ruff
```bash
# Check for issues
poetry run ruff check .

# Auto-fix issues where possible
poetry run ruff check --fix .
```

### Formatting with Black
```bash
# Check formatting
poetry run black --check .

# Format code
poetry run black .
```

### Type Checking with Mypy
```bash
# Check types
poetry run mypy src/
```

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src

# Run specific test file
poetry run pytest tests/test_specific.py

# Run in verbose mode
poetry run pytest -v
```

---

## Project Structure

```
ibkr-options-bot/
├── src/                    # Source code
│   ├── api/               # IBKR API integration
│   ├── strategies/        # Trading strategies
│   ├── risk/              # Risk management
│   └── utils/             # Utilities
├── tests/                 # Test suite
├── docs/                  # Documentation
├── config/                # Configuration files
├── .vscode/               # VSCode settings
├── pyproject.toml         # Poetry configuration
└── README.md              # Project overview
```

---

## Common Issues

### Issue: `poetry: command not found` (Windows)
**Solution:** Poetry not in PATH. Add it permanently:
```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$env:APPDATA\Python\Scripts", "User")
```
Then close and reopen your terminal.

### Issue: `poetry: command not found` (Linux/macOS)
**Solution:** Poetry not in PATH. Add it:
```bash
# macOS/Linux
export PATH="$HOME/.local/bin:$PATH"
```
Add this line to your `~/.bashrc` or `~/.zshrc` to make it permanent.

### Issue: Python version mismatch
**Solution:** Ensure you're using Python 3.10+:
```bash
poetry env use python3.12
poetry install
```

### Issue: Virtual environment not activating
**Solution:** Use Poetry shell:
```bash
poetry shell
```

Or run commands via Poetry:
```bash
poetry run python <script>
```

### Issue: Dependency installation fails
**Solution:** Clear Poetry cache and reinstall:
```bash
poetry cache clear pypi --all
poetry install
```

### Known Issue: Poetry deprecation warnings
**Symptom:** Warnings about deprecated `[tool.poetry.*]` keys when running `poetry check`

**Impact:** Cosmetic only - does not affect functionality

**Resolution:** Will be addressed in Task 0.4 (CI/CD Framework) by migrating to PEP 621 standard format. No action needed for now.

---

## Development Workflow

### Daily Development Cycle
1. Pull latest changes: `git pull origin main`
2. Activate environment: `poetry shell`
3. Run tests before changes: `poetry run pytest`
4. Make your changes
5. Run quality checks:
   ```bash
   poetry run ruff check --fix .
   poetry run black .
   poetry run mypy src/
   poetry run pytest
   ```
6. Commit and push: `git add .` → `git commit -m "..."` → `git push`

### Adding New Dependencies
```bash
# Production dependency
poetry add <package-name>

# Development dependency
poetry add --group dev <package-name>
```

### Updating Dependencies
```bash
# Update all dependencies
poetry update

# Update specific dependency
poetry update <package-name>
```

---

## Next Steps

Once your environment is set up:

1. **Review the architecture:** See `docs/alpha_learnings.md` for implementation insights
2. **Review the strategy:** See project knowledge for trading strategy details
3. **Run the test suite:** `poetry run pytest` to verify everything works
4. **Start coding:** Follow the project roadmap in the Planner board

**Note:** Pre-commit hooks and CI/CD pipelines will be configured in Task 0.4.

---

## Getting Help

- **Documentation:** See `docs/` folder for detailed guides
- **Issues:** Check GitHub Issues for known problems
- **Questions:** Reach out via project communication channels

---

## Environment Health Check Script

Quick one-liner to verify your environment:

```bash
poetry check && \
poetry run ruff --version && \
poetry run black --version && \
poetry run mypy --version && \
poetry run pytest --version && \
echo "✅ Environment is healthy!"
```

If all commands succeed, you're ready to develop!

---

*Last updated: 2026-02-05*
*Next review: Task 0.4 (CI/CD setup)*