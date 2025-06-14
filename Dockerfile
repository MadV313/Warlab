# Use an official Python runtime as the base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy files into the container
COPY . .

# Install dependencies (include python-dotenv for .env support)
RUN pip install --no-cache-dir -r requirements.txt

# Set environment (optional if .env will be sourced inside Python)
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "bot.py"]
