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

    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, "prompt.json")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_data = json.load(f)
    prompt = prompt_data["prompt"]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    examples_path = os.path.join(script_dir, "categorization_examples.json")
    with open(examples_path, "r", encoding="utf-8") as f:
        examples = json.load(f)

    examples_text = "\n".join(
        f'Transaction: {{"booking_text": "{ex.get("booking_text", "")}", "sender_receiver": "{ex.get("sender_receiver", "")}", "purpose": "{ex.get("purpose", "")}"}}\n'
        f'Category: {ex.get("expected_category", "")}, Keyword: {ex.get("expected_keyword", "")}'
        for ex in examples
    )

    # Read the bank statement data from JSON
    with open("transactions.json", "r", encoding="utf-8") as f:
        transactions = json.load(f)

    full_prompt = (
        f"{prompt}\n\n"
        f"Examples:\n{examples_text}\n\n"
        f"Here is the bank statement data in JSON format:\n"
        f"{json.dumps(transactions, indent=2, ensure_ascii=False)}"
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=full_prompt,
        config={
            "response_mime_type": "application/json",     
            "response_schema": list[GenAICat],
            "temperature": 0.2  # Lower temperature for more consistent, deterministic categorization
        }
    )       

    # Write the response to a JSON file
    with open("AI_Categorisation.json", "w", encoding="utf-8") as f:
        f.write(response.text)
    with open("log_prompt.json", "w", encoding="utf-8") as f:
        f.write(full_prompt)

    # Use instantiated objects.
    my_GenAICats: list[GenAICat] = response.parsed

    def count_tokens(text):
        # Approximate: split by whitespace (not exact for LLMs, but gives a rough idea)
        return len(text.split())

    prompt_tokens = count_tokens(full_prompt)
    response_tokens = count_tokens(response.text)
    print(f"Approximate prompt tokens: {prompt_tokens}")
    print(f"Approximate response tokens: {response_tokens}")

    end_time = time.time()
    duration = end_time - start_time
    print(f"Done .... script execution time: {duration:.2f} seconds")

if __name__ == "__main__":
    main()
