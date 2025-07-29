FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy adapter code
COPY . /app/orchestrator/adapter/

# Copy shared modules from platform
COPY ../../shared /app/shared

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Run the adapter service
CMD ["python", "-m", "orchestrator.adapter.main"]