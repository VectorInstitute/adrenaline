"""Clinical NER Service API routes."""

import logging
import os
from typing import Any, Dict

import spacy
from fastapi import APIRouter, Body, HTTPException, status
from medcat.cat import CAT

from api.entities.data import Entity, MetaAnnotation, NERResponse


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

MEDCAT_MODELS_DIR = os.getenv("MEDCAT_MODELS_DIR", "/app/medcat_models")
SELECTED_MODEL = os.getenv(
    "SELECTED_MEDCAT_MODEL", "umls_sm_pt2ch_533bab5115c6c2d6.zip"
)


def load_medcat_model() -> CAT:
    """
    Load the MedCAT model.

    Returns
    -------
    CAT
        The loaded MedCAT model.

    Raises
    ------
    FileNotFoundError
        If the MedCAT model file is not found.
    Exception
        If there's an error loading the model.
    """
    try:
        try:
            spacy.load("en_core_web_md")
        except OSError:
            logger.error("Required spaCy model 'en_core_web_md' is not installed.")
            logger.info("Attempting to download 'en_core_web_md'...")
            spacy.cli.download("en_core_web_md")  # type: ignore
            logger.info("Download completed. Retrying model load.")
            spacy.load("en_core_web_md")

        model_path = os.path.join(MEDCAT_MODELS_DIR, SELECTED_MODEL)
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"MedCAT model not found: {model_path}")

        return CAT.load_model_pack(model_path)
    except Exception as e:
        logger.error(f"Failed to load MedCAT model: {str(e)}")
        raise


# Load MedCAT model
try:
    cat = load_medcat_model()
except Exception as e:
    logger.error(f"Failed to initialize MedCAT: {str(e)}")
    cat = None


def process_entity(entity: Dict[str, Any]) -> Entity:
    """
    Process an entity from MedCAT.

    Parameters
    ----------
    entity : Dict[str, Any]
        The entity dictionary from MedCAT.

    Returns
    -------
    Entity
        The processed Entity object.
    """
    return Entity(
        pretty_name=entity["pretty_name"],
        cui=entity["cui"],
        type_ids=entity["type_ids"],
        types=entity["types"],
        source_value=entity["source_value"],
        detected_name=entity["detected_name"],
        acc=entity["acc"],
        context_similarity=entity["context_similarity"],
        start=entity["start"],
        end=entity["end"],
        icd10=entity["icd10"],
        ontologies=entity["ontologies"],
        snomed=entity["snomed"],
        id=entity["id"],
        meta_anns={k: MetaAnnotation(**v) for k, v in entity["meta_anns"].items()},
    )


@router.post("/extract_entities", response_model=NERResponse)
async def extract_entities(text: str = Body(..., embed=True)) -> NERResponse:
    """
    Extract entities from a medical note.

    Parameters
    ----------
    text : str
        The medical note text to extract entities from.

    Returns
    -------
    NERResponse
        The response containing the extracted entities.

    Raises
    ------
    HTTPException
        If the MedCAT model is not available or if there's an unexpected error.
    """
    if cat is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MedCAT model is not available. Please check the logs for more information.",
        )

    try:
        # Use MedCAT for entity extraction
        entities_dict = cat.get_entities(text)

        # Process entities
        medcat_entities = [
            process_entity(entity) for entity in entities_dict["entities"].values()
        ]

        logger.info(f"Extracted {len(medcat_entities)} entities from the provided text")
        return NERResponse(text=text, entities=medcat_entities)

    except Exception as e:
        logger.error(f"Unexpected error in extract_entities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
