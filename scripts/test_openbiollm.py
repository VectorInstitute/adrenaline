from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
import backoff

# Set the base URL for the API
BASE_URL = "http://gpu039:8080/v1"

# Initialize the OpenAI client
client = OpenAI(base_url=BASE_URL, api_key="EMPTY")

# Initialize Rich console
console = Console()


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def send_chat_prompt(
    prompt: str, model: str = "Llama3-OpenBioLLM-70B", max_tokens: int = 1024
) -> dict:
    """Send a prompt to the chat completions endpoint with retries."""
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful and knowledgeable medical assistant. Provide accurate and concise information about medical conditions and symptoms.",
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
        return completion
    except Exception as e:
        console.print(f"[bold yellow]An error occurred: {e}. Retrying...[/bold yellow]")
        raise


def display_response(response):
    """Display the response in a formatted manner."""
    if response and response.choices:
        text = response.choices[0].message.content.strip()
        panel = Panel(text, title="Response", border_style="blue", expand=False)
        console.print(panel)
    else:
        console.print("[bold red]No valid response data to display.[/bold red]")


# Example usage
if __name__ == "__main__":
    prompt = "I have pain on my right shoulder. What could be the cause?"

    with console.status("[bold green]Sending request...[/bold green]"):
        try:
            response = send_chat_prompt(prompt)
            if response:
                display_response(response)
            else:
                console.print(
                    "[bold red]Failed to get a valid response after retries.[/bold red]"
                )
        except Exception as e:
            console.print(
                f"[bold red]Failed to get a response after multiple attempts: {e}[/bold red]"
            )
