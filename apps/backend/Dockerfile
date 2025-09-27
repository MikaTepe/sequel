FROM python:3.13 AS base
ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential \
    && curl -sSL https://install.python-poetry.org | python - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry \
    && apt-get purge -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# nur pyproject/lock zuerst kopieren für besseren Cache
COPY apps/backend/app/pyproject.toml /app/pyproject.toml
# wenn vorhanden:
# COPY apps/backend/app/poetry.lock /app/poetry.lock

# Dependencies ohne Projektcode installieren (besserer Layer-Cache)
RUN poetry config virtualenvs.create false \
 && poetry install --no-root --only main

# Quellcode
COPY apps/backend/app /app

# Falls lokale Libs benutzt werden, kopiere sie ebenfalls rein:
# COPY libs/common /libs/common

# Prod: Dependencies komplett inkl. dev ausschließen
RUN poetry install --no-root --only main

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]