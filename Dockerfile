# Multi-Stage Enterprise Production Dockerfile
# Stage 1: Build & Dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Pre-download standard NLTK datasets
RUN python -m nltk.downloader -d /root/nltk_data punkt punkt_tab stopwords wordnet averaged_perceptron_tagger_eng vader_lexicon

# Stage 2: Minimal Non-Root Runtime Container
FROM python:3.11-slim AS runner

WORKDIR /app

# Create non-root system user
RUN groupadd -g 10001 querydesk && \
    useradd -u 10001 -g querydesk -s /bin/bash -m querydesk

# Copy installed python packages from builder
COPY --from=builder /root/.local /home/querydesk/.local
COPY --from=builder /root/nltk_data /home/querydesk/nltk_data

ENV PATH=/home/querydesk/.local/bin:$PATH
ENV NLTK_DATA=/home/querydesk/nltk_data
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HOST=0.0.0.0
ENV PORT=5000

# Copy application source code
COPY --chown=querydesk:querydesk . /app

# Switch to non-root user
USER querydesk

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health/ready || exit 1

EXPOSE 5000

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2", "--log-level", "info"]
