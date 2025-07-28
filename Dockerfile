# Multi-stage build for production optimization
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    ca-certificates \
    procps \
    xvfb \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/logs /app/data /app/tmp

# Set Python path
ENV PYTHONPATH=/app

# Development command
CMD ["python", "run.py", "api"]

# Production stage
FROM base as production

WORKDIR /app

# Copy requirements and install production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers with minimal dependencies
RUN playwright install chromium --with-deps

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/tmp

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 proscrape
RUN chown -R proscrape:proscrape /app
USER proscrape

# Set Python path
ENV PYTHONPATH=/app
ENV PRODUCTION=true

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
CMD ["python", "run.py", "api"]