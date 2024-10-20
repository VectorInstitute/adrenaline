"""Data models for patient data."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class QAPair(BaseModel):
    """
    Represents a question-answer pair.

    Attributes
    ----------
    question : str
        The question.
    answer : str
        The answer to the question.
    """

    question: str
    answer: str


class ClinicalNote(BaseModel):
    """
    Represents a clinical note.

    Attributes
    ----------
    note_id : str
        The unique identifier for the note.
    encounter_id : str
        The hospital admission/encounter identifier.
    timestamp : datetime
        The timestamp of the note.
    text : str
        The content of the clinical note.
    note_type : str
        The type of the note (e.g., DS, AD, RR, AR).
    """

    note_id: str = Field(..., description="Unique identifier for the note")
    encounter_id: str = Field(
        ..., description="Hospital admission/encounter identifier"
    )
    timestamp: datetime = Field(..., description="Timestamp of the note")
    text: str = Field(..., description="Content of the clinical note")
    note_type: str = Field(..., description="Type of the note (e.g., DS, AD, RR, AR)")

    @field_validator("encounter_id", mode="before")
    @classmethod
    def convert_encounter_id_to_str(cls, v):
        """Convert the encounter_id to a string."""
        return str(v)


class Event(BaseModel):
    """
    Represents an event in a patient's medical history.

    Attributes
    ----------
    patient_id : int
        The patient identifier.
    encounter_id : Optional[str]
        The hospital admission/encounter identifier.
    code : str
        The code of the event.
    timestamp : Optional[datetime]
        The timestamp of the event.
    numeric_value : Optional[float]
        The numeric value of the event.
    text_value : Optional[str]
        The text value of the event.
    """

    patient_id: int
    encounter_id: Optional[str]
    code: str
    timestamp: Optional[datetime]
    numeric_value: Optional[float]
    text_value: Optional[str]


class PatientData(BaseModel):
    """
    Represents all data for a patient.

    Attributes
    ----------
    patient_id : int
        The patient identifier.
    notes : List[ClinicalNote]
        A list of clinical notes for the patient.
    qa_data : Optional[List[QAPair]]
        An optional list of question-answer pairs for the patient.
    events : List[Event]
        A list of events in the patient's medical history.
    """

    patient_id: int
    notes: List[ClinicalNote]
    qa_data: Optional[List[QAPair]] = None
    events: List[Event]
