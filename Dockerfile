FROM python:3.12-slim

LABEL org.opencontainers.image.title="OverlandListener" \
      org.opencontainers.image.description="GPS location data receiver for the Overland app" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/matt/OverlandListener"

# Create non-root user
RUN adduser --disabled-password --no-create-home appuser

# Install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Env vars
ENV LOG_DIR=/data

# Create data directory owned by appuser
RUN mkdir -p /data && chown appuser:appuser /data

USER appuser
WORKDIR /app/src

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]