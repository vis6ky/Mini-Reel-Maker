# Use slim Python image
FROM python:3.13-slim

# Install system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    espeak \
    ffmpeg \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python dependencies
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Render port
ENV PORT 10000

# Run app with gunicorn
CMD ["gunicorn", "main:app", "-b", "0.0.0.0:10000"]
