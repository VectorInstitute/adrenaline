"""Embedding Service data models."""

from typing import List

from pydantic import BaseModel


class EmbeddingRequest(BaseModel):
    """Embedding request data model.

    Attributes
    ----------
    texts: List[str]
        The texts to embed.
    instruction: str
        The instruction to embed the texts.
    """

    texts: List[str]
    instruction: str = "Represent the text for retrieval:"


class EmbeddingResponse(BaseModel):
    """Embedding response data model.

    Attributes
    ----------
    embeddings: List[List[float]]
        The embeddings of the texts.
    """

    embeddings: List[List[float]]
