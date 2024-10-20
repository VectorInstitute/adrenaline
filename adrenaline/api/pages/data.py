"""Data models for pages."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


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
    """

    page_id: str
    query: str
    patient_id: Optional[int] = None


class QueryAnswer(BaseModel):
    """A query and its answer."""

    query: Query
    answer: Optional[Answer] = None
    is_first: bool = Field(description="Whether this is the first query", default=False)


class Page(BaseModel):
    """A page in the application."""

    id: str
    user_id: str
    patient_id: Optional[int] = None
    query_answers: List[QueryAnswer]
    created_at: datetime
    updated_at: datetime
