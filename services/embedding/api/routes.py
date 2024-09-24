"""Embedding Service API routes."""

import os
import logging
from typing import Dict, List

import torch
from fastapi import APIRouter, HTTPException
from transformers import AutoConfig, AutoModel, AutoTokenizer

from api.embeddings.data import EmbeddingRequest, EmbeddingResponse

# Set batch size and max length
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "4"))
MAX_LENGTH = 512

# Set CUDA allocation config
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

# Global variables for model and tokenizer
model = None
tokenizer = None

async def load_model():
    """Load the GatorTron model and tokenizer."""
    global model, tokenizer

    logger.info("Loading GatorTron model...")
    model_id = "UFNLP/gatortron-medium"
    config = AutoConfig.from_pretrained(model_id, trust_remote_code=True)

    # Load model
    model = AutoModel.from_pretrained(
        model_id,
        config=config,
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )

    # Check GPU availability
    if torch.cuda.is_available():
        logger.info(f"CUDA is available. Found {torch.cuda.device_count()} GPU(s).")
        if torch.cuda.device_count() > 1:
            logger.info("Using DataParallel for multi-GPU support.")
            model = torch.nn.DataParallel(model)
        device = torch.device("cuda")
    else:
        logger.warning("CUDA is not available. Using CPU for inference.")
        device = torch.device("cpu")

    model.to(device)
    model.eval()

    logger.info(f"Model loaded successfully on {device}")

    tokenizer = AutoTokenizer.from_pretrained(model_id)

@torch.no_grad()
def process_batch(texts: List[str]) -> List[List[float]]:
    """Process a batch of texts to generate embeddings."""
    global model, tokenizer

    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        return_tensors="pt",
        max_length=MAX_LENGTH,
    )

    # Move inputs to the same device as the model
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    try:
        outputs = model(**inputs)
    except RuntimeError as e:
        if "out of memory" in str(e):
            torch.cuda.empty_cache()
            # Try again with half the batch size
            half_batch = len(texts) // 2
            return process_batch(texts[:half_batch]) + process_batch(texts[half_batch:])
        else:
            raise

    # Use mean pooling for sentence embeddings
    attention_mask = inputs["attention_mask"]
    embeddings = mean_pooling(outputs.last_hidden_state, attention_mask)

    return embeddings.cpu().numpy().tolist()

def mean_pooling(token_embeddings: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    """Perform mean pooling on the token embeddings."""
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest) -> Dict[str, List[List[float]]]:
    """Create embeddings for a list of texts."""
    global model, tokenizer

    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not initialized")

    try:
        all_embeddings = []
        for i in range(0, len(request.texts), BATCH_SIZE):
            batch = request.texts[i : i + BATCH_SIZE]
            batch_embeddings = process_batch(batch)
            all_embeddings.extend(batch_embeddings)

            # Clear CUDA cache to free up memory
            torch.cuda.empty_cache()

        return {"embeddings": all_embeddings}
    except Exception as e:
        logger.error(f"Error in create_embeddings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e