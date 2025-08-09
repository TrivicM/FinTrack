"""
clean_ai_categorisation.py

This script cleans and consolidates AI-generated transaction categorization data.
It merges duplicate keywords (preferring non-'Other' categories), sorts categories and keywords,
and outputs a cleaned JSON file for downstream analysis and reporting.

Note:
    The output from the AI categorization process often contains duplicate or inconsistent keyword assignments,
    making it difficult to use directly for analysis or reporting. This script is essential for cleaning,
    consolidating, and standardizing the AI-generated categorization data, ensuring that the resulting JSON file
    is well-structured and reliable for further processing (such as in analysis.py).

Typical usage:
    python clean_ai_categorisation.py input.json output.json
"""

import json
import sys
import os
from collections import defaultdict

def load_json(path):
    """
    Loads and returns the contents of a JSON file from the specified path.

    Args:
        path (str): The file path to the JSON file.

    Returns:
        dict or list: The parsed JSON data from the file.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    """
    Save the given data as a JSON file at the specified path.

    Args:
        data (Any): The data to be serialized and saved as JSON.
        path (str or Path): The file path where the JSON data will be written.

    Raises:
        TypeError: If the data provided is not serializable to JSON.
        OSError: If the file cannot be written due to an OS-related error.
    """
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def clean_ai_categorisation(input_path, output_path):
    """
    Cleans and consolidates AI categorisation data from a JSON file.
    This function reads a JSON file containing categories and associated keywords (with reasoning and confidence),
    merges duplicate keywords (preferring non-'Other' categories when conflicts arise), and outputs a cleaned,
    sorted mapping of categories to their keywords.
    
    Args:
        input_path (str): Path to the input JSON file containing the raw categorisation data.
        output_path (str): Path where the cleaned JSON file will be saved.
    
    The output JSON will be a list of dictionaries, each with:
        - "Category": The category name.
        - "Keywords": A sorted list of keyword entries (each with "keyword", "reasoning", and "confidence").
    
    Side Effects:
        - Writes the cleaned data to the specified output path.
        - Prints a confirmation message upon successful save.
    """
    
    data = load_json(input_path)
    category_keywords = defaultdict(list)
    keyword_to_category = {}

    # Merge categories and collect keywords (with reasoning and confidence)
    for entry in data:
        cat = entry.get("Category", "").strip()
        for kw_obj in entry.get("Keywords", []):
            kw_clean = kw_obj.get("keyword", "").strip()
            reasoning = kw_obj.get("reasoning", "")
            confidence = kw_obj.get("confidence", None)
            # If keyword already assigned, skip or warn
            if kw_clean in keyword_to_category:
                # Prefer non-'Other' category
                if keyword_to_category[kw_clean]["Category"] == "Other" and cat != "Other":
                    keyword_to_category[kw_clean] = {
                        "Category": cat,
                        "Entry": {
                            "keyword": kw_clean,
                            "reasoning": reasoning,
                            "confidence": confidence
                        }
                    }
                # Otherwise, keep the first non-'Other' assignment
            else:
                keyword_to_category[kw_clean] = {
                    "Category": cat,
                    "Entry": {
                        "keyword": kw_clean,
                        "reasoning": reasoning,
                        "confidence": confidence
                    }
                }

    # Build cleaned mapping
    for kw, info in keyword_to_category.items():
        cat = info["Category"]
        entry = info["Entry"]
        category_keywords[cat].append(entry)

    # Output as list of dicts, sorted by category
    cleaned = []
    for cat in sorted(category_keywords):
        cleaned.append({
            "Category": cat,
            "Keywords": sorted(category_keywords[cat], key=lambda x: x["keyword"])
        })

    save_json(cleaned, output_path)
    print(f"Cleaned AI_Categorisation.json saved to {output_path}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    outputs_dir = os.path.join(script_dir, "..", "outputs")
    if len(sys.argv) >= 3:
        input_path = sys.argv[1]
        output_path = sys.argv[2]
    else:
        input_path = os.path.join(outputs_dir, "AI_Categorisation.json")
        output_path = os.path.join(outputs_dir, "AI_Categorisation_cleaned.json")
    clean_ai_categorisation(input_path, output_path)