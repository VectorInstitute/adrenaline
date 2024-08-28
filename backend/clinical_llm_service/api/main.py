import gc

import torch
import transformers
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


# Initialize FastAPI app
app = FastAPI()

# Model configuration
model_id = "aaditya/OpenBioLLM-Llama3-8B"

# Initialize the model with memory optimizations
model = transformers.AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float16,
    device_map="auto",
    low_cpu_mem_usage=True,
    offload_folder="offload",
)

# Enable gradient checkpointing for memory efficiency
model.gradient_checkpointing_enable()

# Create the tokenizer
tokenizer = transformers.AutoTokenizer.from_pretrained(model_id)

# Set pad_token_id to eos_token_id if it's not set
if tokenizer.pad_token_id is None:
    tokenizer.pad_token_id = tokenizer.eos_token_id

# System prompt
system_prompt = """You are an expert and experienced from the healthcare and biomedical domain with extensive medical knowledge and practical experience. Your name is adrenaline AI. who's willing to help answer the user's query with explanation. In your explanation, leverage your deep medical expertise such as relevant anatomical structures, physiological processes, diagnostic criteria, treatment guidelines, or other pertinent medical concepts. Use precise medical terminology while still aiming to make the explanation clear and accessible to a general audience."""


# Pydantic model for request body
class Query(BaseModel):
    prompt: str
    context: str = ""


@app.post("/generate")
async def generate_text(query: Query):
    try:
        # Construct the full prompt
        full_prompt = f"System: {system_prompt}\n\nContext: {query.context}\n\nHuman: {query.prompt}\n\nAI:"

        # Create a generator function for streaming
        def generate():
            inputs = tokenizer(
                full_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=1024,
                padding=True,
            )
            input_ids = inputs.input_ids.to(model.device)
            attention_mask = inputs.attention_mask.to(model.device)

            streamer = transformers.TextIteratorStreamer(
                tokenizer, skip_prompt=True, timeout=10.0
            )
            generation_kwargs = dict(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=1024,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                streamer=streamer,
                use_cache=True,
                pad_token_id=tokenizer.pad_token_id,
            )

            # Start the generation in a separate thread
            from threading import Thread

            thread = Thread(target=model.generate, kwargs=generation_kwargs)
            thread.start()

            for new_text in streamer:
                yield new_text + " "

            # Clear CUDA cache after generation
            torch.cuda.empty_cache()
            gc.collect()

        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
