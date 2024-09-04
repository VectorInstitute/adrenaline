"""Backend API routes."""

import asyncio
import logging
import os
from datetime import timedelta
from enum import Enum
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from api.notes.data import MedicalNote, NERResponse
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


class CollectionName(str, Enum):
    """Enum for collection names."""

    MIMICIV_DISCHARGE = "mimiciv_discharge_notes"
    MIMICIV_RADIOLOGY = "mimiciv_radiology_notes"


@router.post("/extract_entities/{collection}/{note_id}", response_model=NERResponse)
async def extract_entities(
    collection: CollectionName,
    note_id: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> NERResponse:
    """
    Extract entities from a medical note.

    Parameters
    ----------
    collection : CollectionName
        The name of the collection containing the note.
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
        note = await db[collection.value].find_one({"note_id": note_id})

        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Medical note not found"
            )

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


@router.get("/collections", response_model=List[str])
async def get_collections(
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> List[str]:
    """
    Retrieve a list of available collections.

    Parameters
    ----------
    db : AsyncIOMotorDatabase
        The database connection.
    current_user : User
        The current authenticated user.

    Returns
    -------
    List[str]
        A list of collection names.

    Raises
    ------
    HTTPException
        If an error occurs during retrieval.
    """
    try:
        collections = await db.list_collection_names()
        return [col for col in collections if col.startswith("mimiciv_")]
    except Exception as e:
        logger.error(f"Error retrieving collections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving collections",
        ) from e


@router.get(
    "/medical_notes/{collection}/{patient_id}", response_model=List[MedicalNote]
)
async def get_medical_notes(
    collection: CollectionName,
    patient_id: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> List[MedicalNote]:
    """
    Retrieve medical notes for a specific patient from a specific collection.

    Parameters
    ----------
    collection : CollectionName
        The name of the collection to query.
    patient_id : str
        The ID of the patient.
    db : AsyncIOMotorDatabase
        The database connection.
    current_user : User
        The current authenticated user.

    Returns
    -------
    List[MedicalNote]
        A list of medical notes for the patient.

    Raises
    ------
    HTTPException
        If the patient ID is invalid, no notes are found, or an error during retrieval.
    """
    try:
        patient_id_int = int(patient_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid patient ID format. Must be an integer.",
        ) from e

    try:
        cursor = db[collection.value].find({"patient_id": patient_id_int})
        notes = await cursor.to_list(length=None)

        if not notes:
            logger.info(f"No medical notes found for patient ID {patient_id_int}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No medical notes found for patient ID {patient_id_int}",
            )

        return [MedicalNote(**note) for note in notes]
    except HTTPException as he:
        # Re-raise HTTP exceptions (including our 404)
        raise he
    except Exception as e:
        logger.error(
            f"Error retrieving medical notes for patient ID {patient_id_int}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving medical notes",
        ) from e


@router.get("/medical_notes/{collection}/note/{note_id}", response_model=MedicalNote)
async def get_medical_note(
    collection: CollectionName,
    note_id: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> MedicalNote:
    """
    Retrieve a specific medical note by its ID from a specific collection.

    Parameters
    ----------
    collection : CollectionName
        The name of the collection to query.
    note_id : str
        The ID of the medical note.
    db : AsyncIOMotorDatabase
        The database connection.
    current_user : User
        The current authenticated user.

    Returns
    -------
    MedicalNote
        The retrieved medical note.

    Raises
    ------
    HTTPException
        If the note is not found or an error occurs during retrieval.
    """
    try:
        note = await db[collection.value].find_one({"note_id": note_id})

        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Medical note not found"
            )

        return MedicalNote(**note)
    except Exception as e:
        logger.error(f"Error retrieving medical note with ID {note_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the medical note",
        ) from e


@router.get(
    "/medical_notes/{collection}/note/{note_id}/raw", response_class=PlainTextResponse
)
async def get_raw_medical_note(
    collection: CollectionName,
    note_id: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> str:
    """
    Retrieve the raw text of a specific medical note by its ID.

    Parameters
    ----------
    collection : CollectionName
        The name of the collection to query.
    note_id : str
        The ID of the medical note.
    db : AsyncIOMotorDatabase
        The database connection.
    current_user : User
        The current authenticated user.

    Returns
    -------
    str
        The raw text of the retrieved medical note.

    Raises
    ------
    HTTPException
        If the note is not found or an error occurs during retrieval.
    """
    try:
        note = await db[collection.value].find_one({"note_id": note_id})

        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Medical note not found"
            )

        return str(note["text"])
    except Exception as e:
        logger.error(f"Error retrieving raw medical note with ID {note_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the raw medical note",
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
