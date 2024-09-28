"""Named Entity Recognition API routes."""

import asyncio
import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.ner.data import NERResponse
from api.patients.db import get_database
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


@router.post("/extract_entities/{patient_id}/{note_id}", response_model=NERResponse)
async def extract_entities(
    patient_id: int,
    note_id: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> NERResponse:
    """
    Extract entities from a clinical note.

    Parameters
    ----------
    patient_id : int
        The ID of the patient.
    note_id : str
        The ID of the note to process.
    db : AsyncIOMotorDatabase
        The database connection.
    current_user : User
        The current authenticated user.

    Returns
    -------
    NERResponse
        The response containing the extracted entities.

    Raises
    ------
    HTTPException
        If the note is not found or if there's an error in entity extraction.
    """
    try:
        # Fetch the note from the database
        patient = await db.patients.find_one(
            {"patient_id": patient_id, "notes.note_id": note_id},
            projection={"notes.$": 1},
        )

        if not patient or not patient.get("notes"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Medical note not found"
            )

        note = patient["notes"][0]
        original_text = note["text"]

        # Call the clinical NER service with increased timeout
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(NER_SERVICE_TIMEOUT)
        ) as client:
            try:
                response = await client.post(
                    NER_SERVICE_URL, json={"text": original_text}
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error(f"HTTP error occurred: {exc}")
                raise HTTPException(
                    status_code=exc.response.status_code,
                    detail=f"Error calling clinical NER service: {exc.response.text}",
                ) from exc
            except httpx.RequestError as exc:
                logger.error(f"An error occurred while requesting {exc.request.url!r}.")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Clinical NER service is unavailable",
                ) from exc
            except asyncio.TimeoutError as exc:
                logger.error("Request to clinical NER service timed out")
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Clinical NER service request timed out",
                ) from exc

        ner_response = response.json()
        ner_response["note_id"] = note_id

        return NERResponse(**ner_response)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in extract_entities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request",
        ) from e
