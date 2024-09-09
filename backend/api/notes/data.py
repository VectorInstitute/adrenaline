"""Data models for medical notes."""

from datetime import datetime
from typing import Dict, List

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
    timestamp : datetime
        The timestamp of the note.
    """

    note_id: str = Field(..., description="Unique identifier for the note")
    patient_id: int = Field(..., description="Patient identifier")
    encounter_id: str = Field(
        ..., description="Hospital admission/encounter identifier"
    )
    text: str = Field(..., description="Content of the medical note")
    timestamp: datetime = Field(..., description="Timestamp of the note")


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
