"""Embedding Service data models."""

from pydantic import BaseModel


class EmbeddingRequest(BaseModel):
    """Embedding request data model.

    Attributes
    ----------
    texts: List[str]
        The texts to embed.
    """

    texts: list[str]


class EmbeddingResponse(BaseModel):
    """Embedding response data model.

    Attributes
    ----------
    embeddings: List[List[float]]
        The embeddings of the texts.
    """

    embeddings: list[list[float]]
