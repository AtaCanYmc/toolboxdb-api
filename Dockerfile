FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Prevent Python from writing pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (if any are needed for psycopg2 or others)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application files
COPY src/ src/
COPY alembic/ alembic/
COPY main.py .

# We don't copy .env or alembic.ini directly, we will rely on environment variables
# But alembic requires alembic.ini to run migrations, so we can copy a template or the file itself
# For security, ensure alembic.ini doesn't contain hardcoded secrets before copying.
COPY alembic.ini .

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
