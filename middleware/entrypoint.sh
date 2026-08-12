#!/bin/sh
set -e

ollama serve &

echo "Waiting for Ollama to be ready..."
until curl -fs http://localhost:11434/api/tags >/dev/null 2>&1; do
    sleep 1
done
echo "Ollama is ready."

exec python app.py
