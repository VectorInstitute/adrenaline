"""Test the openbiollm API endpoint."""

import requests

BASE_URL = "http://gpu054:8080/v1"


def api_request(endpoint: str, data: dict) -> dict:
    """Make an API request and return the JSON response."""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()


def send_prompt(
    prompt: str, model: str = "Llama3-OpenBioLLM-70B", max_tokens: int = 2048
) -> dict:
    """Send a prompt to the completions endpoint."""
    data = {"model": model, "prompt": prompt, "max_tokens": max_tokens}
    return api_request("/completions", data)


# Example usage
if __name__ == "__main__":
    prompt = "I have pain on my right shoulder. What could be the cause?"
    try:
        response = send_prompt(prompt, max_tokens=1024)  # Increased max_tokens
        print("API Response:")
        print(response)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
