"""Routes for managing pages."""

import logging
from datetime import UTC, datetime
from typing import List

from bson import InvalidId, ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from api.pages.data import Page, Query, QueryAnswer
from api.patients.db import get_database
from api.users.auth import get_current_active_user
from api.users.data import User


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class CreatePageRequest(BaseModel):
    """Request body for creating a new page."""

    query: str


@router.post("/pages/create")
async def create_page(
    request: CreatePageRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> dict:
    """Create a new page for a user."""
    logger.info(f"Creating page for user {current_user.id} with query {request.query}")
    now = datetime.now(UTC)
    page_id = str(ObjectId())
    page_data = Page(
        id=page_id,
        user_id=str(current_user.id),
        query_answers=[QueryAnswer(query=Query(query=request.query), is_first=True)],
        created_at=now,
        updated_at=now,
    )
    await db.pages.insert_one(page_data.dict())
    return {"page_id": page_id}


@router.post("/pages/{page_id}/append")
async def append_to_page(
    page_id: str,
    question: str = Body(...),
    answer: str = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> dict:
    """Append a follow-up question and answer to an existing page."""
    existing_page = await db.pages.find_one(
        {"_id": ObjectId(page_id), "user_id": str(current_user.id)}
    )
    if not existing_page:
        raise HTTPException(status_code=404, detail="Page not found")

    updated_data = {
        "$push": {
            "query_answers": {
                "query": {"query": question},
                "answer": {"answer": answer, "reasoning": ""},
                "is_first": False,
            }
        },
        "$set": {"updated_at": datetime.now(UTC)},
    }
    await db.pages.update_one({"_id": ObjectId(page_id)}, updated_data)
    return {"status": "success"}


@router.get("/pages/history", response_model=List[Page])
async def get_user_page_history(
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> List[Page]:
    """Retrieve all pages for the current user."""
    cursor = db.pages.find({"user_id": str(current_user.id)}).sort("created_at", -1)
    pages = await cursor.to_list(length=None)

    return [Page(**page) for page in pages]


@router.get("/pages/{page_id}", response_model=Page)
async def get_page(
    page_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Page:
    """Retrieve a specific page."""
    try:
        _ = ObjectId(page_id)
    except InvalidId as e:
        raise HTTPException(status_code=400, detail="Invalid page ID") from e
    page = await db.pages.find_one({"id": page_id, "user_id": str(current_user.id)})
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    return Page(**page)
