"""Backend server for the app."""

import logging
import os
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.patients.answer import initialize_llm
from api.patients.db import check_database_connection
from api.routes.answer import router as answer_router
from api.routes.auth import router as auth_router
from api.routes.ner import router as ner_router
from api.routes.pages import router as pages_router
from api.routes.patients import router as patients_router
from api.users.crud import create_initial_admin
from api.users.db import get_async_session, init_db


logger = logging.getLogger("uvicorn")
app = FastAPI()
frontend_port = os.getenv("FRONTEND_PORT", None)
if not frontend_port:
    raise ValueError("No FRONTEND_PORT environment variable set!")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{frontend_port}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(ner_router)
app.include_router(answer_router)
app.include_router(pages_router)


@app.on_event("startup")
async def startup_event() -> None:
    """
    Initialize the database and create the initial admin user on startup.

    This function is called when the FastAPI application starts up. It initializes
    the database and creates an initial admin user if one doesn't already exist.
    """
    try:
        await check_database_connection()
        await init_db()
        async for session in get_async_session():
            await create_initial_admin(session)
        # await initialize_llm()
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise


@app.get("/")
async def root() -> Dict[str, str]:
    """
    Root endpoint of the API.

    Returns
    -------
    Dict[str, str]
        A welcome message for the adrenaline API.
    """
    return {"message": "Welcome to the adrenaline API"}


@app.get("/health")
async def health() -> Dict[str, str]:
    """
    Health check endpoint.

    This endpoint can be used to verify that the API is running and responsive.

    Returns
    -------
    Dict[str, str]
        A dictionary indicating the health status of the API.
    """
    return {"status": "OK"}
