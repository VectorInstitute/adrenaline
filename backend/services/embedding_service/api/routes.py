"""Embedding Service API routes."""

import logging
import os
from typing import Dict, List, Tuple

import torch
from fastapi import APIRouter, HTTPException
from huggingface_hub import snapshot_download
from transformers import AutoConfig, AutoModel, AutoTokenizer

from api.embeddings.data import EmbeddingRequest, EmbeddingResponse


# Increase batch size
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "8"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()


def load_model() -> Tuple[AutoModel, AutoTokenizer]:
    """Load the model.

    Returns
    -------
    Tuple[AutoModel, AutoTokenizer]
        The model and tokenizer.

    """
    logger.info("Loading model...")
    model_id = "nvidia/NV-Embed-v2"
    cache_dir = snapshot_download(model_id)
    config = AutoConfig.from_pretrained(cache_dir, trust_remote_code=True)

    if not hasattr(config.latent_attention_config, "_attn_implementation_internal"):
        config.latent_attention_config._attn_implementation_internal = None

    # Load model across both GPUs
    model = AutoModel.from_pretrained(
        cache_dir,
        config=config,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="balanced",  # Automatically balance across available GPUs
    )

    logger.info("Model loaded successfully")
    logger.info(f"Model devices: {model.hf_device_map}")

    tokenizer = AutoTokenizer.from_pretrained(cache_dir)
    return model, tokenizer


model, tokenizer = load_model()


@torch.no_grad()
def process_batch(texts: List[str], instruction: str) -> List[List[float]]:
    """Process a batch of texts.

    Parameters
    ----------
    texts: List[str]
        The texts to embed.
    instruction: str
        The instruction to embed the texts.

    Returns
    -------
    List[List[float]]
        The embeddings of the texts.

    """
    inputs = tokenizer(
        [f"{instruction}\n{text}" for text in texts],
        padding=True,
        truncation=True,
        return_tensors="pt",
        max_length=8192,
    )

    # Move inputs to the first GPU (model will handle distribution)
    inputs = {k: v.to("cuda:0") for k, v in inputs.items()}

    outputs = model(**inputs)
    return (
        outputs.get("sentence_embeddings")
        .to(torch.float32)
        .mean(dim=1)
        .cpu()
        .numpy()
        .tolist()
    )


@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest) -> Dict[str, List[List[float]]]:
    """Create embeddings for a list of texts.

    Parameters
    ----------
    request: EmbeddingRequest
        The request containing the texts and instruction.

    Returns
    -------
    Dict[str, List[List[float]]]
        The embeddings of the texts.

    """
    try:
        all_embeddings = []
        for i in range(0, len(request.texts), BATCH_SIZE):
            batch = request.texts[i : i + BATCH_SIZE]
            batch_embeddings = process_batch(batch, request.instruction)
            all_embeddings.extend(batch_embeddings)

            # Clear CUDA cache to free up memory
            torch.cuda.empty_cache()

        return {"embeddings": all_embeddings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
