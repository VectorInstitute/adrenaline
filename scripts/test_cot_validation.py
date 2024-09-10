"""
This script validates the QA pairs for a given patient using a simple reasoning step.
"""

import asyncio
import json
import logging
from typing import List, Dict
import requests
from pydantic import BaseModel, Field
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import backoff

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
BACKEND_BASE_URL = "http://localhost:8002"
LLM_BASE_URL = "http://gpu043:8080/v1"

# Authentication constants
USERNAME = "admin"
PASSWORD = "admin_password"

# Initialize Rich console
console = Console()

# Initialize the OpenAI client
client = OpenAI(base_url=LLM_BASE_URL, api_key="EMPTY")


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


# Authentication Function
def get_auth_token() -> str:
    """Authenticate and get the access token."""
    try:
        with console.status("[bold green]Authenticating...[/bold green]"):
            response = requests.post(
                f"{BACKEND_BASE_URL}/auth/signin",
                json={"username": USERNAME, "password": PASSWORD},
            )
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.RequestException as e:
        logger.error(f"Authentication failed: {e}")
        raise


# API Interaction Functions
def fetch_patient_data(patient_id: int, auth_token: str) -> PatientData:
    """Fetch patient data from the backend API."""
    try:
        with console.status("[bold green]Fetching patient data...[/bold green]"):
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = requests.get(
                f"{BACKEND_BASE_URL}/patient_data/{patient_id}", headers=headers
            )
        response.raise_for_status()
        return PatientData(**response.json())
    except requests.RequestException as e:
        logger.error(f"Error fetching patient data: {e}")
        raise


# LLM Interaction Function
@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def send_chat_prompt(
    prompt: str, model: str = "Llama3-OpenBioLLM-70B", max_tokens: int = 2048
) -> str:
    """Send a prompt to the chat completions endpoint with retries."""
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful and knowledgeable clinical assistant. Provide accurate and concise information about clinical conditions and symptoms.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            n=1,
            stream=False,
        )
        if not completion.choices or not completion.choices[0].message.content.strip():
            raise Exception("Empty response received")
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"An error occurred: {e}. Retrying...")
        raise


def validate_qa_pair(context: str, question: str, answer: str) -> Dict[str, str]:
    """Validate a QA pair using a simple reasoning step."""
    try:
        # Answer Validation
        console.print("[bold blue]Validating answer...[/bold blue]")
        validation_prompt = f"""
        Given the following context, question, and answer, validate the answer using chain of thought reasoning:

        Context: {context}

        Question: {question}

        Given Answer: {answer}

        Please provide your response in the following JSON format:
        {{
            "is_correct": "Yes/Partially/No",
            "reasoning": "Your step-by-step reasoning here",
            "correct_answer": "Provide the correct answer if the given answer was incorrect or partially correct, otherwise leave this empty"
        }}
        """

        validation_result = send_chat_prompt(validation_prompt)
        console.print(f"[dim]Raw LLM Response: {validation_result[:100]}...[/dim]")

        # Try to parse the result as JSON
        try:
            parsed_result = json.loads(validation_result)
            return {
                "question": question,
                "given_answer": answer,
                "is_correct": parsed_result.get("is_correct", "Unable to determine"),
                "reasoning": parsed_result.get("reasoning", "No reasoning provided"),
                "correct_answer": parsed_result.get("correct_answer", "Not provided"),
            }
        except json.JSONDecodeError:
            # If JSON parsing fails, fall back to text parsing
            lines = validation_result.split("\n")
            is_correct = "Unable to determine"
            reasoning = []
            correct_answer = "Not provided"
            current_section = None

            for line in lines:
                if "is_correct" in line.lower():
                    is_correct = (
                        line.split(":", 1)[1].strip() if ":" in line else line.strip()
                    )
                elif "reasoning" in line.lower():
                    current_section = "reasoning"
                elif "correct answer" in line.lower():
                    correct_answer = (
                        line.split(":", 1)[1].strip() if ":" in line else line.strip()
                    )
                    current_section = None
                elif current_section == "reasoning":
                    reasoning.append(line.strip())

            return {
                "question": question,
                "given_answer": answer,
                "is_correct": is_correct,
                "reasoning": "\n".join(reasoning).strip(),
                "correct_answer": correct_answer,
            }

    except Exception as e:
        logger.error(f"Error in reasoning: {e}")
        return {
            "question": question,
            "given_answer": answer,
            "is_correct": "Error",
            "reasoning": f"Error occurred during validation: {str(e)}",
            "correct_answer": "Unable to determine",
        }


# Main Validation Pipeline
async def validate_patient_qa_pairs(
    patient_id: int, auth_token: str
) -> List[Dict[str, str]]:
    """Validate all QA pairs for a given patient."""
    try:
        patient_data = fetch_patient_data(patient_id, auth_token)
        # Filter for discharge summary notes
        discharge_notes = [
            note for note in patient_data.notes if note.note_type == "DS"
        ]
        context = " ".join(note.text for note in discharge_notes)

        validation_results = []
        for i, qa_pair in enumerate(patient_data.qa_data):
            console.print(
                f"[bold green]Validating QA pair {i+1}/{len(patient_data.qa_data)}[/bold green]"
            )
            result = validate_qa_pair(context, qa_pair.question, qa_pair.answer)
            validation_results.append(result)

        return validation_results
    except Exception as e:
        logger.error(f"Error in validation pipeline: {e}")
        raise


# Asynchronous execution function
async def run_validation(patient_id: int):
    """Run the validation pipeline for a patient."""
    try:
        auth_token = get_auth_token()
        results = await validate_patient_qa_pairs(patient_id, auth_token)
        for result in results:
            panel = Panel(
                Markdown(f"""
                **Question:** {result['question']}
                **Given Answer:** {result['given_answer']}
                **Is Correct:** {result['is_correct']}
                **Reasoning:**
                {result['reasoning']}
                **Correct Answer:** {result['correct_answer']}
                """),
                title="Validation Result",
                border_style="green",
                expand=False,
            )
            console.print(panel)

            # Print raw data for debugging
            console.print("[bold red]Raw Result Data:[/bold red]")
            console.print(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"Validation failed for patient {patient_id}: {e}")


# Main execution
if __name__ == "__main__":
    patient_id = 13074106  # Replace with actual patient ID
    asyncio.run(run_validation(patient_id))
