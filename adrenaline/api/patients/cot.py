"""Chain of Thought based query expansion, and answer generation."""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from api.patients.prompts import (
    general_answer_template,
    general_cot_template,
    patient_answer_template,
    patient_cot_template,
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
        model_name="Llama3-OpenBioLLM-70B",
        temperature=0.3,
        max_tokens=2048,
        request_timeout=60,
    )
    logger.info("ChatOpenAI initialized successfully")
except Exception as e:
    logger.error(f"Error initializing ChatOpenAI: {str(e)}")
    raise


class CoTStep(BaseModel):
    """A single step in the chain of thought process."""

    step: str = Field(description="A single step in the chain of thought process")
    reasoning: str = Field(description="The reasoning behind this step")


class CoTSteps(BaseModel):
    """A list of steps in the chain of thought process."""

    steps: List[CoTStep] = Field(
        description="List of steps in the chain of thought process"
    )


class Answer(BaseModel):
    """The answer to the query."""

    answer: str = Field(description="The answer to the query")
    reasoning: str = Field(description="The reasoning for the answer")


steps_parser = PydanticOutputParser(pydantic_object=CoTSteps)
answer_parser = PydanticOutputParser(pydantic_object=Answer)
general_prompt = PromptTemplate(
    input_variables=["human_input", "format_instructions"],
    template=general_cot_template,
)
patient_prompt = PromptTemplate(
    input_variables=["context", "human_input", "format_instructions"],
    template=patient_cot_template,
)
patient_answer_prompt = PromptTemplate(
    input_variables=["context", "human_input", "steps", "format_instructions"],
    template=patient_answer_template,
)
general_answer_prompt = PromptTemplate(
    input_variables=["human_input", "steps", "format_instructions"],
    template=general_answer_template,
)

# Initialize the LLMChains
general_chain = LLMChain(llm=llm, prompt=general_prompt)
patient_chain = LLMChain(llm=llm, prompt=patient_prompt)
patient_answer_chain = LLMChain(llm=llm, prompt=patient_answer_prompt)
general_answer_chain = LLMChain(llm=llm, prompt=general_answer_prompt)


def parse_llm_output_steps(output: str) -> List[Dict[str, Any]]:
    """Parse the LLM output and extract the JSON content."""
    try:
        parsed = json.loads(output)
        if isinstance(parsed, dict) and "steps" in parsed:
            return parsed["steps"]
    except json.JSONDecodeError:
        try:
            start = output.index("{")
            end = output.rindex("}") + 1
            json_str = output[start:end]
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "steps" in parsed:
                return parsed["steps"]
        except (ValueError, json.JSONDecodeError):
            pass

    raise ValueError("Failed to parse LLM output as JSON")


def parse_llm_output_answer(output: str) -> Tuple[str, str]:
    """Parse the LLM output and extract the JSON content."""
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


async def generate_cot_answer(
    user_query: str,
    mode: str = "general",
    context: str = "",
    steps: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, str]:
    """Generate the answer for a CoT prompt."""
    logger.info(
        f"Starting generate_cot_answer for query: {user_query[:50]}... in {mode} mode"
    )
    steps_str = "\n".join([f"{step['step']}" for step in steps])
    try:
        logger.info("Attempting to run the chain...")
        if mode == "general":
            result = await asyncio.to_thread(
                general_answer_chain.run,
                human_input=user_query,
                steps=steps_str,
                format_instructions=answer_parser.get_format_instructions(),
            )
        elif mode == "patient":
            result = await asyncio.to_thread(
                patient_answer_chain.run,
                context=context,
                human_input=user_query,
                steps=steps_str,
                format_instructions=answer_parser.get_format_instructions(),
            )
        else:
            raise ValueError(f"Invalid mode: {mode}")
        logger.info(f"Chain run successful. Result: {result}")
        answer, reasoning = parse_llm_output_answer(result)
        logger.info(f"Generated answer: {answer}")
        logger.info(f"Generated reasoning: {reasoning}")
        return answer, reasoning
    except ValueError as ve:
        logger.error(f"Error parsing LLM output: {str(ve)}")
        raise
    except Exception as e:
        logger.error(f"Error in generate_cot_answer: {str(e)}")
        raise


async def generate_cot_steps(
    user_query: str, mode: str = "general", context: str = ""
) -> List[Dict[str, Any]]:
    """Generate the steps for a CoT prompt."""
    logger.info(
        f"Starting generate_cot_steps for query: {user_query[:50]}... in {mode} mode"
    )
    try:
        logger.info("Attempting to run the chain...")
        if mode == "general":
            result = await asyncio.to_thread(
                general_chain.run,
                human_input=user_query,
                format_instructions=steps_parser.get_format_instructions(),
            )
        elif mode == "patient":
            result = await asyncio.to_thread(
                patient_chain.run,
                context=context,
                human_input=user_query,
                format_instructions=steps_parser.get_format_instructions(),
            )
        else:
            raise ValueError(f"Invalid mode: {mode}")
        logger.info(f"Chain run successful. Result: {result}")
        steps_list = parse_llm_output_steps(result)
        logger.info(f"Generated {len(steps_list)} CoT steps")
        return steps_list
    except ValueError as ve:
        logger.error(f"Error parsing LLM output: {str(ve)}")
        raise
    except Exception as e:
        logger.error(f"Error in generate_cot_steps: {str(e)}")
        raise


async def test_llm_connection():
    """Test the connection to the LLM."""
    try:
        logger.info("Testing LLM connection...")
        test_query = "What are the risk factors for heart disease?"
        result = await generate_cot_steps(test_query)
        logger.info(f"LLM connection test successful. Generated {len(result)} steps.")
        return True
    except Exception as e:
        logger.error(f"LLM connection test failed: {str(e)}")
        return False


async def initialize_llm():
    """Initialize the LLM."""
    await test_llm_connection()
