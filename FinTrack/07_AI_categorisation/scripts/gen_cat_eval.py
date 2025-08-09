"""
gen_cat_eval.py

This script evaluates the results of AI-based transaction categorization.
It loads transactions and AI-generated category mappings, matches transactions to categories using keywords,
identifies uncategorized and inconsistently categorized transactions, and generates summary statistics and visualizations.

Why this script is needed:
    The output from the AI categorization process may contain duplicate, missing, or inconsistent keyword assignments,
    making it difficult to assess the quality and completeness of the categorization. This script provides essential
    evaluation and diagnostics by:
        - Matching transactions to categories using the AI-generated keywords.
        - Identifying transactions that remain uncategorized or are assigned to multiple conflicting categories.
        - Detecting duplicate keywords and missing categories.
        - Generating summary statistics and confidence score visualizations.
        - Exporting uncategorized and inconsistent transactions for further review or iterative improvement.

By using this script, you can systematically assess and improve the quality of your AI-driven categorization pipeline,
ensuring that downstream analysis is based on reliable and well-structured data.

Typical usage:
    python gen_cat_eval.py transactions.json AI_Categorisation_cleaned.json uncategorized_transactions.json inconsistent_categorizations.json
"""

import json
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import os
import sys

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
        ai_categories (list): A list of dictionaries, where each dictionary represents a category entry with the following structure:

    Returns:
        tuple: A tuple containing four elements:
            - keyword_to_category (dict): Maps each keyword (str) to a set of categories (set of str) it belongs to.
            - category_to_keywords (defaultdict): Maps each category (str) to a set of keywords (set of str) associated with it.
            - all_keywords (list): A list of all keywords (str) found in the input.
            - keyword_confidence (dict): Maps each keyword (str) to its confidence value (float or int), if provided.
    """

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
    """
    Matches transactions to categories based on provided keywords.

    Args:
        transactions (list of dict): A list of transaction dictionaries. Each transaction should contain
        the keys 'sender_receiver', 'booking_text', and 'purpose'.
        keyword_to_category (dict): A dictionary mapping keywords (str) to a list or set of categories.
    
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
        keyword_to_category (dict): A dictionary where keys are keywords and values are lists or sets of categories associated with each keyword.
    
    Returns:
        dict: A dictionary containing only the keywords that are associated with more than one category, mapping each such keyword to its list or set of categories.
    """

    return {kw: cats for kw, cats in keyword_to_category.items() if len(cats) > 1}

def check_category_consistency(transactions, keyword_to_category):
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
        set: A set of category names (str) that are present in the predefined list of desired categories but missing from the input dictionary.
    """

    desired_categories = {
        "haushold", "electricity", "maintenance", "rent", "salary", "bank loan",
        "taxes and fees", "insurance", "leisure", "creditcard", "medicine", "sport",
        "clothing", "atm", "other", "transportation"
    }
    present_categories = set(category_to_keywords.keys())
    return desired_categories - present_categories

def print_confidence_statistics(keyword_confidence):
    """
    Prints statistical information and generates a histogram for keyword confidence scores.
    
    Args:
        keyword_confidence (dict): A dictionary where values are confidence scores (int or float) associated with keywords.
    
    Behavior:
        - Calculates and prints the minimum, maximum, and average confidence scores.
        - Plots and saves a histogram of the confidence scores as 'confidence_histogram.png' in the outputs directory.
        - If no valid confidence values are found, prints a corresponding message.
    
    Notes:
        - The function expects matplotlib.pyplot as plt and os to be imported.
        - The outputs directory is assumed to be located one level above the script's directory.
    """

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
    """
    Prints a summary of transaction categorization results.
    
    Args:
        transactions (list): The list of all transactions processed.
        unmatched (list): The list of transactions that could not be matched to a category.
        inconsistent (list): The list of transactions with inconsistent categorizations.
    
    Prints:
        - Total number of transactions.
        - Number of matched transactions.
        - Number of unmatched transactions.
        - Number of inconsistent categorizations.
        - Coverage percentage of matched transactions.
    """

    coverage = 100 * (len(transactions) - len(unmatched)) / len(transactions) if transactions else 0
    print("\nSummary:")
    print(f"Total transactions: {len(transactions)}")
    print(f"Matched transactions: {len(transactions) - len(unmatched)}")
    print(f"Unmatched transactions: {len(unmatched)}")
    print(f"Inconsistent categorizations: {len(inconsistent)}")
    print(f"Coverage: {coverage:.2f}%")

def save_unmatched_transactions(unmatched, output_path=None):
    """
    Saves a list of unmatched transactions to a JSON file.
    
    Args:
        unmatched (list): A list of unmatched transaction records to be saved.
        output_path (str, optional): The file path where the JSON file will be saved.
        If None, saves to 'uncategorized_transactions.json' in the current script's directory.
    
    Returns:
        None
    
    Raises:
        OSError: If there is an error writing to the specified file path.
    """

    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "uncategorized_transactions.json")
        output_path = os.path.normpath(output_path)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unmatched, f, indent=2, ensure_ascii=False)

def save_inconsistent_categorizations(inconsistent, transactions, output_path="inconsistent_categorizations.json"):
    """
    Saves inconsistent categorizations of transactions to a JSON file.
    This function takes a dictionary of inconsistent categorizations, a list of transaction dictionaries,
    and writes the inconsistent entries to a JSON file. Each entry in the output contains the full transaction
    information (if available) and the list of inconsistent categories. If the full transaction cannot be found,
    the normalized transaction text is included instead.
    
    Args:
        inconsistent (dict): A mapping from normalized transaction text to a set or list of inconsistent categories.
        transactions (list): A list of transaction dictionaries, each containing transaction details.
        output_path (str, optional): The file path to save the output JSON. Defaults to "inconsistent_categorizations.json".
    
    Returns:
        None
    """

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
    """
    Main entry point for evaluating AI-based transaction categorization.
    This function determines file paths for input and output data, either from command-line arguments or default locations.
    It loads transaction and category data, builds keyword mappings, matches transactions to categories, and identifies
    unmatched, duplicate, inconsistent, and missing categorizations. Results are saved to output files, and summary
    statistics are printed to the console.
    
    Command-line arguments (optional):
        1. transactions_path: Path to the transactions JSON file.
        2. categories_path: Path to the AI-categorized categories JSON file.
        3. uncategorized_path: Path to save unmatched transactions.
        4. inconsistent_path: Path to save inconsistent categorizations.
    
    If arguments are not provided, default paths in the outputs directory are used.
    """

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