import os
import sys
import json
from google import genai
from pydantic import BaseModel
import time

class KeywordEntry(BaseModel):
    keyword: str
    reasoning: str
    confidence: float

class GenAICat(BaseModel):
    """
    GenAICat represents a generic AI-generated category with associated keywords.

    Attributes:
        Category (str): The name of the category.
        Keywords (list[str]): A list of keywords relevant to the category.
    """
    Category: str
    Keywords: list[KeywordEntry]

MAX_ATTEMPTS = 3

def is_valid_json(text):
    try:
        json.loads(text)
        return True
    except Exception:
        return False

def main():
    """
    Main function to categorize transactions using AI.
    Reads the prompt and transaction data, sends it to the AI model, and saves the response.
    """
    start_time = time.time()  # Start timing the script execution

    api_key = os.environ.get("GENAI_API_KEY")  # Get the API key from environment variables
    client = genai.Client(api_key=api_key)  # Initialize the GenAI client

    script_dir = os.path.dirname(os.path.abspath(__file__))
    inputs_dir = os.path.join(script_dir, "..", "inputs")
    prompt_path = os.path.join(inputs_dir, "prompt.json")
    examples_path = os.path.join(inputs_dir, "categorization_examples.json")

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_data = json.load(f)
    prompt = prompt_data["prompt"]

    with open(examples_path, "r", encoding="utf-8") as f:
        examples = json.load(f)

    examples_text = ""
    for ex in examples:
        category = ex.get("Category", "")
        keywords = ex.get("Keywords", [])
        for kw in keywords:
            examples_text += f'Category: {category}, Keyword: {kw}\n'

    # Read the bank statement data from JSON
    input_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(inputs_dir, "transactions.json")
    output_file = sys.argv[2] if len(sys.argv) > 2 else os.path.join(script_dir, "..", "outputs", "AI_Categorisation.json")
    with open(input_file, "r", encoding="utf-8") as f:
        transactions = json.load(f)

    full_prompt = (
        f"{prompt}\n\n"
        f"Sample Output Format:\n{examples_text}\n\n"
        f"Here is the bank statement data in JSON format:\n"
        f"{json.dumps(transactions, indent=2, ensure_ascii=False)}"
    )

    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=full_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": list[GenAICat],
                "temperature": 0.2  # Lower temperature for more consistent, deterministic categorization
            }
        )
        if is_valid_json(response.text):
            break
        print(f"Attempt {attempt}: Invalid JSON received, retrying...")
        time.sleep(2)
    else:
        print("Failed to get valid JSON after several attempts.")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(response.text)
        raise RuntimeError("GenAI did not return valid JSON.")

    # Write the valid JSON to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(response.text)
    with open(os.path.join(inputs_dir, "log_prompt.json"), "w", encoding="utf-8") as f:
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
