"""
NER Service using FastAPI and Hugging Face Transformers.

This module provides a FastAPI application for performing Named Entity Recognition (NER)
on biomedical text using a pre-trained model from Hugging Face.
"""

import logging
from typing import List, Tuple

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Set up device (GPU if available, else CPU)
DEVICE = 0 if torch.cuda.is_available() else -1
logger.info(f"Using device: {'GPU' if DEVICE == 0 else 'CPU'}")

# Load model and tokenizer
MODEL_NAME = "d4data/biomedical-ner-all"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME).to(DEVICE)

# Set up NER pipeline
ner_pipeline = pipeline(
    "ner",
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple",
    device=DEVICE,
)


class NERRequest(BaseModel):
    """Request model for NER endpoint."""

    text: str


class Entity(BaseModel):
    """Entity model representing a named entity."""

    entity_group: str
    word: str
    start: int
    end: int
    score: float


class NERResponse(BaseModel):
    """Response model for NER endpoint."""

    entities: List[Entity]


def chunk_text(text: str, max_length: int = 512) -> List[Tuple[str, int]]:
    """
    Split text into chunks of maximum length.

    Parameters
    ----------
    text : str
        The input text to be chunked.
    max_length : int, optional
        The maximum length of each chunk (default is 512).

    Returns
    -------
    List[Tuple[str, int]]
        A list of tuples containing the text chunk and its starting offset.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_length
        if end >= len(text):
            chunks.append((text[start:], start))
            break
        # Find the last period or space before max_length
        last_period = text.rfind(".", start, end)
        last_space = text.rfind(" ", start, end)
        chunk_end = max(last_period, last_space)
        if chunk_end == -1 or chunk_end <= start:
            chunk_end = end
        chunks.append((text[start:chunk_end], start))
        start = chunk_end
    return chunks


@app.post("/ner", response_model=NERResponse)
async def perform_ner(request: NERRequest) -> NERResponse:
    """
    Perform Named Entity Recognition on the input text.

    Parameters
    ----------
    request : NERRequest
        The request object containing the text to analyze.

    Returns
    -------
    NERResponse
        The response object containing the identified entities.

    Raises
    ------
    HTTPException
        If an error occurs during processing.
    """
    try:
        logger.info(f"Received NER request with text length: {len(request.text)}")

        chunks = chunk_text(request.text)
        logger.info(f"Split text into {len(chunks)} chunks")

        all_entities = []

        for i, (chunk, offset) in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)}")
            with torch.no_grad():
                results = ner_pipeline(chunk)

            all_entities.extend(
                [
                    Entity(
                        entity_group=result["entity_group"],
                        word=result["word"],
                        start=result["start"] + offset,
                        end=result["end"] + offset,
                        score=float(result["score"]),
                    )
                    for result in results
                ]
            )

        logger.info(f"NER completed. Found {len(all_entities)} entities.")
        return NERResponse(entities=all_entities)
    except Exception as e:
        logger.error(f"Error during NER: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.on_event("startup")
async def startup_event() -> None:
    """
    Perform startup tasks for the NER service.

    This function is called when the FastAPI application starts up.
    It warms up the model by running inference on a sample sentence.
    """
    logger.info("Starting up the NER service")
    _ = ner_pipeline("This is a warm-up sentence.")
    logger.info("Model warmed up and ready for inference")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003, workers=1)
