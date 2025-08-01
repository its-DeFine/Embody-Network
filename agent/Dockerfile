FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    redis \
    asyncio \
    pyautogen

# Copy agent script
COPY simulated_agent.py .

# Run the agent
CMD ["python", "simulated_agent.py"]