"""Embedding Service API routes."""

import logging
import os
from typing import Dict, List

import torch
from fastapi import APIRouter, HTTPException
from sentence_transformers import SentenceTransformer

from api.embeddings.data import EmbeddingRequest, EmbeddingResponse

# Increase batch size
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()


def load_model() -> SentenceTransformer:
    """Load the model.

    Returns
    -------
    SentenceTransformer
        The sentence transformer model.
    """
    logger.info("Loading model...")
    model_id = "pritamdeka/S-PubMedBert-MS-MARCO"

    model = SentenceTransformer(model_id)

    logger.info("Model loaded successfully")
    return model


# Global variable for model
model = None


@torch.no_grad()
def process_batch(texts: List[str]) -> List[List[float]]:
    """Process a batch of texts.

    Parameters
    ----------
    texts: List[str]
        The texts to embed.

    Returns
    -------
    List[List[float]]
        The embeddings of the texts.
    """
    global model

    # Move model to GPU if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Get embeddings
    embeddings = model.encode(texts, convert_to_tensor=True, device=device)

    return embeddings.cpu().numpy().tolist()


@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest) -> Dict[str, List[List[float]]]:
    """Create embeddings for a list of texts.

    Parameters
    ----------
    request: EmbeddingRequest
        The request containing the texts.

    Returns
    -------
    Dict[str, List[List[float]]]
        The embeddings of the texts.
    """
    try:
        all_embeddings = []
        for i in range(0, len(request.texts), BATCH_SIZE):
            batch = request.texts[i : i + BATCH_SIZE]
            batch_embeddings = process_batch(batch)
            all_embeddings.extend(batch_embeddings)

            # Clear CUDA cache to free up memory
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        return {"embeddings": all_embeddings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def initialize_model() -> None:
    """Initialize the model."""
    global model
    model = load_model()
