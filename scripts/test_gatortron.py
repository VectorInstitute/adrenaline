import asyncio
from typing import List
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModel, AutoConfig
import uvicorn
import warnings

# Suppress the FutureWarning about clean_up_tokenization_spaces
warnings.filterwarnings(
    "ignore", category=FutureWarning, message="clean_up_tokenization_spaces"
)

# Initialize FastAPI app
app = FastAPI()

# Load model and tokenizer
MODEL_NAME = "UFNLP/gatortron-medium"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, clean_up_tokenization_spaces=True)
config = AutoConfig.from_pretrained(MODEL_NAME, trust_remote_code=True)

# Set maximum sequence length
MAX_LENGTH = 2048

# Set batch size for processing
BATCH_SIZE = 8


# Pydantic models for request and response
class EmbeddingRequest(BaseModel):
    texts: List[str]


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]


# Load model across both GPUs
def load_model():
    model = AutoModel.from_pretrained(
        MODEL_NAME, config=config, trust_remote_code=True, torch_dtype=torch.float16
    )
    if torch.cuda.device_count() > 1:
        model = torch.nn.DataParallel(model)
    model.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    return model.eval()


model = load_model()
print(f"Model loaded on device: {next(model.parameters()).device}")


# Function to get embeddings
@torch.no_grad()
def get_embeddings(texts: List[str]) -> List[List[float]]:
    # Tokenize inputs
    inputs = tokenizer(
        texts, padding=True, truncation=True, return_tensors="pt", max_length=MAX_LENGTH
    )

    # Move inputs to the same device as the model
    inputs = {k: v.to(next(model.parameters()).device) for k, v in inputs.items()}

    # Get model output
    outputs = model(**inputs)

    # Use mean pooling for sentence embeddings
    attention_mask = inputs["attention_mask"]
    embeddings = mean_pooling(outputs.last_hidden_state, attention_mask)

    return embeddings.cpu().numpy().tolist()


# Mean pooling function
def mean_pooling(token_embeddings, attention_mask):
    input_mask_expanded = (
        attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    )
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1), min=1e-9
    )


# Async function to process batches
async def process_batch(batch: List[str]) -> List[List[float]]:
    return await asyncio.get_event_loop().run_in_executor(None, get_embeddings, batch)


@app.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    try:
        texts = request.texts
        all_embeddings = []

        # Process texts in batches
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            embeddings = await process_batch(batch)
            all_embeddings.extend(embeddings)

        return EmbeddingResponse(embeddings=all_embeddings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8015, workers=1)
