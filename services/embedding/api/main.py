"""Embedding Service main application."""

from api.routes import initialize_model, router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize the model before creating the FastAPI app
initialize_model()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "OK"}
