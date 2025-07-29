FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for matplotlib
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make run.py executable
RUN chmod +x run.py

# Environment variable for OpenAI API key
ENV OPENAI_API_KEY=""

# Run the application
CMD ["python", "run.py"]