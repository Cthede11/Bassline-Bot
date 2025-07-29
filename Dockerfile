FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (FFmpeg, git, curl)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (merge into one layer)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir pydantic-settings validators PyNaCl jinja2 requests

# Copy application code
COPY . .

# Create directories and set correct permissions
RUN mkdir -p logs data downloads static \
    && useradd --create-home --shell /bin/bash bassline \
    && chown -R bassline:bassline /app

# Switch to non-root user
USER bassline

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check (use curl for simplicity)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8080/health || exit 1

# Expose ports
EXPOSE 8080 9090

# Default command
CMD ["python", "-m", "src.bot"]
