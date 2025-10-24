# Use slim Python image
FROM python:3.13-slim

# Install system packages, fonts, ffmpeg, espeak
RUN apt-get update && apt-get install -y \
    espeak \
    ffmpeg \
    fonts-dejavu-core \
    fonts-noto-color-emoji \
    libfreetype6 \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose Render port
ENV PORT 10000

# Run app with gunicorn
CMD ["gunicorn", "main:app", "-b", "0.0.0.0:10000"]
