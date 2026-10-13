#!/usr/bin/env bash
# Call GET /items/{item_id} with a Google identity token.
#
# Usage:
#   # Local (AUTH_DISABLED=true):
#   export SERVICE_URL="http://127.0.0.1:8000"
#   export SKIP_AUTH=1
#   ./scripts/call_item.sh 1
#
#   # Cloud Run:
#   export SERVICE_URL="https://YOUR-SERVICE-XXXX.run.app"
#   ./scripts/call_item.sh 1

set -euo pipefail

ITEM_ID="${1:-1}"
SERVICE_URL="${SERVICE_URL:?Set SERVICE_URL to your API base URL}"

URL="${SERVICE_URL%/}/items/${ITEM_ID}"

if [[ "${SKIP_AUTH:-0}" == "1" ]]; then
  curl -sS -i "${URL}"
  echo
  exit 0
fi

TOKEN="$(gcloud auth print-identity-token --audiences="${SERVICE_URL}")"

curl -sS -i "${URL}" \
  -H "Authorization: Bearer ${TOKEN}"
echo
