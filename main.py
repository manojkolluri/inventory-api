"""
Cloud Run API with Google identity-token Bearer auth.

- GET  /health
- GET  /items/{item_id}   (demo)
- POST /rows              → insert into BigQuery
"""

from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Path, status
from pydantic import BaseModel, Field

from auth import AuthenticatedUser, require_user
from bq import insert_row

app = FastAPI(
    title="Inventory / Telemetry API",
    description=(
        "Cloud Run API with Google identity-token Bearer auth. "
        "POST /rows writes User_id, session_id, payload into BigQuery."
    ),
    version="1.1.0",
)

INVENTORY = {
    1: {"name": "Milk", "price": 3.99, "brand": "Regular"},
    2: {"name": "Eggs", "price": 4.49, "brand": "Farm Fresh"},
    3: {"name": "Bread", "price": 2.99, "brand": "Bakery"},
}


class RowRequest(BaseModel):
    User_id: str = Field(..., min_length=1, description="User id column")
    session_id: str = Field(..., min_length=1, description="Session id column")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary JSON stored in the payload column",
    )


class RowResponse(BaseModel):
    inserted: bool
    table: str
    requested_by: str
    row: RowRequest


@app.get("/health")
def health():
    return {"status": "ok", "auth": "v3"}


@app.get("/items/{item_id}")
def get_item(
    item_id: Annotated[int, Path(description="Item ID to fetch", ge=1)],
    user: Annotated[AuthenticatedUser, Depends(require_user)],
):
    item = INVENTORY.get(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found",
        )
    return {
        "item_id": item_id,
        "item": item,
        "requested_by": user.email,
    }


@app.post(
    "/rows",
    response_model=RowResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_row(
    body: RowRequest,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
):
    """Insert one BigQuery row: User_id, session_id, payload."""
    try:
        table_id = insert_row(
            user_id=body.User_id,
            session_id=body.session_id,
            payload=body.payload,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write to BigQuery: {exc}",
        ) from exc

    return RowResponse(
        inserted=True,
        table=table_id,
        requested_by=user.email,
        row=body,
    )
