FROM python:3.11-slim

# Create a non-root user (Required for Hugging Face Spaces)
RUN useradd -m -u 1000 user

# Set working directory
WORKDIR /app
RUN chown -R user:user /app

# Install basic system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else into the container and set ownership
COPY --chown=user:user . .

# Switch to the non-root user
USER user

# Set environment variables for container platforms
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PORT=7860

# Default to port 7860, but allow the platform to override PORT.
EXPOSE 7860

# Start the Flask backend using gunicorn
CMD ["sh", "-c", "gunicorn backend:app --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 4 --timeout 120"]
