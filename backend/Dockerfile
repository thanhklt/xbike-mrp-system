FROM python:3.11-slim

# Prevent Python from writing .pyc files & buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_VIRTUALENVS_PATH=/opt/venvs

ARG POETRY_VERSION=2.4.1
ARG INSTALL_DEV=false

WORKDIR /app

# Install system dependencies (build-essential, curl, libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Bootstrap Poetry; application dependencies come exclusively from poetry.lock.
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"
COPY pyproject.toml poetry.lock poetry.toml ./
RUN if [ "$INSTALL_DEV" = "true" ]; then \
    poetry sync --with dev --no-ansi; \
    else \
    poetry sync --only main --no-ansi; \
    fi

# Copy backend code
COPY . .

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
