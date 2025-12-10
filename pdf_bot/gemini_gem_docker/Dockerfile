FROM python:3.9-slim

WORKDIR /app

# System deps for psycopg2 + curl for healthchecks
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/requirements.txt /app/scripts/requirements.txt
RUN pip install --no-cache-dir -r /app/scripts/requirements.txt

COPY scripts /app/scripts

WORKDIR /app
CMD ["python", "scripts/main_brain.py"]
