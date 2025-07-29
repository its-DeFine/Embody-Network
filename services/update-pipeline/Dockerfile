FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including git
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY services/update-pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared /app/shared

# Copy application code
COPY services/update-pipeline /app

# Create deployment directories
RUN mkdir -p /app/deployments/repo /app/deployments/config

# Run the application
CMD ["python", "-u", "main.py"]