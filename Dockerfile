# Use official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Copy all files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables (optional, for local dev)
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "p2.py"]
