FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies including the missing ones
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pydantic-settings validators PyNaCl jinja2

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash bassline && \
    chown -R bassline:bassline /app

# Switch to non-root user
USER bassline

# Create necessary directories
RUN mkdir -p logs data downloads static

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Expose ports
EXPOSE 8000 9090

# Default command
CMD ["python", "-m", "src.bot"]