import json
import time
from pathlib import Path
import os
import google.generativeai as genai

script_dir = os.path.dirname(os.path.abspath(__file__))
outputs_dir = os.path.join(script_dir, "..", "outputs")
inputs_dir = os.path.join(script_dir, "..", "inputs")

INPUT_PATH = Path(os.path.join(outputs_dir, "AI_Categorisation.json"))
OUTPUT_PATH = Path(os.path.join(outputs_dir, "AI_Categorisation_refined.json"))

# Setup Gemini Flash
genai.configure(api_key="GEMINI_API_KEY")  # Replace with your actual key
model = genai.GenerativeModel("models/gemini-1.5-flash")

# Categories you expect
KNOWN_CATEGORIES = [
    "Household", "Electricity", "Maintenance", "Rent", "Salary",
    "Bank loan", "Taxes and Fees", "Insurance", "Leisure", "Creditcard",
    "Medicine", "Sport", "Clothing", "Transportation", "ATM", "Other"
]


# Load AI-categorized transactions
def load_transactions(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# Save output
def save_transactions(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Build batch prompt
def build_batch_prompt(transactions):
    instructions = f"""
You are an expert financial assistant. Your task is to re-categorize the following bank transactions.
Each transaction is currently labeled as "Other", but this may be incorrect.

Use ONLY the following categories:
{", ".join(KNOWN_CATEGORIES)}

IMPORTANT:
- Do NOT use "Other" unless the transaction clearly doesn't fit anywhere else.
- Return a JSON list where each item has:
  "original_description", "new_category", "confidence", and "reasoning".

Transactions:
"""
    for idx, t in enumerate(transactions):
        instructions += f"{idx+1}. {t['description']}\n"

    instructions += "\nReturn JSON in this format:\n[\n  {{ \"original_description\": \"...\", \"new_category\": \"...\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\" }},\n  ...\n]"

    return instructions.strip()

# Send a batch to Gemini
def process_batch(batch):
    prompt = build_batch_prompt(batch)
    try:
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"[❌ ERROR] Batch failed: {e}")
        return None

# Refine all transactions labeled "Other"
def refine(transactions, batch_size=10):
    refined = []
    other_to_fix = [t for t in transactions if t.get("category") == "Other"]
    rest = [t for t in transactions if t.get("category") != "Other"]

    print(f"🔍 Refining {len(other_to_fix)} 'Other' transactions in batches of {batch_size}...")

    for i in range(0, len(other_to_fix), batch_size):
        batch = other_to_fix[i:i+batch_size]
        print(f"🔁 Batch {i//batch_size + 1}/{(len(other_to_fix)-1)//batch_size + 1}...")

        results = process_batch(batch)
        if results is None:
            print("⚠️ Skipping this batch.")
            refined.extend(batch)
            continue

        for original, updated in zip(batch, results):
            original["category"] = updated.get("new_category", "Other")
            original["confidence"] = updated.get("confidence", 0.5)
            original["reasoning"] = updated.get("reasoning", "No reasoning provided.")
            refined.append(original)

        time.sleep(1)  # avoid overloading the API

    return refined + rest

# Main loop
def main():
    print("🚀 Loading transactions...")
    data = load_transactions(INPUT_PATH)

    print("📊 Starting refinement loop with Gemini Flash...")
    updated = refine(data)

    others_remaining = sum(1 for t in updated if t["category"] == "Other")
    print(f"✅ Done. Remaining 'Other': {others_remaining} of {len(updated)}")

    print(f"💾 Saving to {OUTPUT_PATH}...")
    save_transactions(updated, OUTPUT_PATH)
    print("🎉 All done.")

if __name__ == "__main__":
    main()
