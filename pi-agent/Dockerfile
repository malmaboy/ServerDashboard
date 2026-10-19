FROM python:3.12-slim

# socat: bridge Arduino <-> TCP gerido pelo agente (só usado se BRIDGE_ENABLED=true)
RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py bridge.py ./

EXPOSE 9090

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9090"]
