"""LLM module for patients API."""

import logging
import os

from langchain_openai import ChatOpenAI


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up OpenAI client with custom endpoint
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL")
if not LLM_SERVICE_URL:
    raise ValueError("LLM_SERVICE_URL is not set")
logger.info(f"LLM_SERVICE_URL is set to: {LLM_SERVICE_URL}")

os.environ["OPENAI_API_KEY"] = "EMPTY"

# Initialize LLM with increased timeout
try:
    LLM = ChatOpenAI(
        base_url=LLM_SERVICE_URL,
        model_name="Meta-Llama-3.1-70B-Instruct",
        temperature=0.3,
        max_tokens=4096,
        request_timeout=60,
    )
    logger.info("ChatOpenAI initialized successfully")
except Exception as e:
    logger.error(f"Error initializing ChatOpenAI: {str(e)}")
    raise