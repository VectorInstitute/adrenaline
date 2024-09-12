"""Data models for patient data."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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


class MetaAnnotation(BaseModel):
    """
    Represents a meta-annotation in a medical note.

    Attributes
    ----------
    value: str
        The value of the meta-annotation.
    confidence: float
        The confidence of the meta-annotation.
    name: str

    """

    value: str
    confidence: float
    name: str


class Entity(BaseModel):
    """
    Represents an entity in a medical note.

    Attributes
    ----------
    pretty_name: str
        The pretty name of the entity.
    cui: str
        The CUI of the entity.
    type_ids: List[str]
        The type IDs of the entity.
    types: List[str]
        The types of the entity.
    source_value: str
        The source value of the entity.
    detected_name: str
        The detected name of the entity.
    acc: float
        The accuracy of the entity.
    context_similarity: float
        The context similarity of the entity.
    start: int
        The start index of the entity in the text.
    end: int
        The end index of the entity in the text.
    icd10: List[Dict[str, str]]
        The ICD-10 codes of the entity.
    ontologies: List[str]
        The ontologies of the entity.
    snomed: List[str]
        The SNOMED codes of the entity.
    id: int
        The ID of the entity.
    meta_anns: Dict[str, MetaAnnotation]
        The meta-annotations of the entity.
    """

    pretty_name: str
    cui: str
    type_ids: List[str]
    types: List[str]
    source_value: str
    detected_name: str
    acc: float
    context_similarity: float
    start: int
    end: int
    icd10: List[Dict[str, str]]
    ontologies: List[str]
    snomed: List[str]
    id: int
    meta_anns: Dict[str, MetaAnnotation]


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
