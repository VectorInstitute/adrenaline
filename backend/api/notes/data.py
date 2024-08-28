"""Data models for medical notes."""

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