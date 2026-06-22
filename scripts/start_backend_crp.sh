#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"
if [ "${BACKEND_RELOAD:-0}" = "1" ]; then
  conda run -n crp uvicorn app.main:app --reload --host "${BACKEND_HOST:-127.0.0.1}" --port "${BACKEND_PORT:-8000}"
else
  conda run -n crp uvicorn app.main:app --host "${BACKEND_HOST:-127.0.0.1}" --port "${BACKEND_PORT:-8000}"
fi
