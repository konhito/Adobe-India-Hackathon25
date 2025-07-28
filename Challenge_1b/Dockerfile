# Base image with Python and CPU-compatible
FROM --platform=linux/amd64 python:3.10-slim

# Set work directory
WORKDIR /app

# Copy everything
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential poppler-utils && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Preload models to avoid internet calls later
RUN python -c "\
from transformers import AutoTokenizer, AutoModel, pipeline; \
AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2'); \
AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2'); \
pipeline('summarization', model='sshleifer/distilbart-cnn-12-6')"

# Entrypoint
CMD ["python", "run.py"]
