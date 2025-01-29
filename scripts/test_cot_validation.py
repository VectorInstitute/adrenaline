"""
This script validates QA pairs for all patients with QA data, using a structured chain-of-thought reasoning approach.
"""

import os
import re
import asyncio
import json
import logging
from typing import List, Dict, Any
import requests
from pydantic import BaseModel, Field
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich import box
from rich.text import Text
from rich.syntax import Syntax
from rich.columns import Columns
import backoff
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("validation.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Constants
BACKEND_BASE_URL = "http://localhost:8002"
LLM_BASE_URL = "http://gpu004:8080/v1"
USERNAME = "admin"
PASSWORD = "admin_password"
MONGO_URI = "mongodb://root:password@cyclops.cluster.local:27017"
DB_NAME = "clinical_data"
RESULTS_FILE = "validation_results.json"

# Initialize Rich console and OpenAI client
console = Console()
client = OpenAI(base_url=LLM_BASE_URL, api_key="EMPTY")

# Initialize MongoDB client
mongo_client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DB_NAME]
patients_collection = db.patients


# Data Models
class QAPair(BaseModel):
    question: str
    answer: str


class ClinicalNote(BaseModel):
    note_id: str
    encounter_id: str
    text: str
    note_type: str


class PatientData(BaseModel):
    patient_id: int
    notes: List[ClinicalNote]
    qa_data: List[QAPair] = Field(default_factory=list)


class ReasoningStep(BaseModel):
    step_number: int
    content: str


class ValidationResult(BaseModel):
    is_correct: bool
    reasoning: List[ReasoningStep]
    correct_answer: str = ""


# Authentication Function
def get_auth_token() -> str:
    """Authenticate and get the access token."""
    try:
        logger.info("Authenticating...")
        with console.status("[bold green]Authenticating...[/bold green]"):
            response = requests.post(
                f"{BACKEND_BASE_URL}/auth/signin",
                json={"username": USERNAME, "password": PASSWORD},
            )
        response.raise_for_status()
        logger.info("Authentication successful")
        return response.json()["access_token"]
    except requests.RequestException as e:
        logger.error(f"Authentication failed: {e}")
        raise


# API Interaction Functions
def fetch_patient_data(patient_id: int, auth_token: str) -> PatientData:
    """Fetch patient data from the backend API."""
    try:
        logger.info(f"Fetching data for patient {patient_id}")
        with console.status(
            f"[bold green]Fetching data for patient {patient_id}...[/bold green]"
        ):
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = requests.get(
                f"{BACKEND_BASE_URL}/patient_data/{patient_id}", headers=headers
            )
        response.raise_for_status()
        logger.info(f"Successfully fetched data for patient {patient_id}")
        return PatientData(**response.json())
    except requests.RequestException as e:
        logger.error(f"Error fetching data for patient {patient_id}: {e}")
        raise


# LLM Interaction Function
@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def send_chat_prompt(
    prompt: str, model: str = "Llama3-OpenBioLLM-70B", max_tokens: int = 2048
) -> str:
    """Send a prompt to the chat completions endpoint with retries."""
    try:
        logger.debug(f"Sending prompt to LLM: {prompt[:50]}...")
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a highly skilled clinical assistant tasked with validating question-answer pairs based on given context. Provide detailed, step-by-step reasoning for your conclusions. Always return your response in valid JSON format.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            n=1,
            stream=False,
        )
        if not completion.choices or not completion.choices[0].message.content.strip():
            raise Exception("Empty response received from LLM")
        logger.debug("Successfully received response from LLM")
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error in LLM interaction: {e}. Retrying...")
        raise


def construct_json_from_text(text: str) -> Dict[str, Any]:
    """Attempt to construct a JSON object from unstructured text."""
    constructed_json = {}

    # Try to extract is_correct
    is_correct_match = re.search(r'is_correct["\s:]+(\w+)', text, re.IGNORECASE)
    if is_correct_match:
        is_correct = is_correct_match.group(1).lower() == "true"
        constructed_json["is_correct"] = is_correct

    # Try to extract reasoning
    reasoning_matches = re.findall(
        r'step_number["\s:]+(\d+)[,\s]*content["\s:]+(.+?)(?=step_number|\Z)',
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if reasoning_matches:
        constructed_json["reasoning"] = [
            {"step_number": int(num), "content": content.strip()}
            for num, content in reasoning_matches
        ]

    # Try to extract correct_answer
    correct_answer_match = re.search(
        r'correct_answer["\s:]+(.+?)(?=\Z|\})', text, re.DOTALL | re.IGNORECASE
    )
    if correct_answer_match:
        constructed_json["correct_answer"] = correct_answer_match.group(1).strip()

    return constructed_json if len(constructed_json) >= 2 else {}


def extract_json_from_response(response: str) -> Dict[str, Any]:
    """Extract and parse JSON from the LLM response."""
    try:
        # First, try to parse the entire response as JSON
        return json.loads(response)
    except json.JSONDecodeError:
        # If that fails, try to extract JSON using a simpler regex
        json_pattern = r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}"
        json_matches = re.findall(json_pattern, response, re.DOTALL)

        for match in json_matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # If no valid JSON is found, try to construct a JSON from the response
        constructed_json = construct_json_from_text(response)
        if constructed_json:
            return constructed_json

        # If all else fails, raise an error
        raise ValueError("No valid JSON found in LLM response")


def validate_qa_pair(context: str, question: str, answer: str) -> Dict[str, Any]:
    """Validate a QA pair using structured chain-of-thought reasoning."""
    try:
        logger.info(f"Validating QA pair - Question: {question[:50]}...")
        console.print("[bold blue]Validating answer...[/bold blue]")
        validation_prompt = f"""
        Given the following context, question, and answer, validate the answer using chain-of-thought reasoning:

        Context: {context}

        Question: {question}

        Given Answer: {answer}

        Please follow these steps in your reasoning:
        1. Identify key information in the context relevant to the question.
        2. Analyze how the given answer relates to this key information.
        3. Determine if the answer is fully supported by the context.
        4. If the answer is incorrect, explain why and provide the correct answer based on the context.

        Provide your response in the following JSON format:
        {{
            "is_correct": true/false,
            "reasoning": [
                {{"step_number": 1, "content": "..."}},
                {{"step_number": 2, "content": "..."}},
                {{"step_number": 3, "content": "..."}},
                {{"step_number": 4, "content": "..."}}
            ],
            "correct_answer": "Provide the correct answer if the given answer was incorrect, otherwise leave this empty"
        }}

        Ensure that your response is a valid JSON object.
        """

        validation_result = send_chat_prompt(validation_prompt)
        print(validation_result)
        logger.debug(f"Raw LLM Response: {validation_result[:100]}...")

        parsed_result = extract_json_from_response(validation_result)

        # Validate and sanitize the parsed result
        sanitized_result = {
            "is_correct": parsed_result.get("is_correct", False),
            "reasoning": [],
            "correct_answer": parsed_result.get("correct_answer", ""),
        }

        reasoning = parsed_result.get("reasoning", [])
        if isinstance(reasoning, list):
            sanitized_result["reasoning"] = [
                step["content"]
                if isinstance(step, dict) and "content" in step
                else str(step)
                for step in reasoning
            ]
        elif isinstance(reasoning, str):
            sanitized_result["reasoning"] = [reasoning]

        logger.info(
            f"QA pair validation complete - Is Correct: {sanitized_result['is_correct']}"
        )

        return {
            "question": question,
            "given_answer": answer,
            "is_correct": sanitized_result["is_correct"],
            "reasoning": sanitized_result["reasoning"],
            "correct_answer": sanitized_result["correct_answer"],
        }
    except Exception as e:
        logger.error(f"Error in reasoning: {e}")
        logger.debug(f"Problematic LLM response: {validation_result}")
        return {
            "question": question,
            "given_answer": answer,
            "is_correct": False,
            "reasoning": [f"Error occurred during validation: {str(e)}"],
            "correct_answer": "Unable to determine",
        }


# Main Validation Pipeline
async def validate_patient_qa_pairs(
    patient_id: int, auth_token: str
) -> List[Dict[str, str]]:
    """Validate all QA pairs for a given patient."""
    try:
        logger.info(f"Starting validation for patient {patient_id}")
        patient_data = fetch_patient_data(patient_id, auth_token)
        discharge_notes = [
            note for note in patient_data.notes if note.note_type == "DS"
        ]
        context = " ".join(note.text for note in discharge_notes)

        validation_results = []
        for i, qa_pair in enumerate(patient_data.qa_data):
            console.print(
                f"[bold green]Validating QA pair {i + 1}/{len(patient_data.qa_data)} for patient {patient_id}[/bold green]"
            )
            result = validate_qa_pair(context, qa_pair.question, qa_pair.answer)
            result["patient_id"] = patient_id
            validation_results.append(result)

        logger.info(f"Completed validation for patient {patient_id}")
        return validation_results
    except Exception as e:
        logger.error(f"Error in validation pipeline for patient {patient_id}: {e}")
        raise


async def get_patients_with_qa_pairs() -> List[int]:
    """Fetch all patients that have QA pairs."""
    logger.info("Fetching patients with QA pairs")
    cursor = patients_collection.find(
        {"qa_pairs": {"$exists": True, "$ne": []}}, projection={"patient_id": 1}
    )
    patients = [doc["patient_id"] for doc in await cursor.to_list(length=None)]
    logger.info(f"Found {len(patients)} patients with QA pairs")
    return patients


def save_results(results: List[Dict[str, str]]):
    """Save validation results to a JSON file."""
    logger.info(f"Saving validation results to {RESULTS_FILE}")
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Results saved successfully")


def load_results() -> List[Dict[str, str]]:
    """Load validation results from a JSON file."""
    if os.path.exists(RESULTS_FILE):
        logger.info(f"Loading existing results from {RESULTS_FILE}")
        with open(RESULTS_FILE, "r") as f:
            return json.load(f)
    logger.info("No existing results found")
    return []


async def run_validation() -> None:
    """Run the validation pipeline for all patients with QA pairs."""
    try:
        logger.info("Starting validation process")
        auth_token = get_auth_token()
        patients_with_qa = await get_patients_with_qa_pairs()
        total_patients = len(patients_with_qa)

        all_results = load_results()
        results_by_patient: Dict[int, List[Dict[str, Any]]] = {}
        for result in all_results:
            patient_id = result["patient_id"]
            if patient_id not in results_by_patient:
                results_by_patient[patient_id] = []
            results_by_patient[patient_id].append(result)

        total_correct = sum(1 for result in all_results if result["is_correct"])
        total_qa_pairs = len(all_results)

        for i, patient_id in enumerate(patients_with_qa, 1):
            if patient_id in results_by_patient:
                patient_results = results_by_patient[patient_id]
                if not result["reasoning"]:
                    logger.info(f"Skipping patient {patient_id} (no reasoning)")
                    console.print(
                        f"[yellow]Skipping patient {patient_id} (no reasoning)[/yellow]"
                    )
                    continue
                if all(
                    result["is_correct"] and "Error" not in result["reasoning"][0]
                    for result in patient_results
                ):
                    logger.info(
                        f"Skipping patient {patient_id} (all correct and no errors)"
                    )
                    console.print(
                        f"[yellow]Skipping patient {patient_id} (all correct and no errors)[/yellow]"
                    )
                    continue
                else:
                    logger.info(
                        f"Re-validating patient {patient_id} (some incorrect answers or errors)"
                    )
                    console.print(
                        f"[yellow]Re-validating patient {patient_id} (some incorrect answers or errors)[/yellow]"
                    )
            else:
                logger.info(f"Validating new patient {patient_id}")
                console.print(
                    f"[bold green]Validating new patient {patient_id}[/bold green]"
                )

            results = await validate_patient_qa_pairs(patient_id, auth_token)

            # Remove old results for this patient if any
            all_results = [r for r in all_results if r["patient_id"] != patient_id]
            all_results.extend(results)

            total_correct = sum(1 for result in all_results if result["is_correct"])
            total_qa_pairs = len(all_results)

            accuracy = (
                (total_correct / total_qa_pairs) * 100 if total_qa_pairs > 0 else 0
            )
            logger.info(f"Current Overall Accuracy: {accuracy:.2f}%")
            console.print(
                f"\n[bold cyan]Current Overall Accuracy: {accuracy:.2f}%[/bold cyan]"
            )
            console.print(f"Processed {i}/{total_patients} patients\n")

            save_results(all_results)

            for result in results:
                reasoning_steps = (
                    result["reasoning"].split("\n")
                    if isinstance(result["reasoning"], str)
                    else result["reasoning"]
                )
                formatted_reasoning = "\n".join(
                    [f"• {step.strip()}" for step in reasoning_steps if step.strip()]
                )

                question = Text(f"Question:\n{result['question']}", style="bold cyan")
                given_answer = Text(
                    f"Given Answer:\n{result['given_answer']}", style="bold yellow"
                )
                is_correct = Text(
                    f"Is Correct: {'Yes' if result['is_correct'] else 'No'}",
                    style="bold green" if result["is_correct"] else "bold red",
                )
                correct_answer = Text(
                    f"Correct Answer:\n{result['correct_answer'] if not result['is_correct'] else 'N/A'}",
                    style="bold green",
                )

                reasoning_syntax = Syntax(
                    formatted_reasoning, "markdown", theme="monokai", line_numbers=False
                )
                reasoning_title = Text("Reasoning:", style="bold blue")

                panel_content = Columns(
                    [
                        question,
                        given_answer,
                        is_correct,
                        reasoning_title,
                        reasoning_syntax,
                        correct_answer,
                    ],
                    expand=True,
                    align="left",
                )

                panel = Panel(
                    panel_content,
                    title="Validation Result",
                    border_style="green" if result["is_correct"] else "red",
                    box=box.HEAVY,
                    expand=False,
                    padding=(1, 1),
                )
                console.print(panel)

        final_accuracy = (
            (total_correct / total_qa_pairs) * 100 if total_qa_pairs > 0 else 0
        )
        logger.info(
            f"Validation Complete! Final Overall Accuracy: {final_accuracy:.2f}%"
        )
        logger.info(f"Total QA Pairs Validated: {total_qa_pairs}")
        console.print("\n[bold green]Validation Complete![/bold green]")
        console.print(
            f"[bold cyan]Final Overall Accuracy: {final_accuracy:.2f}%[/bold cyan]"
        )
        console.print(f"Total QA Pairs Validated: {total_qa_pairs}")

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        logger.exception("Detailed traceback:")


# Main execution
if __name__ == "__main__":
    logger.info("Starting script execution")
    asyncio.run(run_validation())
    logger.info("Script execution completed")
