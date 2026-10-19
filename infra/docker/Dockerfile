# Creation Engine editor: Matt's Eagle Homebrew at the commit pinned in
# frontend/eagle-homebrew-host/eagle-homebrew.pin, bundled with the VTT's Foundry stand-ins.
FROM node:22-bookworm-slim AS creation-engine
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY frontend/eagle-homebrew-host/ frontend/eagle-homebrew-host/
RUN sh frontend/eagle-homebrew-host/tools/fetch-vendor.sh \
 && cd frontend/eagle-homebrew-host \
 && npm ci --no-audit --no-fund \
 && npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
COPY --from=creation-engine /build/vtt/static/eagle-homebrew/ /app/vtt/static/eagle-homebrew/

EXPOSE 5000

CMD ["gunicorn", "--worker-class", "eventlet", "--workers", "1", "--bind", "0.0.0.0:5000", "app:app"]
