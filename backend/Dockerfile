FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends gnucobol \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home necro

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY samples samples

USER necro
WORKDIR /app/backend
ENV PORT=8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
