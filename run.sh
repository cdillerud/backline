#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m uvicorn src.app:app --host 127.0.0.1 --port "${PORT:-8000}"
