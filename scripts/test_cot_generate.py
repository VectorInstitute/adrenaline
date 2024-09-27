import asyncio
import logging
from typing import List, Dict
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.text import Text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("cot_test.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Constants
BACKEND_BASE_URL = "http://localhost:8002"
USERNAME = "admin"
PASSWORD = "admin_password"
PATIENT_ID = 10005858

# Initialize Rich console
console = Console()


async def get_auth_token() -> str:
    """Authenticate and get the access token."""
    try:
        logger.info("Authenticating...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_BASE_URL}/auth/signin",
                json={"username": USERNAME, "password": PASSWORD},
            )
            response.raise_for_status()
            logger.info("Authentication successful")
            return response.json()["access_token"]
    except httpx.RequestError as e:
        logger.error(f"Authentication failed: {e}")
        raise


async def generate_cot_steps(
    query: str, auth_token: str, patient_id: str = None
) -> List[Dict[str, str]]:
    """Generate the steps for a COT prompt."""
    try:
        logger.info("Generating CoT steps...")
        async with httpx.AsyncClient(timeout=90.0) as client:
            payload = {"query": query}
            if patient_id:
                payload["patient_id"] = patient_id

            response = await client.post(
                f"{BACKEND_BASE_URL}/generate_cot_steps",
                headers={"Authorization": f"Bearer {auth_token}"},
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            steps = result.get("cot_steps", [])
            logger.info(f"Generated {len(steps)} CoT steps")
            return steps
    except httpx.RequestError as e:
        logger.error(f"Error generating CoT steps: {e}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e}")
        logger.error(f"Response content: {e.response.text}")
        raise


async def generate_cot_answer(
    query: str, auth_token: str, patient_id: str = None
) -> str:
    """Generate the answer for a COT prompt."""
    try:
        logger.info("Generating CoT answer...")
        async with httpx.AsyncClient(timeout=90.0) as client:
            payload = {"query": query}
            if patient_id:
                payload["patient_id"] = patient_id

            response = await client.post(
                f"{BACKEND_BASE_URL}/generate_cot_answer",
                headers={"Authorization": f"Bearer {auth_token}"},
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            answer = result.get("answer", "")
            logger.info(f"Generated answer: {answer}")
            return answer
    except httpx.RequestError as e:
        logger.error(f"Error generating CoT answer: {e}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e}")
        logger.error(f"Response content: {e.response.text}")
        raise


def display_cot_steps(query: str, steps: List[Dict[str, str]], patient_id: str = None):
    """Display the CoT steps using Rich."""
    title = f"[bold magenta]Query:[/bold magenta] {query}"
    if patient_id:
        title += f" [bold cyan](Patient ID: {patient_id})[/bold cyan]"

    tree = Tree(title)
    for i, step in enumerate(steps, 1):
        step_tree = tree.add(Text(f"Step {i}: {step['step']}", style="green"))
        if "reasoning" in step:
            step_tree.add(Text(f"Reasoning: {step['reasoning']}", style="yellow"))

    console.print(
        Panel(tree, title="Chain-of-Thought Steps", border_style="cyan", expand=False)
    )


def display_cot_answer(query: str, answer: str, patient_id: str = None):
    """Display the CoT answer using Rich."""
    title = f"[bold magenta]Query:[/bold magenta] {query}"
    if patient_id:
        title += f" [bold cyan](Patient ID: {patient_id})[/bold cyan]"

    console.print(
        Panel(
            f"[bold green]Answer:[/bold green] {answer}",
            title=title,
            border_style="green",
            expand=False,
        )
    )


async def main():
    try:
        # Get authentication token
        auth_token = await get_auth_token()

        # General queries
        general_queries = [
            "What are the common symptoms and treatments for congestive heart failure?",
            "How does diabetes affect kidney function?",
            "What are the risk factors for developing hypertension?",
            "Explain the mechanism of action of ACE inhibitors in treating hypertension.",
            "What are the potential complications of untreated type 2 diabetes?",
        ]

        # Patient-specific queries
        patient_queries = [
            "What is the patient's current medication regimen?",
            "Are there any concerning trends in the patient's recent lab results?",
            "What is the patient's history of cardiovascular events?",
            "Has the patient shown any signs of medication side effects?",
            "What lifestyle modifications should be recommended based on the patient's current condition?",
        ]

        # Process general queries
        for query in general_queries:
            console.rule("[bold blue]New General Query", style="blue")
            try:
                cot_steps = await generate_cot_steps(query, auth_token)
                display_cot_steps(query, cot_steps)
            except Exception as query_error:
                console.print(
                    f"[bold red]Error processing query:[/bold red] {query_error}"
                )
            await asyncio.sleep(1)

        # Process patient-specific queries
        for query in patient_queries:
            console.rule("[bold green]New Patient-Specific Query", style="green")
            try:
                cot_steps = await generate_cot_steps(query, auth_token, PATIENT_ID)
                display_cot_steps(query, cot_steps, PATIENT_ID)
                cot_answer = await generate_cot_answer(query, auth_token, PATIENT_ID)
                display_cot_answer(query, cot_answer, PATIENT_ID)
            except Exception as query_error:
                console.print(
                    f"[bold red]Error processing query:[/bold red] {query_error}"
                )
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        console.print(f"[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    asyncio.run(main())
