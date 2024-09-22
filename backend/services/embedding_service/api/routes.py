"""Embedding Server for NV-Embed-v2 Model."""

import os
from typing import Dict, List, Tuple

import torch
from fastapi import APIRouter, HTTPException
from huggingface_hub import snapshot_download
from transformers import AutoConfig, AutoModel, AutoTokenizer

from api.embeddings.data import EmbeddingRequest, EmbeddingResponse


# Set environment variables for GPU usage
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Use only one GPU
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"

# Set batch size (can be overridden by environment variable)
BATCH_SIZE = 32

router = APIRouter()


def load_model() -> Tuple[AutoModel, AutoTokenizer]:
    """
    Load the NV-Embed-v2 model and tokenizer with optimizations for memory and speed.

    Returns
    -------
    model: AutoModel
        The NV-Embed-v2 model.
    tokenizer: AutoTokenizer
        The tokenizer for the NV-Embed-v2 model.
    """
    print("Loading model...")
    model_id = "nvidia/NV-Embed-v2"

    # Download the model files
    cache_dir = snapshot_download(model_id)

    config = AutoConfig.from_pretrained(cache_dir, trust_remote_code=True)

    # Add the missing attribute if it doesn't exist
    if not hasattr(config.latent_attention_config, "_attn_implementation_internal"):
        config.latent_attention_config._attn_implementation_internal = None

    # Load the model directly to GPU
    model = AutoModel.from_pretrained(
        cache_dir,
        config=config,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto",
    )

    print("Model loaded successfully")
    print(f"Model device: {next(model.parameters()).device}")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(cache_dir)

    return model, tokenizer


model, tokenizer = load_model()


@torch.no_grad()
def process_batch(texts: List[str], instruction: str) -> List[List[float]]:
    """Process a batch of texts and return their embeddings.

    Parameters
    ----------
    texts: List[str]
        The texts to embed.
    instruction: str
        The instruction to embed the texts.

    Returns
    -------
    embeddings: List[List[float]]
        The embeddings of the texts.
    """
    inputs = tokenizer(
        [f"{instruction}\n{text}" for text in texts],
        padding=True,
        truncation=True,
        return_tensors="pt",
        max_length=8192,
    )

    # Move inputs to the same device as the model
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    outputs = model(**inputs)
    # Use float32 for mean calculation to maintain precision
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
    """Create embeddings for the given texts.

    Parameters
    ----------
    request: EmbeddingRequest
        The request containing the texts to embed.

    Returns
    -------
    embeddings: Dict[str, List[List[float]]]
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
