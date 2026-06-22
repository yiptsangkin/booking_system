#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../frontend"
if [ ! -d node_modules ]; then
  env -u http_proxy -u https_proxy -u all_proxy npm install --registry="${NPM_REGISTRY:-https://registry.npmmirror.com}"
fi
npm run build
