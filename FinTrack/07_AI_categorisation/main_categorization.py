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
    print(f"Running: {' '.join(script_and_args)}")
    result = subprocess.run(["python"] + script_and_args, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("⚠️ Error:", result.stderr)

def load_uncategorized_count(uncategorized_path):
    if not os.path.exists(uncategorized_path):
        return 0
    with open(uncategorized_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return len(data)

def merge_json_files(pattern, key=None):
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
    merged = merge_json_files(pattern, key)
    with open(outname, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"Merged file saved as {outname}")

def merge_category_json_files(pattern):
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
    merged = merge_category_json_files(pattern)
    with open(outname, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"Merged file saved as {outname}")

def main():
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
