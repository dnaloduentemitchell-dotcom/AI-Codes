#!/usr/bin/env bash
set -euo pipefail

API_URL=${API_URL:-http://localhost:8000}

echo "Checking health endpoint..."
curl -s "${API_URL}/health" | grep -q '"status"'

echo "Smoke test passed."
