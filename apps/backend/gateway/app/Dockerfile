FROM python:3.13

ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -sSL https://install.python-poetry.org | python - && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry && \
    apt-get purge -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared dependencies
COPY shared/ /shared/

# Install shared package
WORKDIR /shared
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main

# Install gateway dependencies
WORKDIR /app
COPY apps/gateway/pyproject.toml apps/gateway/poetry.lock* ./
RUN poetry config virtualenvs.create false && \
     poetry install --no-root --only main

# Copy application code
COPY apps/gateway/app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]