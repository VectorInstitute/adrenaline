"""Patient data API routes."""

import logging
import os
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.patients.data import ClinicalNote, Event, PatientData, QAPair
from api.patients.db import get_database
from api.patients.ehr import (
    fetch_latest_medications,
    fetch_patient_encounters,
    fetch_patient_events,
    fetch_patient_events_by_type,
    init_lazy_df,
)
from api.users.auth import (
    get_current_active_user,
)
from api.users.data import User


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration

MEDS_DATA_DIR = os.getenv(
    "MEDS_DATA_DIR", "/mnt/data/odyssey/meds/hosp/merge_to_MEDS_cohort/train"
)

# Initialize the lazy DataFrame
init_lazy_df(MEDS_DATA_DIR)


@router.get("/patient_data/{patient_id}/medications", response_model=str)
async def get_latest_medications(
    patient_id: int,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> str:
    """Retrieve latest medications for a specific patient.

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
    str
        The latest medications for the patient.
    """
    try:
        medications = fetch_latest_medications(patient_id)
        logger.info(f"Retrieved medications for patient ID {patient_id} {medications}")
        return medications
    except Exception as e:
        logger.error(
            f"Error retrieving medications for patient ID {patient_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving medications",
        ) from e


@router.get(
    "/patient_data/{patient_id}/events/{event_type}", response_model=List[Event]
)
async def get_patient_events_by_type(
    patient_id: int,
    event_type: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> List[Event]:
    """Retrieve events filtered by event_type for a specific patient.

    Parameters
    ----------
    patient_id : int
        The ID of the patient.
    event_type : str
        The type of event to filter by.
    db : AsyncIOMotorDatabase
        The database connection.
    current_user : User
        The current authenticated user.

    Returns
    -------
    List[Event]
        List of events of the specified type for the patient.
    """
    try:
        return fetch_patient_events_by_type(patient_id, event_type)
    except Exception as e:
        logger.error(f"Error retrieving events for patient ID {patient_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving patient events",
        ) from e


@router.get("/patient_data/encounters/{patient_id}", response_model=List[dict])
async def get_encounters(
    patient_id: int,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> List[dict]:
    """
    Retrieve encounters with admission dates for a patient.

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
    List[dict]
        List of encounters with their admission dates.
    """
    try:
        return fetch_patient_encounters(patient_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving encounters for patient ID {patient_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving patient encounters",
        ) from e


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
