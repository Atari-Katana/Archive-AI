# Librarian Service - Library Ingestion & Processing
# Archive-AI v7.5 - Phase 5.1

FROM python:3.11-slim

# Install system dependencies for PDF processing and OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 librarian

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY processor.py .
COPY watcher.py .
COPY storage.py .

# Create watch directory
RUN mkdir -p /watch

# Set ownership
RUN chown -R librarian:librarian /app /watch

# Switch to non-root user
USER librarian

# Health check endpoint (will add FastAPI server in 5.2)
# For now, just run the watcher
CMD ["python", "-u", "watcher.py", "--watch-dir", "/watch"]
