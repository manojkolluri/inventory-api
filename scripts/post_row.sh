#!/usr/bin/env bash
# POST a dummy row to Cloud Run → BigQuery.
#
# Usage:
#   export SERVICE_URL="https://inventory-api-XXXX.us-central1.run.app"
#   ./scripts/post_row.sh

set -euo pipefail

SERVICE_URL="${SERVICE_URL:?Set SERVICE_URL}"
TOKEN="$(gcloud auth print-identity-token)"

curl -sS -i -X POST "${SERVICE_URL%/}/rows" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "User_id": "dummy-user-001",
    "session_id": "dummy-session-abc",
    "payload": {
      "event": "demo",
      "source": "curl",
      "ok": true
    }
  }'
echo
