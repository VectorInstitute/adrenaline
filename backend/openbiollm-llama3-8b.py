import transformers
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Initialize FastAPI app
app = FastAPI()

# Model configuration
model_id = "aaditya/OpenBioLLM-Llama3-8B"

# Initialize the model
model = transformers.AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

# Create the tokenizer
tokenizer = transformers.AutoTokenizer.from_pretrained(model_id)

# Create the pipeline
pipeline = transformers.pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    device_map="auto",
)

# System prompt
system_prompt = """You are an expert and experienced from the healthcare and biomedical domain with extensive medical knowledge and practical experience. Your name is adrenaline AI. who's willing to help answer the user's query with explanation. In your explanation, leverage your deep medical expertise such as relevant anatomical structures, physiological processes, diagnostic criteria, treatment guidelines, or other pertinent medical concepts. Use precise medical terminology while still aiming to make the explanation clear and accessible to a general audience."""

# Pydantic model for request body
class Query(BaseModel):
    prompt: str

@app.post("/generate")
async def generate_text(query: Query):
    try:
        # Construct the full prompt
        full_prompt = f"System: {system_prompt}\n\nHuman: {query.prompt}\n\nAI:"

        # Generate response
        outputs = pipeline(
            full_prompt,
            max_new_tokens=256,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )

        # Extract the generated text
        generated_text = outputs[0]["generated_text"][len(full_prompt):]

        return {"response": generated_text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
