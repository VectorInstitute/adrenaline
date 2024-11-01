"""Routes for generating answers and performing cohort searches."""

import logging
import os
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.pages.data import Query
from api.patients.answer import generate_answer
from api.patients.data import CohortSearchQuery, CohortSearchResult
from api.patients.db import get_database
from api.patients.rag import (
    ChromaManager,
    EmbeddingManager,
    NERManager,
    RAGManager,
    retrieve_relevant_notes,
)
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

CHROMA_HOST = os.getenv("CHROMA_SERVICE_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_SERVICE_PORT", "8000"))
COLLECTION_NAME = "patient_notes"
TOP_K = 5
EMBEDDING_SERVICE_HOST = os.getenv("EMBEDDING_SERVICE_HOST", "localhost")
EMBEDDING_SERVICE_PORT = os.getenv("EMBEDDING_SERVICE_PORT", "8004")
EMBEDDING_SERVICE_URL = (
    f"http://{EMBEDDING_SERVICE_HOST}:{EMBEDDING_SERVICE_PORT}/embeddings"
)
NER_SERVICE_PORT = os.getenv("NER_SERVICE_PORT", "8000")
NER_SERVICE_URL = f"http://clinical-ner-service-dev:{NER_SERVICE_PORT}/extract_entities"

EMBEDDING_MANAGER = EmbeddingManager(EMBEDDING_SERVICE_URL)
CHROMA_MANAGER = ChromaManager(CHROMA_HOST, CHROMA_PORT, COLLECTION_NAME)
CHROMA_MANAGER.connect()
NER_MANAGER = NERManager(NER_SERVICE_URL)
RAG_MANAGER = RAGManager(EMBEDDING_MANAGER, CHROMA_MANAGER, NER_MANAGER)


@router.post("/generate_answer")
async def generate_answer_endpoint(
    query: Query = Body(...),  # noqa: B008
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Dict[str, str]:
    """Generate an answer using RAG."""
    try:
        logger.info(f"Processing query: {query.query}")

        if not query.query:
            raise HTTPException(status_code=400, detail="Query string is empty")
        if not query.page_id:
            raise HTTPException(status_code=400, detail="Page ID is missing")

        mode = "patient" if query.patient_id else "general"
        context = ""

        if mode == "patient":
            if not query.patient_id:
                raise HTTPException(
                    status_code=400,
                    detail="Patient ID is required for patient-specific queries",
                )

            logger.info(f"Retrieving relevant notes for patient {query.patient_id}")
            relevant_notes = await retrieve_relevant_notes(
                user_query=query.query,
                embedding_manager=EMBEDDING_MANAGER,
                chroma_manager=CHROMA_MANAGER,
                patient_id=query.patient_id,
                top_k=TOP_K,
            )

            if not relevant_notes:
                logger.warning(
                    f"No relevant notes found for patient {query.patient_id}"
                )
                context = "No relevant patient notes found."
            else:
                # Format notes with metadata for better context
                context_parts = []
                for note in relevant_notes:
                    note_context = (
                        f"Note Type: {note['note_type']}\n"
                        f"Date: {datetime.fromtimestamp(note['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Content: {note['note_text']}\n"
                        f"Relevance Score: {note['distance']:.3f}\n"
                    )
                    context_parts.append(note_context)
                context = "\n---\n".join(context_parts)

        logger.info("Generating answer")
        answer, reasoning = await generate_answer(
            user_query=query.query,
            mode=mode,
            context=context,
        )

        # Update the page with the new answer
        update_result = await db.pages.update_one(
            {"id": query.page_id, "user_id": str(current_user.id)},
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

        if update_result.modified_count == 0:
            logger.warning("Answer was not stored in the database")

        return {
            "answer": answer,
            "reasoning": reasoning,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating answer: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while generating the answer: {str(e)}",
        ) from e


@router.post("/cohort_search")
async def cohort_search_endpoint(
    query: CohortSearchQuery = Body(...),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> List[CohortSearchResult]:
    """Perform a cohort search across all patients."""
    try:
        logger.info(f"Received cohort search query: {query.query}")

        if not query.query:
            raise ValueError("Query string is empty")

        cohort_results = await RAG_MANAGER.cohort_search(query.query, query.top_k)
        logger.info(f"Found {len(cohort_results)} patients matching the query")

        return [
            CohortSearchResult(
                patient_id=patient_id,
                note_type=note_details["note_type"],
                note_text=note_details["note_text"][
                    :500
                ],  # Limit to first 500 characters
                timestamp=note_details["timestamp"],
                similarity_score=note_details["distance"],
            )
            for patient_id, note_details in cohort_results
        ]

    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        logger.error(
            f"Unexpected error in cohort_search_endpoint: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        ) from e
