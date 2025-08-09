"""
main_categorization.py

This script orchestrates the iterative AI-based categorization workflow for financial transactions.
It automates the process of running external scripts for categorization, cleaning, and evaluation in multiple rounds,
each time focusing on transactions that remain uncategorized. The workflow continues until all transactions are categorized,
no further progress is made, or a maximum number of iterations is reached.

Key features:
    - Runs the AI categorization, cleaning, and evaluation scripts in sequence for each iteration.
    - Tracks and manages uncategorized and inconsistently categorized transactions.
    - Merges and consolidates results from all iterations into final output files.
    - Ensures robust, automated processing for high-quality, comprehensive categorization.

This script is intended to be the main entry point for the categorization pipeline and should be run after preparing
the input transaction data and AI models.

Dependencies:
    - Python 3.x
    - Required Python packages: subprocess, json, os, time, glob

Usage:
    1. Set up the environment: Ensure Python 3.x is installed and the required packages are available.
    2. Prepare input data: Place the input transaction data file (transactions.json) in the 'inputs' directory.
    3. Configure AI models: Ensure the AI models and scripts are available in the 'scripts' directory.
    4. Run the script: Execute this script (main_categorization.py) to start the categorization process.
    5. Review results: Check the 'outputs' directory for the categorized transaction files and reports.
"""

import subprocess
import json
import os
import time
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
INPUTS_DIR = os.path.join(BASE_DIR, "inputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)
MAX_ITERATIONS = 5
TARGET_COVERAGE = 1.0  # 100%

def run_script(script_and_args):
    """
    Executes a Python script with the specified arguments as a subprocess.

    Args:
        script_and_args (list): A list containing the script name followed by its arguments.

    Prints:
        The command being run, the standard output of the subprocess, and any errors encountered.
    
    """
    print(f"Running: {' '.join(script_and_args)}")
    result = subprocess.run(["python"] + script_and_args, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("⚠️ Error:", result.stderr)

def load_uncategorized_count(uncategorized_path):
    """
    Loads and returns the count of uncategorized items from a JSON file.

    Args:
        uncategorized_path (str): The file path to the JSON file containing uncategorized items.

    Returns:
        int: The number of uncategorized items. Returns 0 if the file does not exist.
    """

    if not os.path.exists(uncategorized_path):
        return 0
    with open(uncategorized_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return len(data)

def merge_json_files(pattern, key=None):
    """
    Merge multiple JSON files matching a glob pattern into a single list, removing duplicates.

    Args:
        pattern (str): Glob pattern to match JSON files.
        key (str, optional): Key for identifying unique entries; if None, the entire entry is used.

    Returns:
        list: Merged and deduplicated JSON objects from all matched files.
    """

    merged = []
    seen = set()
    for fname in sorted(glob.glob(pattern)):
        with open(fname, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    data = [data]
                for entry in data:
                    # Use a unique key if provided, else use str(entry)
                    unique = entry.get(key) if key and isinstance(entry, dict) and key in entry else json.dumps(entry, sort_keys=True)
                    if unique not in seen:
                        merged.append(entry)
                        seen.add(unique)
            except Exception as e:
                print(f"Error reading {fname}: {e}")
    return merged

def save_merged(pattern, outname, key=None):
    """
    Merge JSON files matching a pattern and save the result to an output file.

    Args:
        pattern (str): Glob pattern to match JSON files.
        outname (str): Output filename for the merged JSON data.
        key (str, optional): Key for deduplication.

    Returns:
        None

    Side Effects:
        Writes the merged JSON data to the specified output file and prints a confirmation message.
    """

    merged = merge_json_files(pattern, key)
    with open(outname, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"Merged file saved as {outname}")

def merge_category_json_files(pattern):
    """
    Merge multiple JSON files containing category-keyword mappings into a single list.

    Args:
        pattern (str): Glob pattern to match JSON files.

    Returns:
        list: List of dictionaries, each with "Category" and "Keywords" keys.
    """

    merged = {}
    for fname in sorted(glob.glob(pattern)):
        with open(fname, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for entry in data:
                    cat = entry.get("Category")
                    keywords = entry.get("Keywords", [])
                    if not cat:
                        continue
                    if cat not in merged:
                        merged[cat] = []
                    # Add only unique keywords
                    existing = {kw['keyword'] for kw in merged[cat] if 'keyword' in kw}
                    for kw in keywords:
                        if 'keyword' in kw and kw['keyword'] not in existing:
                            merged[cat].append(kw)
                            existing.add(kw['keyword'])
            except Exception as e:
                print(f"Error reading {fname}: {e}")
    # Output as list of dicts, sorted by category
    return [
        {"Category": cat, "Keywords": sorted(merged[cat], key=lambda x: x["keyword"])}
        for cat in sorted(merged)
    ]

def save_merged_categories(pattern, outname):
    """
    Merges multiple category JSON files matching a given pattern and saves the merged result to a specified output file.

    Args:
        pattern (str): The glob pattern to match input JSON files for merging.
        outname (str): The filename for the merged output JSON file.

    Returns:
        None

    Side Effects:
        Writes the merged JSON data to the specified output file and prints a confirmation message.
    """

    merged = merge_category_json_files(pattern)
    with open(outname, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"Merged file saved as {outname}")

def main():
    """
    Run the iterative categorization workflow for financial transactions.

    Executes categorization, cleaning, and evaluation scripts in multiple rounds,
    manages uncategorized transactions, and merges results into consolidated output files.
    """

    iteration = 1
    previous_count = None
    gen_cat_input = os.path.join(INPUTS_DIR, "transactions.json")  # Start with all transactions

    while iteration <= MAX_ITERATIONS:
        print(f"\n🔁 Iteration {iteration}...")

        cat_path = os.path.join(OUTPUTS_DIR, f"AI_Categorisation_{iteration}.json")
        cleaned_cat_path = os.path.join(OUTPUTS_DIR, f"AI_Categorisation_cleaned_{iteration}.json")
        uncategorized_path = os.path.join(OUTPUTS_DIR, f"uncategorized_transactions_{iteration}.json")
        inconsistent_path = os.path.join(OUTPUTS_DIR, f"inconsistent_categorizations_{iteration}.json")

        # 1. Run AI categorization on the appropriate input file
        # Pass the input file as an argument to GenCat.py
        run_script([os.path.join(SCRIPTS_DIR, "GenCat.py"), gen_cat_input, cat_path])

        # 2. Clean the output
        run_script([os.path.join(SCRIPTS_DIR, "clean_ai_categorisation.py"), cat_path, cleaned_cat_path])

        # 3. Evaluate
        run_script([
            os.path.join(SCRIPTS_DIR, "gen_cat_eval.py"),
            gen_cat_input,
            cleaned_cat_path,
            uncategorized_path,
            inconsistent_path
        ])

        # 4. Check number of remaining uncategorized
        count = load_uncategorized_count(uncategorized_path)
        print(f"🧾 Unmatched transactions remaining: {count}")

        if count == 0:
            print("\n✅ All transactions categorized.")
            break

        if previous_count is not None and count == previous_count:
            print("\n⚠️ No improvement from last iteration. Stopping.")
            break

        previous_count = count
        iteration += 1

        # After the first iteration, switch to uncategorized_transactions.json
        gen_cat_input = uncategorized_path
        time.sleep(1)  # optional pause

    else:
        print(f"\n⏹️ Reached max iterations ({MAX_ITERATIONS}). Some transactions may remain uncategorized.")

    # Merge all AI_Categorisation_cleaned_*.json
    save_merged(os.path.join(OUTPUTS_DIR, "AI_Categorisation_cleaned_*.json"), os.path.join(OUTPUTS_DIR, "AI_Categorisation_cleaned.json"))
    # Merge all AI_Categorisation_*.json
    save_merged(os.path.join(OUTPUTS_DIR, "AI_Categorisation_*.json"), os.path.join(OUTPUTS_DIR, "AI_Categorisation.json"))
    # Merge all uncategorized_transactions_*.json
    save_merged(os.path.join(OUTPUTS_DIR, "uncategorized_transactions_*.json"), os.path.join(OUTPUTS_DIR, "uncategorized_transactions.json"))
    # Merge all inconsistent_categorizations_*.json
    save_merged(os.path.join(OUTPUTS_DIR, "inconsistent_categorizations_*.json"), os.path.join(OUTPUTS_DIR, "inconsistent_categorizations.json"))
    # Merge category files
    save_merged_categories(os.path.join(OUTPUTS_DIR, "AI_Categorisation_cleaned_*.json"), os.path.join(OUTPUTS_DIR, "AI_Categorisation_cleaned.json"))
    save_merged_categories(os.path.join(OUTPUTS_DIR, "AI_Categorisation_*.json"), os.path.join(OUTPUTS_DIR, "AI_Categorisation.json"))

if __name__ == "__main__":
    main()
