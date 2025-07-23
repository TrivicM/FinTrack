import json
from collections import defaultdict, Counter

def main():

    # --- Load data ---
    with open("transactions.json", "r", encoding="utf-8") as f:
        transactions = json.load(f)

    with open("AI_Categorisation.json", "r", encoding="utf-8") as f:
        ai_categories = json.load(f)

    # --- Flatten keywords and build mappings ---
    keyword_to_category = {}
    category_to_keywords = defaultdict(set)
    all_keywords = []

    for entry in ai_categories:
        cat = entry.get("Category", "").strip().lower()
        for kw in entry.get("Keywords", []):
            kw_l = kw.strip().lower()
            all_keywords.append(kw_l)
            if kw_l in keyword_to_category:
                keyword_to_category[kw_l].add(cat)
            else:
                keyword_to_category[kw_l] = {cat}
            category_to_keywords[cat].add(kw_l)

    # --- 1. Coverage: Match each transaction to a keyword ---
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

    coverage = 100 * (len(transactions) - len(unmatched)) / len(transactions) if transactions else 0

    print(f"Total transactions: {len(transactions)}")
    print(f"Matched transactions: {len(transactions) - len(unmatched)}")
    print(f"Unmatched transactions: {len(unmatched)}")
    print(f"Coverage: {coverage:.2f}%")
    if unmatched:
        print("\nSample unmatched transactions:")
        for tx in unmatched[:5]:
            print(tx)

    # --- 2. Duplicate keywords (keywords in more than one category) ---
    duplicates = {kw: cats for kw, cats in keyword_to_category.items() if len(cats) > 1}
    if duplicates:
        print("\nDuplicate keywords (appear in multiple categories):")
        for kw, cats in duplicates.items():
            print(f"  '{kw}': {list(cats)}")
    else:
        print("\nNo duplicate keywords found.")

    # --- 3. Category consistency (same sender/receiver or booking_text in multiple categories) ---
    tx_to_category = defaultdict(set)
    for tx in transactions:
        text = f"{tx.get('sender_receiver','')} {tx.get('booking_text','')} {tx.get('purpose','')}".lower()
        for kw, cats in keyword_to_category.items():
            if kw and kw in text:
                tx_to_category[text].update(cats)
    if tx_to_category:
        inconsistent = {tx: cats for tx, cats in tx_to_category.items() if len(cats) > 1}
        if inconsistent:
            print("\nInconsistent categorization (same transaction text matches multiple categories):")
            for tx, cats in list(inconsistent.items())[:5]:
                print(f"  '{tx}': {list(cats)}")
        else:
            print("\nNo inconsistent categorizations found.")

    # --- 4. Missing categories (desired categories not present in AI_Categorisation.json) ---
    desired_categories = {
        "haushold", "electricity", "maitenance", "rent", "tenants", "salary", "bank loan",
        "taxes and fees", "insurance", "leisure", "creditcard", "medicine", "sport",
        "clothing", "travel", "transportation", "atm", "other"
    }
    present_categories = set(category_to_keywords.keys())
    missing = desired_categories - present_categories
    if missing:
        print("\nMissing categories (not present in AI_Categorisation.json):")
        for cat in missing:
            print(f"  {cat}")
    else:
        print("\nAll desired categories are present.")

    # --- 5. Category distribution ---
    print("\nCategory distribution (matched transactions):")
    cat_counts = Counter(matched_categories)
    for cat, count in cat_counts.most_common():
        print(f"  {cat}: {count}")

   

if __name__ == "__main__":
    main()