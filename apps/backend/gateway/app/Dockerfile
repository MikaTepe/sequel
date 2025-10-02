FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi==0.117.1 \
    uvicorn[standard]==0.37.0 \
    pydantic==2.11.9 \
    pydantic-settings==2.1.0 \
    httpx==0.27.0

# Set root as workdir
WORKDIR /

# Copy shared to /shared
COPY shared /shared

# Copy gateway code to /app
COPY gateway/app /app

# Set PYTHONPATH
ENV PYTHONPATH=/:/shared

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]