FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for ccxt or compilations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose Flask port
EXPOSE 5000

# Default command (can be overridden in docker-compose)
CMD ["python", "run.py"]
