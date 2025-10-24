# Use Python 3.12 slim for better compatibility
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Use PORT environment variable from Render
ENV PORT 10000

# Run app
CMD ["gunicorn", "main:app", "-b", "0.0.0.0:10000"]
