"""Routes for managing pages."""

import logging
from datetime import datetime
from typing import Dict

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.patients.db import get_database
from api.users.auth import (
    get_current_active_user,
)
from api.users.data import User


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/pages/create")
async def create_page(
    original_query: str = Body(...),  # noqa: B008
    answer: str = Body(...),  # noqa: B008
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Dict[str, str]:
    """Create a new page for a user.

    Parameters
    ----------
    original_query : str
        The original query that the user asked.
    answer : str
        The answer to the original query.
    db : AsyncIOMotorDatabase
        The database to use.
    current_user : User
        The current active user.

    Returns
    -------
    Dict[str, str]
        The ID of the created page.
    """
    page_data = {
        "user_id": str(current_user.id),
        "original_query": original_query,
        "responses": [{"answer": answer, "created_at": datetime.utcnow()}],
        "follow_ups": [],
    }
    result = await db.pages.insert_one(page_data)
    return {"page_id": str(result.inserted_id)}


@router.post("/pages/{page_id}/append")
async def append_to_page(
    page_id: str,
    question: str = Body(...),  # noqa: B008
    answer: str = Body(...),  # noqa: B008
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Dict[str, str]:
    """Append a follow-up question and answer to an existing page.

    Parameters
    ----------
    page_id : str
        The ID of the page to append to.
    question : str
        The question to append.
    answer : str

    Returns
    -------
    Dict[str, str]
        The status of the operation.
    """
    existing_page = await db.pages.find_one(
        {"_id": ObjectId(page_id), "user_id": str(current_user.id)}
    )
    if not existing_page:
        raise HTTPException(status_code=404, detail="Page not found")

    updated_data = {
        "$push": {
            "follow_ups": {
                "question": question,
                "answer": answer,
                "created_at": datetime.utcnow(),
            }
        }
    }
    await db.pages.update_one({"_id": ObjectId(page_id)}, updated_data)
    return {"status": "success"}


@router.get("/pages/{page_id}")
async def get_page(
    page_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Dict[str, str]:
    """Retrieve a specific page.

    Parameters
    ----------
    page_id : str
        The ID of the page to retrieve.
    db : AsyncIOMotorDatabase
        The database to use.
    current_user : User

    Returns
    -------
    Dict[str, str]
        The page data.
    """
    page = await db.pages.find_one(
        {"_id": ObjectId(page_id), "user_id": str(current_user.id)}
    )
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    page["_id"] = str(page["_id"])  # Convert ObjectId to string
    return page


@router.get("/pages")
async def get_user_pages(
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Dict[str, str]:
    """Retrieve all pages for the current user.

    Parameters
    ----------
    db : AsyncIOMotorDatabase
        The database to use.
    current_user : User

    Returns
    -------
    Dict[str, str]
        The pages data.
    """
    cursor = db.pages.find({"user_id": str(current_user.id)})
    pages = await cursor.to_list(length=None)
    for page in pages:
        page["_id"] = str(page["_id"])  # Convert ObjectId to string
    return pages
