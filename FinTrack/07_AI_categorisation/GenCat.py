from google import genai
from pydantic import BaseModel
import json  # Add this import
import time  # Add this import for timing the script execution
import os  # Import os to handle file paths



class GenAICat(BaseModel):
    """
    GenAICat represents a generic AI-generated category with associated keywords.

    Attributes:
        Category (str): The name of the category.
        Keywords (list[str]): A list of keywords relevant to the category.
    """
    Category: str
    Keywords: list[str]

def main():
    """
    Main function to categorize transactions using AI.
    Reads the prompt and transaction data, sends it to the AI model, and saves the response.
    """
    start_time = time.time()  # Start timing the script execution

    api_key = os.environ.get("GENAI_API_KEY")  # Get the API key from environment variables
    client = genai.Client(api_key=api_key)  # Initialize the GenAI client

    # Read the prompt from a JSON file
    with open("prompt.json", "r", encoding="utf-8") as f:
        prompt_data = json.load(f)
    prompt = prompt_data["prompt"]

    # Read the bank statement data from JSON
    with open("transactions.json", "r", encoding="utf-8") as f:
        transactions = json.load(f)

    # Prepare the full prompt for the LLM
    full_prompt = (
        f"{prompt}\n\n"
        f"Here is the bank statement data in JSON format:\n"
        f"{json.dumps(transactions, indent=2, ensure_ascii=False)}"
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=full_prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[GenAICat],
        },
    )

    # Write the response to a JSON file
    with open("AI_Categorisation.json", "w", encoding="utf-8") as f:
        f.write(response.text)

    # Use instantiated objects.
    my_GenAICats: list[GenAICat] = response.parsed
    # Read the prompt from a JSON file
    with open("prompt.json", "r", encoding="utf-8") as f:
        prompt_data = json.load(f)
    prompt = prompt_data["prompt"]

    # Read the bank statement data from JSON
    with open("transactions.json", "r", encoding="utf-8") as f:
        transactions = json.load(f)

    # Prepare the full prompt for the LLM
    # You can adjust the formatting as needed for your use case
    full_prompt = (
        f"{prompt}\n\n"
        f"Here is the bank statement data in JSON format:\n"
        f"{json.dumps(transactions, indent=2, ensure_ascii=False)}"
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=full_prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[GenAICat],
        },
    )

    # Write the response to a JSON file
    with open("AI_Categorisation.json", "w", encoding="utf-8") as f:
        f.write(response.text)

    # Use instantiated objects.
    my_GenAICats: list[GenAICat] = response.parsed

    end_time = time.time()
    duration = end_time - start_time
    print(f"Done .... script execution time: {duration:.2f} seconds")

if __name__ == "__main__":
    main()