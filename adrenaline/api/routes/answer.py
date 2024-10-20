"""Routes for generating answers."""

import logging
import os
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Body, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.pages.data import Query
from api.patients.answer import generate_answer
from api.patients.db import get_database
from api.patients.rag import EmbeddingManager, MilvusManager, retrieve_relevant_notes
from api.users.auth import get_current_active_user
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
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))
COLLECTION_NAME = "patient_notes"
TOP_K = 5
EMBEDDING_SERVICE_HOST = os.getenv("EMBEDDING_SERVICE_HOST", "localhost")
EMBEDDING_SERVICE_PORT = os.getenv("EMBEDDING_SERVICE_PORT", "8004")
EMBEDDING_SERVICE_URL = (
    f"http://{EMBEDDING_SERVICE_HOST}:{EMBEDDING_SERVICE_PORT}/embeddings"
)
EMBEDDING_MANAGER = EmbeddingManager(EMBEDDING_SERVICE_URL)
MILVUS_MANAGER = MilvusManager(MILVUS_HOST, MILVUS_PORT)
MILVUS_MANAGER.connect()


@router.post("/generate_cot_answer")
async def generate_cot_answer_endpoint(
    query: Query = Body(...),  # noqa: B008
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Dict[str, str]:
    """Generate a COT answer."""
    try:
        logger.info(f"Received query for answer generation: {query}")

        if not query.query:
            raise ValueError("Query string is empty")
        if not query.page_id:
            raise ValueError("Page ID is missing")

        mode = "patient" if query.patient_id else "general"
        context = ""

        if mode == "patient":
            if not query.patient_id:
                raise ValueError("Patient ID is missing for patient mode")

            logger.info(f"Fetching relevant notes for patient ID: {query.patient_id}")
            relevant_notes = await retrieve_relevant_notes(
                user_query=query.query,
                embedding_manager=EMBEDDING_MANAGER,
                milvus_manager=MILVUS_MANAGER,
                patient_id=query.patient_id,
                top_k=TOP_K,
            )
            context = "\n".join(
                [
                    f"Note Type: {note['note_type']}\n"
                    f"Timestamp: {datetime.fromtimestamp(note['timestamp'])}\n"
                    f"Content: {note['note_text']}\n"
                    for note in relevant_notes
                ]
            )

        logger.info("Generating answer")
        answer, reasoning = await generate_answer(
            user_query=query.query,
            mode=mode,
            context=context,
        )

        logger.info("Updating page with generated answer")
        page = await db.pages.find_one(
            {"id": query.page_id, "user_id": str(current_user.id)}
        )
        if not page:
            raise HTTPException(status_code=404, detail="Page not found")

        await db.pages.update_one(
            {"_id": page["_id"]},
            {
                "$set": {
                    "query_answers.$[elem].answer": {
                        "answer": answer,
                        "reasoning": reasoning,
                    },
                }
            },
            array_filters=[{"elem.query.query": query.query}],
        )

        logger.info("Successfully generated and stored COT answer")
        return {
            "answer": answer,
            "reasoning": reasoning,
        }

    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except HTTPException as he:
        logger.error(f"HTTP exception: {he.detail}")
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in generate_cot_answer_endpoint: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        ) from e
