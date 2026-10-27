#!/usr/bin/env bash
# Run Flutter with DEV_HOST / DEV_API_PORT from repo root .env
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"

DEV_HOST="127.0.0.1"
DEV_API_PORT="8001"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a
  source <(grep -E '^(DEV_HOST|DEV_API_PORT)=' "$ENV_FILE" | sed 's/\r$//')
  set +a
  DEV_HOST="${DEV_HOST:-127.0.0.1}"
  DEV_API_PORT="${DEV_API_PORT:-8001}"
else
  echo "Warning: no $ENV_FILE — using $DEV_HOST:$DEV_API_PORT (copy .env.example to .env)" >&2
fi

echo "FuelLink mobile → DEV_HOST=$DEV_HOST DEV_API_PORT=$DEV_API_PORT"

cd "$REPO_ROOT/mobile"
exec flutter run \
  --dart-define=DEV_HOST="$DEV_HOST" \
  --dart-define=DEV_API_PORT="$DEV_API_PORT" \
  "$@"
