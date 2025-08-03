def build_batch_prompt(transactions):
    categories = [
        "Household", "Electricity", "Maintenance", "Rent", "Salary", "Bank loan", "Taxes and Fees", "Insurance", "Leisure", "Creditcard", "Medicine", "Sport", "Clothing", "Transportation", "ATM", "Other"
    ]

    prompt = f"""
You are a financial assistant helping to categorize bank transactions.

Each transaction below is currently labeled as "Other". This label was used as a fallback and is likely incorrect. Your job is to assign the most appropriate category from this list:

{", ".join(categories)}

Instructions:
- Do NOT assign "Other" again unless it's truly unclear what the transaction refers to.
- Be precise. Use your knowledge of brand names, services, and context.
- Output a JSON array with:
- original_description
- reasoning (based on known info or assumptions)
- new_category
- confidence
- confidence should be a float between 0.0 and 1.0, where 1.0 means very confident.
- If you can't categorize a transaction, explain why in the reasoning.
Now re-categorize the following:
"""

    for i, t in enumerate(transactions):
        prompt += f"{i+1}. {t['description']}\n"

    return prompt.strip()

