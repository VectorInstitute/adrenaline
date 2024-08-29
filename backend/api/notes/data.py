"""Data models for medical notes."""

from typing import List

from pydantic import BaseModel, Field


class MedicalNote(BaseModel):
    """
    Represents a medical note.

    Attributes
    ----------
    note_id : str
        The unique identifier for the note.
    subject_id : int
        The subject (patient) identifier.
    hadm_id : str
        The hospital admission identifier.
    text : str
        The content of the medical note.
    """

    note_id: str = Field(..., description="Unique identifier for the note")
    subject_id: int = Field(..., description="Subject (patient) identifier")
    hadm_id: str = Field(..., description="Hospital admission identifier")
    text: str = Field(..., description="Content of the medical note")


class Entity(BaseModel):
    """
    Represents an entity in a medical note.

    Attributes
    ----------
    entity_group : str
        The type of the entity.
    word : str
        The word that the entity represents.
    start : int
        The start index of the entity in the text.
    end : int
        The end index of the entity in the text.
    score : float
        The score of the entity.
    """

    entity_group: str
    word: str
    start: int
    end: int
    score: float


class NERResponse(BaseModel):
    """
    Represents the response from the NER service.

    Attributes
    ----------
    note_id : str
        The unique identifier for the note.
    text : str
        The content of the medical note.
    entities : List[Entity]
        The list of entities in the medical note.
    """

    note_id: str
    text: str
    entities: List[Entity]
