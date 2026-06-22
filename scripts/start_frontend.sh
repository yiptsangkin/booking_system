#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../frontend"
if [ ! -d node_modules ]; then
  env -u http_proxy -u https_proxy -u all_proxy npm install --registry="${NPM_REGISTRY:-https://registry.npmmirror.com}"
fi
export VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://127.0.0.1:${BACKEND_PORT:-8000}}"
npm run dev -- --host "${FRONTEND_HOST:-127.0.0.1}" --port "${FRONTEND_PORT:-5173}"
