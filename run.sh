#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="survey-api"

echo "[1/2] Building Docker image..."
docker build -t "$IMAGE_NAME" .

echo "[2/2] Running container on http://localhost:8080 ..."
echo "Press Ctrl+C to stop."

docker run -it --rm -p 8080:8080 "$IMAGE_NAME"

