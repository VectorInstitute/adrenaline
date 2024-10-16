"""Data models for pages."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CoTStep(BaseModel):
    """A single step in the chain of thought process."""

    step: str = Field(description="A single step in the chain of thought process")
    reasoning: str = Field(description="The reasoning behind this step")


class CoTSteps(BaseModel):
    """A list of steps in the chain of thought process."""

    steps: List[CoTStep] = Field(
        description="List of steps in the chain of thought process"
    )


class Answer(BaseModel):
    """The answer to the query."""

    answer: str = Field(description="The answer to the query")
    reasoning: str = Field(description="The reasoning for the answer")


class Query(BaseModel):
    """
    Represents a query.

    Attributes
    ----------
    page_id : str
        The page identifier.
    query : str
        The query.
    patient_id : Optional[int] = None
        The patient identifier.
    steps : Optional[List[CoTStep]] = None
        The steps in the chain of thought process.
    """

    page_id: str
    query: str
    patient_id: Optional[int] = None
    steps: Optional[List[CoTStep]] = None


class QueryAnswer(BaseModel):
    """A query and its answer."""

    query: Query
    answer: Optional[Answer] = None
    is_first: bool = Field(description="Whether this is the first query", default=False)


class Page(BaseModel):
    """A page in the application."""

    id: str
    user_id: str
    query_answers: List[QueryAnswer]
    created_at: datetime
    updated_at: datetime
