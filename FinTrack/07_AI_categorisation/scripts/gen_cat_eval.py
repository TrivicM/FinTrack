import json
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import os
import sys

def load_data(transactions_path, categories_path):
    with open(transactions_path, "r", encoding="utf-8") as f:
        transactions = json.load(f)
    with open(categories_path, "r", encoding="utf-8") as f:
        ai_categories = json.load(f)
    return transactions, ai_categories

def build_keyword_mappings(ai_categories):
    keyword_to_category = {}
    category_to_keywords = defaultdict(set)
    keyword_confidence = {}
    all_keywords = []
    for entry in ai_categories:
        cat = entry.get("Category", "").strip().lower()
        for kw_obj in entry.get("Keywords", []):
            # kw_obj is a dict with 'keyword', 'reasoning', 'confidence'
            kw_l = kw_obj.get("keyword", "").strip().lower()
            confidence = kw_obj.get("confidence", None)
            all_keywords.append(kw_l)
            if kw_l in keyword_to_category:
                keyword_to_category[kw_l].add(cat)
            else:
                keyword_to_category[kw_l] = {cat}
            category_to_keywords[cat].add(kw_l)
            if confidence is not None:
                keyword_confidence[kw_l] = confidence
    return keyword_to_category, category_to_keywords, all_keywords, keyword_confidence

def match_transactions(transactions, keyword_to_category):
    unmatched = []
    matched_categories = []
    for tx in transactions:
        text = f"{tx.get('sender_receiver','')} {tx.get('booking_text','')} {tx.get('purpose','')}".lower()
        found = False
        for kw, cats in keyword_to_category.items():
            if kw and kw in text:
                matched_categories.extend(list(cats))
                found = True
                break
        if not found:
            unmatched.append(tx)
    return matched_categories, unmatched

def find_duplicate_keywords(keyword_to_category):
    return {kw: cats for kw, cats in keyword_to_category.items() if len(cats) > 1}

def check_category_consistency(transactions, keyword_to_category):
    tx_to_category = defaultdict(set)
    for tx in transactions:
        text = f"{tx.get('sender_receiver','')} {tx.get('booking_text','')} {tx.get('purpose','')}".lower()
        for kw, cats in keyword_to_category.items():
            if kw and kw in text:
                tx_to_category[text].update(cats)
    inconsistent = {tx: cats for tx, cats in tx_to_category.items() if len(cats) > 1}
    return inconsistent

def find_missing_categories(category_to_keywords):
    desired_categories = {
        "haushold", "electricity", "maintenance", "rent", "salary", "bank loan",
        "taxes and fees", "insurance", "leisure", "creditcard", "medicine", "sport",
        "clothing", "atm", "other", "transportation"
    }
    present_categories = set(category_to_keywords.keys())
    return desired_categories - present_categories

def print_confidence_statistics(keyword_confidence):
    confidences = [v for v in keyword_confidence.values() if isinstance(v, (int, float))]
    if confidences:
        print("\nConfidence statistics for all keywords:")
        print(f"  Min confidence: {min(confidences):.2f}")
        print(f"  Max confidence: {max(confidences):.2f}")
        print(f"  Avg confidence: {sum(confidences)/len(confidences):.2f}")

        # Plot histogram of confidence values
        plt.figure(figsize=(7, 4))
        plt.hist(confidences, bins=20, color='skyblue', edgecolor='black')
        plt.title("Histogram of Keyword Confidence Scores")
        plt.xlabel("Confidence")
        plt.ylabel("Number of Keywords")
        plt.tight_layout()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        outputs_dir = os.path.join(script_dir, "..", "outputs")
        plt.savefig(os.path.join(outputs_dir, "confidence_histogram.png"), dpi=120)
        plt.close()
        print("Histogram of keyword confidence scores saved as confidence_histogram.png")
    else:
        print("\nNo confidence values found.")

def print_summary(transactions, unmatched, inconsistent):
    coverage = 100 * (len(transactions) - len(unmatched)) / len(transactions) if transactions else 0
    print("\nSummary:")
    print(f"Total transactions: {len(transactions)}")
    print(f"Matched transactions: {len(transactions) - len(unmatched)}")
    print(f"Unmatched transactions: {len(unmatched)}")
    print(f"Inconsistent categorizations: {len(inconsistent)}")
    print(f"Coverage: {coverage:.2f}%")

def save_unmatched_transactions(unmatched, output_path=None):
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "uncategorized_transactions.json")
        output_path = os.path.normpath(output_path)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unmatched, f, indent=2, ensure_ascii=False)

def save_inconsistent_categorizations(inconsistent, transactions, output_path="inconsistent_categorizations.json"):
    # Build a mapping from normalized transaction text to the full transaction dict
    tx_text_to_full = {}
    for tx in transactions:
        text = f"{tx.get('sender_receiver','')} {tx.get('booking_text','')} {tx.get('purpose','')}".lower()
        tx_text_to_full[text] = tx

    inconsistent_list = []
    for tx_text, cats in inconsistent.items():
        tx_full = tx_text_to_full.get(tx_text)
        if tx_full:
            inconsistent_list.append({
                "transaction": tx_full,
                "categories": list(cats)
            })
        else:
            # fallback: include the text if not found
            inconsistent_list.append({
                "transaction_text": tx_text,
                "categories": list(cats)
            })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(inconsistent_list, f, indent=2, ensure_ascii=False)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    outputs_dir = os.path.join(script_dir, "..", "outputs")
    if len(sys.argv) >= 5:
        transactions_path = sys.argv[1]
        categories_path = sys.argv[2]
        uncategorized_path = sys.argv[3]
        inconsistent_path = sys.argv[4]
    else:
        transactions_path = os.path.join(outputs_dir, "transactions.json")
        categories_path = os.path.join(outputs_dir, "AI_Categorisation_cleaned.json")
        uncategorized_path = os.path.join(outputs_dir, "uncategorized_transactions.json")
        inconsistent_path = os.path.join(outputs_dir, "inconsistent_categorizations.json")

    transactions, ai_categories = load_data(transactions_path, categories_path)
    keyword_to_category, category_to_keywords, all_keywords, keyword_confidence = build_keyword_mappings(ai_categories)
    matched_categories, unmatched = match_transactions(transactions, keyword_to_category)
    duplicates = find_duplicate_keywords(keyword_to_category)
    inconsistent = check_category_consistency(transactions, keyword_to_category)
    missing = find_missing_categories(category_to_keywords)
    save_unmatched_transactions(unmatched, uncategorized_path)
    save_inconsistent_categorizations(inconsistent, transactions, inconsistent_path)

    print_confidence_statistics(keyword_confidence)
    print_summary(transactions, unmatched, inconsistent)

if __name__ == "__main__":
    main()