"""
Basic Cloud Run API.

- GET /health          → no app auth (useful for checks)
- GET /items/{item_id} → requires Authorization: Bearer <Google identity token>
"""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, status

from auth import AuthenticatedUser, require_user

app = FastAPI(
    title="Inventory API",
    description=(
        "Demo API for Cloud Run + Google identity-token Bearer auth. "
        "Call with: gcloud auth print-identity-token --audiences=<SERVICE_URL>"
    ),
    version="1.0.0",
)

# Fake "database" for learning
INVENTORY = {
    1: {"name": "Milk", "price": 3.99, "brand": "Regular"},
    2: {"name": "Eggs", "price": 4.49, "brand": "Farm Fresh"},
    3: {"name": "Bread", "price": 2.99, "brand": "Bakery"},
}


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
