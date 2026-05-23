FROM python:3.11-slim

# System deps needed by faiss-cpu and sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model into the image so cold starts are instant
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY . .

# Render assigns PORT dynamically; default to 8000 locally
ENV PORT=8000

EXPOSE 8000

CMD uvicorn app:app --host 0.0.0.0 --port $PORT
