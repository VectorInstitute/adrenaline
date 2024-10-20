"""Answer generation based on the context."""

import json
import logging
import os
from typing import Tuple

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_openai import ChatOpenAI

from api.pages.data import Answer
from api.patients.prompts import (
    general_answer_template,
    patient_answer_template,
)


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
    llm = ChatOpenAI(
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

answer_parser = PydanticOutputParser(pydantic_object=Answer)
patient_answer_prompt = PromptTemplate(
    input_variables=["context", "human_input", "format_instructions"],
    template=patient_answer_template,
)
general_answer_prompt = PromptTemplate(
    input_variables=["human_input", "format_instructions"],
    template=general_answer_template,
)

# Initialize the LLMChains
patient_answer_chain = RunnableSequence(patient_answer_prompt | llm)
general_answer_chain = RunnableSequence(general_answer_prompt | llm)


def parse_llm_output_answer(output: str) -> Tuple[str, str]:
    """Parse the LLM output and extract the JSON content.

    Parameters
    ----------
    output: str
        The LLM output to parse.

    Returns
    -------
    Tuple[str, str]
        The answer and the reasoning.
    """
    try:
        parsed = json.loads(output)
        if isinstance(parsed, dict) and "answer" in parsed and "reasoning" in parsed:
            return parsed["answer"], parsed["reasoning"]
        if isinstance(parsed, dict) and "answer" in parsed:
            return parsed["answer"], ""
        raise ValueError("Invalid JSON format")
    except json.JSONDecodeError:
        pass
    raise ValueError("Failed to parse LLM output as JSON")


async def generate_answer(
    user_query: str,
    mode: str = "general",
    context: str = "",
) -> Tuple[str, str]:
    """Generate the answer for a query.

    Parameters
    ----------
    user_query: str
        The user query to generate the answer for.
    mode: str
        The mode to generate the answer in.
    context: str
        The context to generate the answer in.

    Returns
    -------
    Tuple[str, str]
        The answer and the reasoning.
    """
    logger.info(
        f"Starting generate_answer for query: {user_query[:50]}... in {mode} mode"
    )
    try:
        logger.info("Attempting to run the chain...")
        if mode == "general":
            result = await general_answer_chain.ainvoke(
                {
                    "human_input": user_query,
                    "format_instructions": answer_parser.get_format_instructions(),
                }
            )
        elif mode == "patient":
            result = await patient_answer_chain.ainvoke(
                {
                    "context": context,
                    "human_input": user_query,
                    "format_instructions": answer_parser.get_format_instructions(),
                }
            )
        else:
            raise ValueError(f"Invalid mode: {mode}")
        logger.info(f"Chain run successful. Result: {result}")
        answer, reasoning = parse_llm_output_answer(result.content)
        logger.info(f"Generated answer: {answer}")
        logger.info(f"Generated reasoning: {reasoning}")
        return answer, reasoning
    except ValueError as ve:
        logger.error(f"Error parsing LLM output: {str(ve)}")
        raise
    except Exception as e:
        logger.error(f"Error in generate_answer: {str(e)}")
        raise


async def test_llm_connection():
    """Test the connection to the LLM.

    Returns
    -------
    bool
        True if the connection is successful, False otherwise.
    """
    try:
        logger.info("Testing LLM connection...")
        test_query = "What are the risk factors for heart disease?"
        result = await generate_answer(test_query, mode="general")
        logger.info(f"LLM connection test successful. Generated {result}.")
        return True
    except Exception as e:
        logger.error(f"LLM connection test failed: {str(e)}")
        return False


async def initialize_llm():
    """Initialize the LLM.

    Returns
    -------
    bool
        True if the connection is successful, False otherwise.
    """
    await test_llm_connection()
