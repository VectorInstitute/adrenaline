"""Backend API routes."""

import asyncio
import logging
import os
from datetime import timedelta
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from api.notes.data import ClinicalNote, NERResponse, PatientData, QAPair
from api.notes.db import get_database
from api.users.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    get_current_active_user,
)
from api.users.crud import (
    create_user,
    delete_user,
    get_users,
    update_user,
    update_user_password,
)
from api.users.data import User, UserCreate
from api.users.db import get_async_session
from api.users.utils import verify_password


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
NER_SERVICE_TIMEOUT = 300  # 5 minutes
NER_SERVICE_PORT = os.getenv("NER_SERVICE_PORT", "8000")
NER_SERVICE_URL = f"http://clinical-ner-service-dev:{NER_SERVICE_PORT}/extract_entities"
LLM_SERVICE_HOST = os.getenv("LLM_SERVICE_HOST")
LLM_SERVICE_PORT = os.getenv("LLM_SERVICE_PORT", "8080")
LLM_SERVICE_URL = f"http://{LLM_SERVICE_HOST}:{LLM_SERVICE_PORT}/v1"


@router.get("/database_summary", response_model=Dict[str, Any])
async def get_database_summary(
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
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


@router.get("/patient_data/{patient_id}", response_model=PatientData)
async def get_patient_data(
    patient_id: int,
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> PatientData:
    """
    Retrieve all data for a specific patient, including clinical notes and QA pairs.

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

        return PatientData(patient_id=patient_id, notes=notes, qa_data=qa_pairs)

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
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
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
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
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


@router.post("/extract_entities/{patient_id}/{note_id}", response_model=NERResponse)
async def extract_entities(
    patient_id: int,
    note_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # noqa: B008
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


@router.post("/auth/signin")
async def signin(
    request: Request,
    db: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> Dict[str, Any]:
    """
    Authenticate a user and return an access token.

    Parameters
    ----------
    request : Request
        The incoming request object.
    db : AsyncSession
        The database session.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing the access token, token type, and user information.

    Raises
    ------
    HTTPException
        If the credentials are invalid or missing.
    """
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username and password are required",
        )

    user = await authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "role": user.role},
    }


@router.post("/auth/signout")
async def signout(
    request: Request,
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Dict[str, str]:
    """
    Sign out the current user.

    Parameters
    ----------
    request : Request
        The incoming request object.
    current_user : User
        The current authenticated user.

    Returns
    -------
    Dict[str, str]
        A dictionary containing a success message.

    Raises
    ------
    HTTPException
        If the user is not authenticated.
    """
    return {"message": "Successfully signed out"}


@router.get("/auth/session")
async def get_session(
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Dict[str, Any]:
    """
    Get the current user's session information.

    Parameters
    ----------
    current_user : User
        The current authenticated user.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing the user's session information.

    Raises
    ------
    HTTPException
        If the user is not authenticated.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role,
        }
    }


@router.post("/auth/signup", response_model=User)
async def signup(
    user: UserCreate,
    current_user: User = Depends(get_current_active_user),  # noqa: B008
    db: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> User:
    """
    Create a new user (admin only).

    Parameters
    ----------
    user : UserCreate
        The user data to create.
    current_user : User
        The current authenticated user.
    db : AsyncSession
        The asynchronous database session.

    Returns
    -------
    User
        The created user.

    Raises
    ------
    HTTPException
        If the current user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create users",
        )
    return await create_user(db=db, user=user)


@router.get("/users", response_model=List[User])
async def get_users_route(
    current_user: User = Depends(get_current_active_user),  # noqa: B008
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> List[User]:
    """
    Get a list of users (admin only).

    Parameters
    ----------
    current_user : User
        The current authenticated user.
    skip : int, optional
        The number of users to skip, by default 0.
    limit : int, optional
        The maximum number of users to return, by default 100.
    db : AsyncSession
        The asynchronous database session.

    Returns
    -------
    List[User]
        A list of users.

    Raises
    ------
    HTTPException
        If the current user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view users"
        )
    return list(await get_users(db, skip=skip, limit=limit))


@router.put("/users/{user_id}", response_model=User)
async def update_user_route(
    user_id: int,
    user_update: UserCreate,
    current_user: User = Depends(get_current_active_user),  # noqa: B008
    db: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> User:
    """
    Update a user (admin only).

    Parameters
    ----------
    user_id : int
        The ID of the user to update.
    user_update : UserCreate
        The updated user data.
    current_user : User
        The current authenticated user.
    db : AsyncSession
        The asynchronous database session.

    Returns
    -------
    User
        The updated user.

    Raises
    ------
    HTTPException
        If the current user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update users",
        )
    return await update_user(db=db, user_id=user_id, user_update=user_update)


@router.post("/auth/update-password")
async def update_password(
    request: Request,
    current_user: User = Depends(get_current_active_user),  # noqa: B008
    db: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> Dict[str, str]:
    """
    Update the current user's password.

    Parameters
    ----------
    request : Request
        The incoming request object.
    current_user : User
        The current authenticated user.
    db : AsyncSession
        The database session.

    Returns
    -------
    Dict[str, str]
        A dictionary containing a success message.

    Raises
    ------
    HTTPException
        If the current password is incorrect or the new password is invalid.
    """
    data = await request.json()
    current_password = data.get("currentPassword")
    new_password = data.get("newPassword")

    if not current_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Current password and new password are required",
        )

    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password",
        )

    try:
        await update_user_password(db, current_user.id, new_password)
        await db.commit()
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the password",
        ) from e

    return {"message": "Password updated successfully"}


@router.delete("/users/{user_id}")
async def delete_user_route(
    user_id: int,
    current_user: User = Depends(get_current_active_user),  # noqa: B008
    db: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> Dict[str, str]:
    """
    Delete a user (admin only).

    Parameters
    ----------
    user_id : int
        The ID of the user to delete.
    current_user : User
        The current authenticated user.
    db : AsyncSession
        The asynchronous database session.

    Returns
    -------
    Dict[str, str]
        A dictionary containing a success message.

    Raises
    ------
    HTTPException
        If the current user is not an admin or if the user is not found.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete users",
        )

    success = await delete_user(db=db, user_id=user_id)
    if success:
        return {"message": "User deleted successfully"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
