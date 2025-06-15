FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create app directory
WORKDIR /app

# Install Python and system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-dev \
        python3-pip \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Copy requirements (using mock requirements for testing)
COPY server/requirements-mock.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server/ /app/server/

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Set default environment variables
ENV SERVER_PORT=9876
ENV SERVER_HOST=0.0.0.0

# GPU monitoring configuration
ENV GPU_SHORT_TERM_UPTIME_THRESHOLD=99.0
ENV GPU_MEDIUM_TERM_UPTIME_THRESHOLD=99.0
ENV GPU_LONG_TERM_UPTIME_THRESHOLD=99.0
ENV GPU_MIN_VRAM_GB=30.0
ENV GPU_BASE_DELAY_MULTIPLIER=10.0
ENV GPU_MAX_DELAY_MULTIPLIER=100.0

# Expose the server port
EXPOSE 9876

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9876/health || exit 1

# Run the application
CMD ["python3", "-m", "uvicorn", "server.server:app", "--host", "0.0.0.0", "--port", "9876"]