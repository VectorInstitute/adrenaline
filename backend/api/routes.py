"""Backend API routes."""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from api.notes.data import Entity, MedicalNote, NERResponse
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


def preprocess_text(text: str) -> Tuple[str, List[int]]:
    """
    Preprocess the input text by removing non-printable characters.

    Parameters
    ----------
    text : str
        The input text to preprocess.

    Returns
    -------
    Tuple[str, List[int]]
        A tuple with the preprocessed text and a list of removed character indices.
    """
    preprocessed = []
    removed_indices = []
    for i, char in enumerate(text):
        if char.isprintable() or char.isspace():
            preprocessed.append(char)
        else:
            removed_indices.append(i)
    return "".join(preprocessed), removed_indices


def adjust_entity_positions(
    entities: List[Entity], removed_indices: List[int]
) -> List[Entity]:
    """
    Adjust entity positions based on removed character indices.

    Parameters
    ----------
    entities : List[Entity]
        The list of entities to adjust.
    removed_indices : List[int]
        The list of indices of removed characters.

    Returns
    -------
    List[Entity]
        The list of entities with adjusted positions.
    """
    adjusted_entities = []
    for entity in entities:
        start = entity.start + sum(1 for i in removed_indices if i < entity.start)
        end = entity.end + sum(1 for i in removed_indices if i < entity.end)
        adjusted_entities.append(
            Entity(
                entity_group=entity.entity_group,
                word=entity.word,
                start=start,
                end=end,
                score=entity.score,
            )
        )
    return adjusted_entities


@router.post("/extract_entities/{note_id}", response_model=NERResponse)
async def extract_entities(
    note_id: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> NERResponse:
    """
    Extract entities from a medical note.

    Parameters
    ----------
    note_id : str
        The ID of the medical note.
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
        If the note is not found or an error occurs during processing.
    """
    try:
        collection = db.medical_notes
        note = await collection.find_one({"note_id": note_id})

        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Medical note not found"
            )

        original_text = note["text"]
        preprocessed_text, removed_indices = preprocess_text(original_text)

        ner_url = "http://cyclops.cluster.local:8003/ner"
        async with AsyncClient() as client:
            response = await client.post(
                ner_url,
                json={"text": preprocessed_text},
                timeout=60.0,
            )
            response.raise_for_status()
            ner_result = response.json()

            if "entities" not in ner_result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="NER endpoint returned unexpected response",
                )

            preprocessed_entities = [
                Entity(**entity) for entity in ner_result["entities"]
            ]
            adjusted_entities = adjust_entity_positions(
                preprocessed_entities, removed_indices
            )

        logger.info(f"Extracted {len(adjusted_entities)} entities from note {note_id}")
        return NERResponse(
            note_id=note_id, text=original_text, entities=adjusted_entities
        )

    except Exception as e:
        logger.error(f"Unexpected error in extract_entities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e


@router.get("/medical_notes/{patient_id}", response_model=List[MedicalNote])
async def get_medical_notes(
    patient_id: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> List[MedicalNote]:
    """
    Retrieve medical notes for a specific patient.

    Parameters
    ----------
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
        If the patient ID is invalid or an error occurs during retrieval.
    """
    try:
        patient_id_int = int(patient_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid patient ID format. Must be an integer.",
        ) from e

    try:
        collection = db.medical_notes
        cursor = collection.find({"subject_id": patient_id_int})
        notes = await cursor.to_list(length=None)

        if not notes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No medical notes found for this patient",
            )

        return [MedicalNote(**note) for note in notes]
    except Exception as e:
        logger.error(
            f"Error retrieving medical notes for patient ID {patient_id_int}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving medical notes",
        ) from e


@router.get("/medical_notes/note/{note_id}", response_model=MedicalNote)
async def get_medical_note(
    note_id: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> MedicalNote:
    """
    Retrieve a specific medical note by its ID.

    Parameters
    ----------
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
        collection = db.medical_notes
        note = await collection.find_one({"note_id": note_id})

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


@router.get("/medical_notes/note/{note_id}/raw", response_class=PlainTextResponse)
async def get_raw_medical_note(
    note_id: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_database),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> str:
    """
    Retrieve the raw text of a specific medical note by its ID.

    Parameters
    ----------
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
        collection = db.medical_notes
        note = await collection.find_one({"note_id": note_id})

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
