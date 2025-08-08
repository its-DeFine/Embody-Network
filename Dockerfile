# Backend only - no frontend needed
FROM python:3.11-slim@sha256:9c36d8a0e4f6e5e78c1d28a6a6a75a8b9a7d1f2ac7d2ff1b0c2cb2a79f7a2c2c

WORKDIR /app

# Install system dependencies including Docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app

# Copy application
COPY app/ /app/app/

# Create data directories
RUN mkdir -p /app/data /app/data/audit /app/backups

# Expose port
EXPOSE 8000

# Run the application
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]