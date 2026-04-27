FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for faiss and fitz
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set an environment variable so the app knows it's in a Docker container
ENV ENVIRONMENT=production

EXPOSE 8000

# Use $PORT to allow cloud providers or standard Docker commands to inject the port
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
