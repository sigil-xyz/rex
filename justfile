default:
    @just --list

# Install all dependencies and set up pre-commit
install:
    uv sync --dev
    pre-commit install

# Run all checks (lint + typecheck + test + typos)
check: lint typecheck test typos

# Lint with ruff
lint:
    uv run ruff check .
    uv run ruff format --check .

# Fix all auto-fixable lint issues
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Type check with mypy
typecheck:
    uv run mypy src/

# Run tests
test:
    uv run pytest

# Run tests with HTML coverage report
cov:
    uv run pytest --cov=src/rex --cov-report=html
    @echo "Coverage report: htmlcov/index.html"

# Check for typos
typos:
    typos .

# Start the daemon in foreground dev mode
dev:
    uv run rex --dev

# View live daemon logs
logs:
    journalctl --user -u rex -f

# Install systemd user service
service-install:
    mkdir -p ~/.config/systemd/user
    cp systemd/rex.service ~/.config/systemd/user/rex.service
    systemctl --user daemon-reload
    systemctl --user enable --now rex
    @echo "Rex service installed and started"

# Remove systemd user service
service-remove:
    systemctl --user disable --now rex
    rm -f ~/.config/systemd/user/rex.service
    systemctl --user daemon-reload

# Release: bump version, update changelog, tag
release version:
    @echo "Releasing {{version}}"
    sed -i "s/^version = .*/version = \"{{version}}\"/" pyproject.toml
    python scripts/compile_changelog.py {{version}}
    git add pyproject.toml CHANGELOG.md
    git commit -m "chore: release {{version}}"
    git tag v{{version}}
    @echo "Run: git push origin main v{{version}}"
