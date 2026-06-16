# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Add a non-root user (Hugging Face Spaces requires user ID 1000)
RUN useradd -m -u 1000 user
USER user

# Set home directory and path for the new user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy project files and assign ownership to the user
COPY --chown=user . $HOME/app/

# Expose FastAPI port (Hugging Face Spaces defaults to 7860)
EXPOSE 7860

# Run alembic migrations on start, then launch backend
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 7860
