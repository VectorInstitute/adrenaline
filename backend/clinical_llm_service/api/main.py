"""
Clinical LLM Service using FastAPI and Hugging Face Transformers.

This module provides a FastAPI application for generating clinical text
using a pre-trained language model.
"""

import gc
import logging
from threading import Thread
from typing import Generator

import torch
import transformers
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from transformers import PreTrainedModel, PreTrainedTokenizer


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Model configuration
MODEL_ID = "aaditya/OpenBioLLM-Llama3-8B"

# Initialize the model with memory optimizations
model: PreTrainedModel = transformers.AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    device_map="auto",
    low_cpu_mem_usage=True,
    offload_folder="offload",
)

# Enable gradient checkpointing for memory efficiency
model.gradient_checkpointing_enable()

# Create the tokenizer
tokenizer: PreTrainedTokenizer = transformers.AutoTokenizer.from_pretrained(MODEL_ID)

# Set pad_token_id to eos_token_id if it's not set
if tokenizer.pad_token_id is None:
    tokenizer.pad_token_id = tokenizer.eos_token_id

# Improved system prompt
SYSTEM_PROMPT = """
You are an expert healthcare AI designed to provide clear and accurate responses to user queries related to biomedical topics. Leverage your knowledge of anatomy, physiology, diagnostic criteria, treatment guidelines, and pertinent medical concepts. Ensure responses are precise and comprehensible for a general audience.

When asked to extract entities or provide structured output, always return a valid JSON object without any additional text or explanations. The JSON object should have entity types as keys and lists of extracted entities as values.

Guidelines:
1. Provide concise yet comprehensive answers.
2. Use medical terminology appropriately, explaining complex terms when necessary.
3. If the query lacks context, provide a general, informative response.
4. For structured output requests, use a clear JSON format without any surrounding text.
5. Conclude your response when the query has been fully addressed.
"""


class Query(BaseModel):
    """Pydantic model for request body."""

    prompt: str = Field(..., description="The user's query or instruction")
    context: str = Field("", description="Optional context for the query")


def is_answer_complete(text: str) -> bool:
    """
    Check if the answer is complete.

    Parameters
    ----------
    text : str
        The generated text to check.

    Returns
    -------
    bool
        True if the answer is complete, False otherwise.
    """
    completion_keywords = [
        "In conclusion",
        "To summarize",
        "In summary",
        "Therefore",
        "Thus",
        "In essence",
    ]
    return any(keyword.lower() in text.lower() for keyword in completion_keywords)


def generate_text(prompt: str, max_new_tokens: int = 1024) -> str:
    """
    Generate text based on the given prompt.

    Parameters
    ----------
    prompt : str
        The input prompt for text generation.
    max_new_tokens : int, optional
        The maximum number of new tokens to generate (default is 1024).

    Returns
    -------
    str
        The generated text.
    """
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=1024,
        padding=True,
    )
    input_ids = inputs.input_ids.to(model.device)
    attention_mask = inputs.attention_mask.to(model.device)

    output = model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        use_cache=True,
        pad_token_id=tokenizer.pad_token_id,
    )

    return str(tokenizer.decode(output[0], skip_special_tokens=True))


def clear_cuda_cache() -> None:
    """Clear CUDA cache and collect garbage."""
    torch.cuda.empty_cache()
    gc.collect()


@app.post("/generate_stream")
async def generate_text_stream(query: Query) -> StreamingResponse:
    """
    Generate text stream based on the given query.

    Parameters
    ----------
    query : Query
        The query object containing the prompt and context.

    Returns
    -------
    StreamingResponse
        A streaming response containing the generated text.

    Raises
    ------
    HTTPException
        If an error occurs during text generation.
    """
    try:
        full_prompt = f"System: {SYSTEM_PROMPT}\n\nContext: {query.context}\n\nHuman: {query.prompt}\n\nAI:"

        def generate() -> Generator[str, None, None]:
            streamer = transformers.TextIteratorStreamer(
                tokenizer, skip_prompt=True, timeout=10.0
            )
            generation_kwargs = {
                "inputs": tokenizer(full_prompt, return_tensors="pt").input_ids.to(
                    model.device
                ),
                "max_new_tokens": 1024,
                "do_sample": True,
                "temperature": 0.7,
                "top_p": 0.9,
                "streamer": streamer,
                "use_cache": True,
            }

            thread = Thread(target=model.generate, kwargs=generation_kwargs)
            thread.start()

            generated_text = ""
            for new_text in streamer:
                generated_text += new_text + " "
                yield new_text + " "

                if is_answer_complete(generated_text):
                    break

            clear_cuda_cache()

        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Error in generate_text_stream: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/generate")
async def generate(query: Query) -> JSONResponse:
    """
    Generate text based on the given query.

    Parameters
    ----------
    query : Query
        The query object containing the prompt and context.

    Returns
    -------
    JSONResponse
        A JSON response containing the generated text.

    Raises
    ------
    HTTPException
        If an error occurs during text generation.
    """
    try:
        full_prompt = f"System: {SYSTEM_PROMPT}\n\nContext: {query.context}\n\nHuman: {query.prompt}\n\nAI:"
        generated_text = generate_text(full_prompt)
        ai_response = generated_text.split("AI:")[-1].strip()

        clear_cuda_cache()

        return JSONResponse(content={"response": ai_response})
    except Exception as e:
        logger.error(f"Error in generate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003, workers=1)
