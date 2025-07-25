import json
from collections import defaultdict, Counter

def load_data(transactions_path, categories_path):
    """
    Loads transaction data and AI-generated categories from specified JSON files.

    Args:
        transactions_path (str): Path to the JSON file containing transaction data.
        categories_path (str): Path to the JSON file containing AI-generated categories.

    Returns:
        tuple: A tuple containing:
            - transactions (dict or list): The loaded transaction data.
            - ai_categories (dict or list): The loaded AI-generated categories.
    """
    with open(transactions_path, "r", encoding="utf-8") as f:
        transactions = json.load(f)
    with open(categories_path, "r", encoding="utf-8") as f:
        ai_categories = json.load(f)
    return transactions, ai_categories

def build_keyword_mappings(ai_categories):
    """
    Builds mappings between keywords and categories from a list of AI category entries.

    Args:
        ai_categories (list of dict): A list where each dict represents a category entry with keys:
            - "Category" (str): The category name.
            - "Keywords" (list of str): The keywords associated with the category.

    Returns:
        tuple:
            - keyword_to_category (dict): Maps each keyword (str, lowercased) to a set of category names (str, lowercased) it belongs to.
            - category_to_keywords (defaultdict of set): Maps each category name (str, lowercased) to a set of its associated keywords (str, lowercased).
            - all_keywords (list): A list of all keywords (str, lowercased) found in the input, including duplicates.

    Notes:
        - All category names and keywords are stripped of whitespace and converted to lowercase.
        - If a keyword appears in multiple categories, it will be mapped to all relevant categories in keyword_to_category.
    """
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
    return keyword_to_category, category_to_keywords, all_keywords

def match_transactions(transactions, keyword_to_category):
    """
    Matches transactions to categories based on provided keywords.

    Args:
        transactions (list of dict): A list of transaction dictionaries. Each transaction may contain the keys
            'sender_receiver', 'booking_text', and 'purpose'.
        keyword_to_category (dict): A dictionary mapping keywords (str) to sets or lists of categories.

    Returns:
        tuple:
            matched_categories (list): A list of categories matched from the transactions.
            unmatched (list): A list of transaction dictionaries that did not match any keyword.
    """
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
    """
    Finds keywords that are associated with more than one category.

    Args:
        keyword_to_category (dict): A dictionary mapping keywords to a list or set of categories.

    Returns:
        dict: A dictionary containing only the keywords that are mapped to more than one category, 
              with their corresponding categories.
    """
    return {kw: cats for kw, cats in keyword_to_category.items() if len(cats) > 1}

def check_category_consistency(transactions, keyword_to_category):
    """
    Checks for category inconsistencies in a list of transactions based on keyword-to-category mappings.

    Each transaction is analyzed by concatenating its 'sender_receiver', 'booking_text', and 'purpose' fields.
    If a keyword from the mapping is found in the transaction text, the corresponding categories are associated with that transaction.
    A transaction is considered inconsistent if it is associated with more than one category.

    Args:
        transactions (list of dict): List of transaction records, each as a dictionary with keys such as 'sender_receiver', 'booking_text', and 'purpose'.
        keyword_to_category (dict): Mapping from keyword (str) to a set or list of categories (iterable of str).

    Returns:
        dict: A dictionary where keys are transaction texts and values are sets of categories, 
              containing only those transactions that are associated with more than one category.
    """
    tx_to_category = defaultdict(set)
    for tx in transactions:
        text = f"{tx.get('sender_receiver','')} {tx.get('booking_text','')} {tx.get('purpose','')}".lower()
        for kw, cats in keyword_to_category.items():
            if kw and kw in text:
                tx_to_category[text].update(cats)
    inconsistent = {tx: cats for tx, cats in tx_to_category.items() if len(cats) > 1}
    return inconsistent

def find_missing_categories(category_to_keywords):
    """
    Finds and returns the set of desired categories that are missing from the provided category-to-keywords mapping.

    Args:
        category_to_keywords (dict): A dictionary mapping category names (str) to their associated keywords.

    Returns:
        set: A set of category names (str) that are present in the predefined list of desired categories but missing from the keys of the input dictionary.
    """
    desired_categories = {
        "haushold", "electricity", "maitenance", "rent", "tenants", "salary", "bank loan",
        "taxes and fees", "insurance", "leisure", "creditcard", "medicine", "sport",
        "clothing", "travel", "transportation", "atm", "other"
    }
    present_categories = set(category_to_keywords.keys())
    return desired_categories - present_categories

def print_results(transactions, matched_categories, unmatched, duplicates, inconsistent, missing, category_to_keywords):
    """
    Prints a detailed evaluation report of transaction categorization results.

    Args:
        transactions (list): List of all transaction records.
        matched_categories (list): List of categories assigned to matched transactions.
        unmatched (list): List of transactions that could not be matched to any category.
        duplicates (dict): Dictionary mapping duplicate keywords to the set of categories they appear in.
        inconsistent (dict): Dictionary mapping transaction texts to sets of categories when matched to multiple categories.
        missing (list): List of categories that are missing from the AI_Categorisation.json file.
        category_to_keywords (dict): Dictionary mapping categories to their associated keywords.

    Outputs:
        Prints statistics and sample data about matched, unmatched, duplicate, inconsistent, and missing categories,
        as well as the distribution of matched categories.
    """
    coverage = 100 * (len(transactions) - len(unmatched)) / len(transactions) if transactions else 0
    print(f"Total transactions: {len(transactions)}")
    print(f"Matched transactions: {len(transactions) - len(unmatched)}")
    print(f"Unmatched transactions: {len(unmatched)}")
    print(f"Coverage: {coverage:.2f}%")
    if unmatched:
        print("\nSample unmatched transactions:")
        for tx in unmatched[:5]:
            print(tx)
    if duplicates:
        print("\nDuplicate keywords (appear in multiple categories):")
        for kw, cats in duplicates.items():
            print(f"  '{kw}': {list(cats)}")
    else:
        print("\nNo duplicate keywords found.")
    if inconsistent:
        print("\nInconsistent categorization (same transaction text matches multiple categories):")
        for tx, cats in list(inconsistent.items())[:5]:
            print(f"  '{tx}': {list(cats)}")
    else:
        print("\nNo inconsistent categorizations found.")
    if missing:
        print("\nMissing categories (not present in AI_Categorisation.json):")
        for cat in missing:
            print(f"  {cat}")
    else:
        print("\nAll desired categories are present.")
    print("\nCategory distribution (matched transactions):")
    cat_counts = Counter(matched_categories)
    for cat, count in cat_counts.most_common():
        print(f"  {cat}: {count}")

def main():
    """
    Main function to evaluate AI-based transaction categorization.

    This function performs the following steps:
    1. Loads transaction data and AI-generated categories from JSON files.
    2. Builds mappings between keywords and categories.
    3. Matches transactions to categories based on keywords.
    4. Identifies duplicate keywords across categories.
    5. Checks for inconsistencies in category assignments.
    6. Finds categories that are missing keywords.
    7. Prints a summary of the evaluation results.

    Returns:
        None
    """
    transactions, ai_categories = load_data("transactions.json", "AI_Categorisation.json")
    keyword_to_category, category_to_keywords, all_keywords = build_keyword_mappings(ai_categories)
    matched_categories, unmatched = match_transactions(transactions, keyword_to_category)
    duplicates = find_duplicate_keywords(keyword_to_category)
    inconsistent = check_category_consistency(transactions, keyword_to_category)
    missing = find_missing_categories(category_to_keywords)
    print_results(transactions, matched_categories, unmatched, duplicates, inconsistent, missing, category_to_keywords)

if __name__ == "__main__":
    main()