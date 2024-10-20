"""Embedding Service data models."""

from typing import List

from pydantic import BaseModel


class EmbeddingRequest(BaseModel):
    """Embedding request data model.

    Attributes
    ----------
    texts: List[str]
        The texts to embed.
    """

    texts: List[str]


class EmbeddingResponse(BaseModel):
    """Embedding response data model.

    Attributes
    ----------
    embeddings: List[List[float]]
        The embeddings of the texts.
    """

    embeddings: List[List[float]]
