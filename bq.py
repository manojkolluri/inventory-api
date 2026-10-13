"""BigQuery insert helper."""

from __future__ import annotations

import json
import os
from typing import Any

from google.cloud import bigquery


def _table_id() -> str:
    project = os.getenv("GCP_PROJECT_ID", "").strip()
    dataset = os.getenv("BQ_DATASET", "").strip()
    table = os.getenv("BQ_TABLE", "").strip()
    if not project or not dataset or not table:
        raise RuntimeError(
            "Set GCP_PROJECT_ID, BQ_DATASET, and BQ_TABLE env vars on Cloud Run"
        )
    return f"{project}.{dataset}.{table}"


def insert_row(*, user_id: str, session_id: str, payload: dict[str, Any]) -> str:
    """Insert one row. Returns the fully-qualified table id."""
    table_id = _table_id()
    client = bigquery.Client(project=os.environ["GCP_PROJECT_ID"])

    # BigQuery JSON columns expect a JSON-encoded string for streaming insert.
    row = {
        "User_id": user_id,
        "session_id": session_id,
        "payload": json.dumps(payload),
    }
    errors = client.insert_rows_json(table_id, [row])
    if errors:
        raise RuntimeError(f"BigQuery insert errors: {errors}")
    return table_id
