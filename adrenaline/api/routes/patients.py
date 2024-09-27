"""Patient data API routes."""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.patients.cot import generate_cot_answer, generate_cot_steps
from api.patients.data import ClinicalNote, PatientData, QAPair, Query
from api.patients.db import get_database
from api.patients.ehr import fetch_patient_events, init_lazy_df
from api.patients.rag import EmbeddingManager, MilvusManager, retrieve_relevant_notes
from api.users.auth import (
    get_current_active_user,
)
from api.users.data import User


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
NER_SERVICE_TIMEOUT = 300  # 5 minutes
NER_SERVICE_PORT = os.getenv("NER_SERVICE_PORT", "8000")
NER_SERVICE_URL = f"http://clinical-ner-service-dev:{NER_SERVICE_PORT}/extract_entities"
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL")
MEDS_DATA_DIR = os.getenv(
    "MEDS_DATA_DIR", "/mnt/data/odyssey/meds/hosp/merge_to_MEDS_cohort/train"
)
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
EMBEDDING_SERVICE_HOST = os.getenv("EMBEDDING_SERVICE_HOST", "localhost")
EMBEDDING_SERVICE_PORT = os.getenv("EMBEDDING_SERVICE_PORT", "8004")
EMBEDDING_SERVICE_URL = (
    f"http://{EMBEDDING_SERVICE_HOST}:{EMBEDDING_SERVICE_PORT}/embeddings"
)
COLLECTION_NAME = "patient_notes"
TOP_K = 5

# Initialize the lazy DataFrame
init_lazy_df(MEDS_DATA_DIR)


EMBEDDING_MANAGER = EmbeddingManager(EMBEDDING_SERVICE_URL)
MILVUS_MANAGER = MilvusManager(MILVUS_HOST, MILVUS_PORT)
MILVUS_MANAGER.connect()


if not LLM_SERVICE_URL:
    raise ValueError("LLM_SERVICE_URL is not set")


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


@router.post("/pages/create")
async def create_page(
    original_query: str = Body(...),  # noqa: B008
    answer: str = Body(...),  # noqa: B008
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
):
    """Create a new page for a user."""
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
):
    """Append a follow-up question and answer to an existing page."""
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
):
    """Retrieve a specific page."""
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
):
    """Retrieve all pages for the current user."""
    cursor = db.pages.find({"user_id": str(current_user.id)})
    pages = await cursor.to_list(length=None)
    for page in pages:
        page["_id"] = str(page["_id"])  # Convert ObjectId to string
    return pages


@router.get("/patient_data/{patient_id}", response_model=PatientData)
async def get_patient_data(
    patient_id: int,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> PatientData:
    """
    Retrieve all data for a specific patient, i.e. clinical notes, QA pairs, and events.

    Parameters
    ----------
    patient_id : int
        The ID of the patient.
    db : AsyncIOMotorDatabase
        The database connection.
    current_user : User
        The current authenticated user.

    Returns
    -------
    PatientData
        The patient data.
    """
    try:
        patient = await db.patients.find_one({"patient_id": patient_id})

        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for patient ID {patient_id}",
            )

        notes = [ClinicalNote(**note) for note in patient.get("notes", [])]
        qa_pairs = [QAPair(**qa) for qa in patient.get("qa_pairs", [])]

        # Fetch events data
        events = fetch_patient_events(patient_id)

        return PatientData(
            patient_id=patient_id, notes=notes, qa_data=qa_pairs, events=events
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving data for patient ID {patient_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving patient data",
        ) from e


@router.get("/patient/{patient_id}/note/{note_id}", response_model=ClinicalNote)
async def get_patient_note(
    patient_id: int,
    note_id: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> ClinicalNote:
    """
    Retrieve a specific clinical note for a patient.

    Parameters
    ----------
    patient_id : int
        The ID of the patient.
    note_id : str
        The ID of the note to retrieve.
    db : AsyncIOMotorDatabase
        The database connection.
    current_user : User
        The current authenticated user.

    Returns
    -------
    ClinicalNote
        The clinical note.
    """
    try:
        patient = await db.patients.find_one(
            {"patient_id": patient_id, "notes.note_id": note_id},
            projection={"notes.$": 1},
        )

        if not patient or not patient.get("notes"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Clinical note not found"
            )

        note = patient["notes"][0]
        return ClinicalNote(**note)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving clinical note for patient ID {patient_id}, note ID {note_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the clinical note",
        ) from e


@router.get("/patient/{patient_id}/note/{note_id}/raw", response_model=str)
async def get_raw_clinical_note(
    patient_id: int,
    note_id: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> str:
    """
    Retrieve the raw text of a specific clinical note by its ID.

    Parameters
    ----------
    patient_id : int
        The ID of the patient.
    note_id : str
        The ID of the note to retrieve.
    db : AsyncIOMotorDatabase
        The database connection.
    current_user : User
        The current authenticated user.

    Returns
    -------
    str
        The raw text of the clinical note.
    """
    try:
        patient = await db.patients.find_one(
            {"patient_id": patient_id, "notes.note_id": note_id},
            projection={"notes.$": 1},
        )

        if not patient or not patient.get("notes"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Medical note not found"
            )

        return patient["notes"][0]["text"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving raw clinical note with ID {note_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the raw clinical note",
        ) from e


@router.get("/database_summary", response_model=Dict[str, Any])
async def get_database_summary(
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Dict[str, Any]:
    """
    Retrieve a summary of the entire database.

    Parameters
    ----------
    db : AsyncIOMotorDatabase
        The database connection.
    current_user : User
        The current authenticated user.

    Returns
    -------
    Dict[str, Any]
        The database summary.
    """
    try:
        pipeline = [
            {
                "$facet": {
                    "patient_count": [{"$count": "total"}],
                    "note_count": [
                        {"$project": {"note_count": {"$size": "$notes"}}},
                        {"$group": {"_id": None, "total": {"$sum": "$note_count"}}},
                    ],
                    "qa_count": [
                        {
                            "$project": {
                                "qa_count": {"$size": {"$ifNull": ["$qa_pairs", []]}}
                            }
                        },
                        {"$group": {"_id": None, "total": {"$sum": "$qa_count"}}},
                    ],
                }
            },
            {
                "$project": {
                    "total_patients": {"$arrayElemAt": ["$patient_count.total", 0]},
                    "total_notes": {"$arrayElemAt": ["$note_count.total", 0]},
                    "total_qa_pairs": {"$arrayElemAt": ["$qa_count.total", 0]},
                }
            },
        ]

        result = await db.patients.aggregate(pipeline).next()

        summary = {
            "total_patients": result["total_patients"] or 0,
            "total_notes": result["total_notes"] or 0,
            "total_qa_pairs": result["total_qa_pairs"] or 0,
        }

        logger.info(f"Database summary: {summary}")
        return summary
    except Exception as e:
        logger.error(f"Error retrieving database summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving database summary",
        ) from e
