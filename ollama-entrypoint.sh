#!/bin/bash
set -e

MODEL="${OLLAMA_MODEL:-llama3}"

echo "Starting Ollama..."
ollama serve &

until ollama list >/dev/null 2>&1; do
  echo "Waiting for Ollama to be ready..."
  sleep 2
done

echo "Pulling model: $MODEL"
ollama pull "$MODEL"

echo "Ollama ready with model: $MODEL"
wait
