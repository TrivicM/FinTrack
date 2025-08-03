import json
import sys
import os
from collections import defaultdict

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def clean_ai_categorisation(input_path, output_path):
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