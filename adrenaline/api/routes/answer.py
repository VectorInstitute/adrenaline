"""Routes for generating answers."""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.patients.cot import generate_cot_answer, generate_cot_steps
from api.patients.data import Query
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


@router.post("/generate_cot_answer")
async def generate_cot_answer_endpoint(
    query: Query = Body(...),  # noqa: B008
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
):
    """Generate a Chain of Thought answer for a user query."""

    async def event_stream():
        try:
            mode = "patient" if query.patient_id else "general"
            context = ""

            if mode == "patient":
                patient_data = await get_patient_data(
                    query.patient_id, db, current_user
                )
                relevant_notes = await retrieve_relevant_notes(
                    query.query,
                    patient_data.notes,
                    EMBEDDING_MANAGER,
                    MILVUS_MANAGER,
                    query.patient_id,
                )
                context = "\n".join([note.text for note in relevant_notes])
            else:
                context = ""

            steps = await generate_cot_steps(query.query, mode, context)
            for step in steps:
                yield f"data: {json.dumps({'type': 'step', 'content': step})}\n\n"
                await asyncio.sleep(0.1)  # Simulate some delay between steps

            answer, reasoning = await generate_cot_answer(
                query.query, mode, context, steps
            )
            yield f"data: {json.dumps({'type': 'answer', 'content': {'answer': answer, 'reasoning': reasoning}})}\n\n"

            # Create a new page
            page_data = {
                "user_id": str(current_user.id),
                "original_query": query.query,
                "responses": [{"answer": answer, "created_at": datetime.utcnow()}],
                "follow_ups": [],
            }
            result = await db.pages.insert_one(page_data)
            page_id = str(result.inserted_id)

            yield f"data: {json.dumps({'type': 'page_id', 'content': page_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/generate_cot_steps")
async def generate_cot_steps_endpoint(
    query: Query = Body(...),  # noqa: B008
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Dict[str, List[Dict[str, str]]]:
    """Generate Chain of Thought steps for a user query."""
    try:
        mode = "patient" if query.patient_id else "general"
        context = ""

        if mode == "patient":
            logger.info(f"Retrieving patient data for patient ID {query.patient_id}")
            patient_data = await get_patient_data(query.patient_id, db, current_user)
            relevant_notes = await retrieve_relevant_notes(
                query.query,
                patient_data.notes,
                EMBEDDING_MANAGER,
                MILVUS_MANAGER,
                query.patient_id,
            )
            context = "\n".join([note.text for note in relevant_notes])

        steps = await generate_cot_steps(query.query, mode, context)
        return {"cot_steps": steps}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}"
        ) from e
