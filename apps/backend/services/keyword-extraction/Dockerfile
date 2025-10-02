FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi==0.117.1 \
    uvicorn[standard]==0.37.0 \
    pydantic==2.11.9 \
    pydantic-settings==2.1.0 \
    keybert==0.9.0 \
    sentence-transformers==5.1.1 \
    scikit-learn==1.5.2

WORKDIR /

COPY shared /shared
COPY services/keyword-extraction/app /app

ENV PYTHONPATH=/:/shared

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]