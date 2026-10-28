# MT5 Quant Server Bridge Image (Python 3.12-slim)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && \
    update-ca-certificates && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir aiohttp

COPY server/mt5_bridge_server.py /app/server/mt5_bridge_server.py

EXPOSE 5000

CMD ["python", "-m", "server.mt5_bridge_server"]
