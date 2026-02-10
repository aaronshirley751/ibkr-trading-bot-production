# docker/bot/Dockerfile

FROM python:3.11-slim-bookworm

LABEL maintainer="Charter & Stone Capital"
LABEL description="Trading bot with Gateway orchestration"
LABEL version="1.0.0"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash botuser
WORKDIR /app

# Install Poetry
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy dependency files first (layer caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev dependencies in production)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev --no-root

# Copy application code
COPY src/ ./src/
COPY docker/bot/entrypoint.sh ./entrypoint.sh

# Make entrypoint executable
RUN chmod +x ./entrypoint.sh

# Switch to non-root user
USER botuser

# Health check (optional, for external monitoring)
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import src.utils.gateway_health as gh; exit(0 if gh.quick_check() else 1)" || exit 1

ENTRYPOINT ["./entrypoint.sh"]
