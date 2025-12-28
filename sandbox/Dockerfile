# Code Sandbox Dockerfile
# Secure, isolated Python execution environment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for sandbox execution
RUN useradd -m -u 1000 sandboxuser && \
    chown -R sandboxuser:sandboxuser /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Switch to non-root user
USER sandboxuser

# Expose port
EXPOSE 8000

# Run the server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
