"""Routes for generating answers."""

import logging
import os

from fastapi import APIRouter, Body, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.pages.data import Query
from api.patients.cot import generate_cot_answer, generate_cot_steps
from api.patients.db import get_database
from api.patients.rag import EmbeddingManager, MilvusManager, retrieve_relevant_notes
from api.routes.patients import get_patient_data
from api.users.auth import (
    get_current_active_user,
)
from api.users.data import User


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter()


# Configuration
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL")
if not LLM_SERVICE_URL:
    raise ValueError("LLM_SERVICE_URL is not set")

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
EMBEDDING_SERVICE_HOST = os.getenv("EMBEDDING_SERVICE_HOST", "localhost")
EMBEDDING_SERVICE_PORT = os.getenv("EMBEDDING_SERVICE_PORT", "8004")
EMBEDDING_SERVICE_URL = (
    f"http://{EMBEDDING_SERVICE_HOST}:{EMBEDDING_SERVICE_PORT}/embeddings"
)
COLLECTION_NAME = "patient_notes"
TOP_K = 5
EMBEDDING_MANAGER = EmbeddingManager(EMBEDDING_SERVICE_URL)
MILVUS_MANAGER = MilvusManager(MILVUS_HOST, MILVUS_PORT)
MILVUS_MANAGER.connect()


@router.post("/generate_cot_steps")
async def generate_cot_steps_endpoint(
    query: Query = Body(...),  # noqa: B008
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
):
    """Generate COT steps.

    Parameters
    ----------
    query : Query
        The query to generate steps for.
    db : AsyncIOMotorDatabase
        The database to use.
    current_user : User
        The current user.

    Returns
    -------
    List[Step]
        The generated steps.
    """
    try:
        mode = "patient" if query.patient_id else "general"
        context = ""

        if mode == "patient":
            patient_data = await get_patient_data(query.patient_id, db, current_user)
            relevant_notes = await retrieve_relevant_notes(
                user_query=query.query,
                notes=patient_data.notes,
                embedding_manager=EMBEDDING_MANAGER,
                milvus_manager=MILVUS_MANAGER,
                patient_id=query.patient_id,
            )
            context = "\n".join([note.text for note in relevant_notes])

        steps = await generate_cot_steps(
            user_query=query.query,
            mode=mode,
            context=context,
        )

        # Update the page with the generated steps
        page = await db.pages.find_one({"query_answers.query.query": query.query})
        if page:
            await db.pages.update_one(
                {"_id": page["_id"]},
                {
                    "$set": {
                        "query_answers.$[elem].query.steps": [
                            step.dict() for step in steps
                        ]
                    }
                },
                array_filters=[{"elem.query.query": query.query}],
            )

        return {"cot_steps": [step.dict() for step in steps]}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}"
        ) from e


@router.post("/generate_cot_answer")
async def generate_cot_answer_endpoint(
    query: Query = Body(...),  # noqa: B008
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
):
    """Generate a COT answer.

    Parameters
    ----------
    query : Query
        The query to generate an answer for.
    db : AsyncIOMotorDatabase
        The database to use.
    current_user : User
        The current user.

    Returns
    -------
    Dict[str, str]
        The generated answer and reasoning.
    """
    try:
        mode = "patient" if query.patient_id else "general"
        context = ""

        if mode == "patient":
            patient_data = await get_patient_data(query.patient_id, db, current_user)
            relevant_notes = await retrieve_relevant_notes(
                user_query=query.query,
                notes=patient_data.notes,
                embedding_manager=EMBEDDING_MANAGER,
                milvus_manager=MILVUS_MANAGER,
                patient_id=query.patient_id,
            )
            context = "\n".join([note.text for note in relevant_notes])

        if not query.steps:
            raise HTTPException(
                status_code=400, detail="Steps are required to generate an answer"
            )

        answer, reasoning = await generate_cot_answer(
            user_query=query.query,
            steps=query.steps,
            mode=mode,
            context=context,
        )

        # Update the page with the generated answer
        page = await db.pages.find_one({"query_answers.query.query": query.query})
        if page:
            await db.pages.update_one(
                {"_id": page["_id"]},
                {
                    "$set": {
                        "query_answers.$[elem].answer": {
                            "answer": answer,
                            "reasoning": reasoning,
                        }
                    }
                },
                array_filters=[{"elem.query.query": query.query}],
            )

        return {
            "answer": answer,
            "reasoning": reasoning,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}"
        ) from e
