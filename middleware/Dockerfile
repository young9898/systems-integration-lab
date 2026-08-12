FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates zstd \
 && curl -fsSL https://ollama.com/install.sh | sh \
 && rm -rf /usr/local/lib/ollama/cuda_v12 /usr/local/lib/ollama/cuda_v13 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py entrypoint.sh ./
# Tests live under middleware/ deliberately: the build context is ./middleware,
# so a tests/ directory at the repo root could not be COPYed here at all. They
# ship with the image so they can run against the exact dependency versions the
# container has:
#   docker compose exec middleware python -m unittest discover -s tests
COPY tests ./tests
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
