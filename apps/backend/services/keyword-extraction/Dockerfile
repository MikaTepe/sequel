FROM python:3.13

ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl build-essential && \
    curl -sSL https://install.python-poetry.org | python - && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry && \
    apt-get purge -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install shared dependencies
COPY shared/ /shared/
WORKDIR /shared
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main

# Install service dependencies
WORKDIR /app
COPY apps/services/keyword-extraction/pyproject.toml ./
COPY apps/services/keyword-extraction/poetry.lock* ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main

# Copy application code
COPY apps/services/keyword-extraction/app ./app

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]