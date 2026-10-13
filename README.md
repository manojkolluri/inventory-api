# Inventory API — FastAPI on Cloud Run + identity token auth

Tiny learning API:

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/health` | none (app-level) |
| `GET` | `/items/{item_id}` | Bearer Google identity token |

Valid item IDs: `1`, `2`, `3`.

---

## 1) Run locally

```bash
cd /Users/manojkolluri/Desktop/FastAPI
source .venv/bin/activate
pip install -r requirements.txt

export AUTH_DISABLED=true
uvicorn main:app --reload --port 8000
```

Test:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/items/1
# open http://127.0.0.1:8000/docs
```

Or:

```bash
export SERVICE_URL="http://127.0.0.1:8000"
export SKIP_AUTH=1
./scripts/call_item.sh 1
```

---

## 2) How auth works on Cloud Run

Two layers:

1. **Cloud Run IAM** — only callers with `roles/run.invoker` can hit the service. They must send a Google ID token.
2. **Your app (`auth.py`)** — validates that Bearer token and checks its **audience** matches `TOKEN_AUDIENCE` (your service URL).

Client pattern:

```bash
TOKEN=$(gcloud auth print-identity-token --audiences="https://YOUR-SERVICE.run.app")
curl -H "Authorization: Bearer ${TOKEN}" \
  "https://YOUR-SERVICE.run.app/items/1"
```

`--audiences` must be the exact Cloud Run URL (no trailing slash). That same value goes into env var `TOKEN_AUDIENCE`.

---

## 3) Deploy to Cloud Run

Replace placeholders.

```bash
PROJECT=YOUR_GCP_PROJECT_ID
REGION=us-central1
SERVICE=inventory-api

gcloud config set project "$PROJECT"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Deploy (require authentication)
gcloud run deploy "$SERVICE" \
  --source . \
  --region="$REGION" \
  --project="$PROJECT" \
  --no-allow-unauthenticated \
  --set-env-vars="AUTH_DISABLED=false"
```

Copy the service URL from the deploy output, then set the audience:

```bash
SERVICE_URL=$(gcloud run services describe "$SERVICE" \
  --region="$REGION" --project="$PROJECT" \
  --format='value(status.url)')

gcloud run services update "$SERVICE" \
  --region="$REGION" --project="$PROJECT" \
  --update-env-vars="TOKEN_AUDIENCE=${SERVICE_URL}"
```

Grant yourself invoker permission:

```bash
gcloud run services add-iam-policy-binding "$SERVICE" \
  --region="$REGION" --project="$PROJECT" \
  --member="user:YOUR_EMAIL@example.com" \
  --role="roles/run.invoker"
```

---

## 4) Call the deployed API

```bash
export SERVICE_URL="https://inventory-api-XXXX-uc.a.run.app"
./scripts/call_item.sh 1
```

Or manually:

```bash
SERVICE_URL="https://inventory-api-XXXX-uc.a.run.app"
TOKEN=$(gcloud auth print-identity-token --audiences="${SERVICE_URL}")

curl -i "${SERVICE_URL}/items/1" \
  -H "Authorization: Bearer ${TOKEN}"
```

Expected JSON shape:

```json
{
  "item_id": 1,
  "item": {"name": "Milk", "price": 3.99, "brand": "Regular"},
  "requested_by": "you@example.com"
}
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `401` from your app | Wrong/missing token, or `TOKEN_AUDIENCE` ≠ service URL |
| `403` Forbidden (Cloud Run) | Your user lacks `roles/run.invoker` |
| `404 Item not found` | Use `item_id` 1, 2, or 3 |
| Local auth failures | Set `AUTH_DISABLED=true` while learning |

---

## Files

- `main.py` — routes
- `auth.py` — Bearer identity-token check
- `Dockerfile` — Cloud Run image
- `scripts/call_item.sh` — curl helper
