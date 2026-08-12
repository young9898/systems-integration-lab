FROM python:3.12-slim

WORKDIR /app

# Ollama is downloaded to a file and then run, NOT piped into sh. `curl ... | sh`
# hides download failures: the pipeline's exit status is sh's, and sh reading an
# empty stdin exits 0, so a 503 from the download produces a "successful" build of
# an image with no ollama binary in it. That failure then surfaces at runtime as
# an entrypoint looping on "ollama: not found" — far from its cause.
# `command -v ollama` is the receipt: if the install did not produce a binary on
# PATH, the build fails here instead of shipping.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates zstd \
 && curl -fsSL https://ollama.com/install.sh -o /tmp/ollama-install.sh \
 && sh /tmp/ollama-install.sh \
 && rm -f /tmp/ollama-install.sh \
 && command -v ollama \
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
