import pandas as pd
import sqlite3
import os
import glob
import logging
import hashlib
import numpy as np

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, "bank_statements.db")
log_path = os.path.join(script_dir, "db_update.log")

# Setup logging
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

# Unified column mapping for all banks
COLUMN_MAPPING = {
    # Bank_A
    "Buchung": "date",
    "Wertstellungsdatum": "value_date",
    "Auftraggeber/Empfänger": "sender_receiver",
    "Buchungstext": "booking_text",
    "Verwendungszweck": "purpose",
    "Saldo": "balance",
    "Währung": "currency",
    "Betrag": "amount",
    # Bank_B
    "Buchungstag": "date",
    "Wertstellungstag": "value_date",
    "GegenIBAN": "iban",
    "Name Gegenkonto": "sender_receiver",
    "Umsatz": "amount",
    # Bank_C
    "Auftragskonto": "account_number",
    "Valutadatum": "value_date",
    "Glaeubiger ID": "creditor_id",
    "Mandatsreferenz": "mandate_reference",
    "Kundenreferenz (End-to-End)": "customer_reference",
    "Sammlerreferenz": "collector_reference",
    "Lastschrift Ursprungsbetrag": "original_debit_amount",
    "Auslagenersatz Ruecklastschrift": "return_debit_expense",
    "Beguenstigter/Zahlungspflichtiger": "sender_receiver",
    "Kontonummer/IBAN": "iban",
    "BIC (SWIFT-Code)": "bic",
    "Waehrung": "currency",
    "Info": "info",
    # Bank_D / New Bank
    "Wert": "value_date",
    "Umsatzart": "booking_text",
    "Begünstigter / Auftraggeber": "sender_receiver",
    "IBAN / Kontonummer": "iban",
    "BIC": "bic",
    "Kundenreferenz": "customer_reference",
    "Mandatsreferenz": "mandate_reference",
    "Gläubiger ID": "creditor_id",
    "Fremde Gebühren": "info",
    "Abweichender Empfänger": "info",
    "Anzahl der Aufträge": "info",
    "Anzahl der Schecks": "info",
    "Soll": "debit",   # Soll = expenses
    "Haben": "credit", # Haben = income
}

# All possible unified columns (add more if needed)
ALL_COLUMNS = [
    "date", "value_date", "sender_receiver", "booking_text", "purpose", "debit", "credit", "balance",
    "currency", "amount", "iban", "bic", "info", "account_number", "creditor_id",
    "mandate_reference", "customer_reference", "collector_reference",
    "original_debit_amount", "return_debit_expense", "bank_name"
]

ALL_COLUMNS_WITH_HASH = ALL_COLUMNS + ["transaction_hash"]

def create_transactions_table(db_path, table_name="transactions"):
    """
    Create the transactions table with all possible columns and a unique constraint on transaction_hash.
    """
    conn = sqlite3.connect(db_path)
    columns_sql = ", ".join([f'"{col}" TEXT' for col in ALL_COLUMNS_WITH_HASH])
    create_sql = (
        f'CREATE TABLE IF NOT EXISTS {table_name} ('
        f'{columns_sql}, '
        'UNIQUE(transaction_hash)'
        ');'
    )
    conn.execute(create_sql)
    conn.commit()
    conn.close()

def find_header_row(file_path, sep=';', encoding='ISO-8859-1'):
    """
    Find the header row in a CSV file by matching known column names.
    Returns the row index of the header.
    """
    with open(file_path, 'r', encoding=encoding) as f:
        for i, line in enumerate(f):
            headers = line.strip().split(sep)
            match_count = sum(1 for h in headers if h.strip() in COLUMN_MAPPING)
            if match_count >= 3:
                logging.info(f"Header row found at line {i} in {file_path}")
                return i
    logging.error(f"Header row could not be found in the file: {file_path}")
    raise ValueError(f"Header row could not be found in the file: {file_path}")

def row_hash(row):
    """
    Generate a hash for a row based on all available data.
    """
    concat = '|'.join([str(row.get(col, '')).strip() for col in ALL_COLUMNS])
    return hashlib.sha256(concat.encode('utf-8')).hexdigest()

def load_csv_with_mapping(file_path, bank_name, sep=";"):
    """
    Load a CSV file, map its columns to unified names, clean and convert data types,
    and return a DataFrame ready for database insertion.
    Tries UTF-8 encoding first, then falls back to ISO-8859-1.
    """
    # Try UTF-8 first, then fallback to ISO-8859-1
    encodings = ['utf-8', 'ISO-8859-1']
    for encoding in encodings:
        try:
            header_row = find_header_row(file_path, sep=sep, encoding=encoding)
            df = pd.read_csv(file_path, sep=sep, header=header_row, encoding=encoding)
            break
        except UnicodeDecodeError:
            logging.warning(f"Failed to read {file_path} with encoding {encoding}, trying next encoding.")
        except Exception as e:
            logging.error(f"Error reading {file_path} with encoding {encoding}: {e}")
            raise
    else:
        raise ValueError(f"Could not read {file_path} with tried encodings.")

    df.columns = [col.strip() for col in df.columns]

    # Map columns to unified names
    unified_data = {}
    for col in df.columns:
        mapped_col = COLUMN_MAPPING.get(col)
        if mapped_col:
            unified_data[mapped_col] = df[col]
    unified_df = pd.DataFrame(unified_data)

    # Ensure all columns exist
    for col in ALL_COLUMNS:
        if col not in unified_df.columns:
            # Use 0.0 for numeric, "" for text
            if col in ["balance", "amount", "debit", "credit", "original_debit_amount", "return_debit_expense"]:
                unified_df[col] = 0.0
            else:
                unified_df[col] = ""

    unified_df["bank_name"] = bank_name

    # Convert date column to datetime
    if "date" in unified_df.columns:
        unified_df["date"] = pd.to_datetime(
            unified_df["date"], errors="coerce", dayfirst=True
        ).dt.strftime("%d.%m.%Y")

    # Clean text columns
    for col in ["sender_receiver", "booking_text", "purpose"]:
        if col in unified_df.columns:
            unified_df[col] = (
                unified_df[col]
                .astype(str)
                .str.strip()
                .str.replace(r"\s+", " ", regex=True)
            )

    # Robust numeric conversion for relevant columns
    for col in ["balance", "amount", "debit", "credit", "original_debit_amount", "return_debit_expense"]:
        if col in unified_df.columns:
            unified_df[col] = pd.to_numeric(
                unified_df[col]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False),
                errors="coerce"
            ).fillna(0.0)

    # Fill missing values for text columns
    for col in ALL_COLUMNS:
        if unified_df[col].dtype == object:
            unified_df[col] = unified_df[col].fillna("")

    # Generate transaction_hash
    unified_df["transaction_hash"] = unified_df.apply(row_hash, axis=1)

    logging.info(f"Loaded and mapped CSV: {file_path} (bank: {bank_name}), shape: {unified_df.shape}")
    return unified_df[ALL_COLUMNS_WITH_HASH]

def save_to_sqlite(df, db_path=db_path, table_name="transactions"):
    """
    Save the DataFrame into an SQLite database, ignoring duplicates.
    Logs the number of records saved and duplicates skipped.
    """
    conn = sqlite3.connect(db_path)
    try:
        before = pd.read_sql_query(f"SELECT COUNT(*) as cnt FROM {table_name}", conn)["cnt"][0]
        df.to_sql(table_name, conn, if_exists="append", index=False, method="multi")
        after = pd.read_sql_query(f"SELECT COUNT(*) as cnt FROM {table_name}", conn)["cnt"][0]
        inserted = after - before
        skipped = len(df) - inserted
        logging.info(f"Saved {inserted} new records to {db_path} in table '{table_name}'. Skipped {skipped} duplicates.")
    except sqlite3.IntegrityError as e:
        logging.info(f"Duplicate entry skipped: {e}")
    except Exception as e:
        logging.error(f"Error saving to database: {e}")
        raise
    finally:
        conn.close()

def detect_bank_name(filename):
    """
    Extract only the bank name from filename (without extension and year/suffix).
    E.g. 'Bank_A -2024.csv' or 'Bank_A_2024.csv' -> 'Bank_A'
    """
    base = os.path.splitext(os.path.basename(filename))[0]
    # Split at first space, dash, or underscore followed by a year or any non-letter
    import re
    match = re.match(r"([A-Za-z0-9]+(?:_[A-Za-z0-9]+)*)", base)
    if match:
        return match.group(1)
    return base

# ---------------------------- MAIN EXECUTION ----------------------------

# Automatically find all CSV files in the raw data folder
raw_data_dir = os.path.abspath(os.path.join(script_dir, '..', '02_raw_data'))
csv_files = glob.glob(os.path.join(raw_data_dir, '*.csv')) + glob.glob(os.path.join(raw_data_dir, '*.CSV'))

if not csv_files:
    logging.warning(f"No CSV files found in {raw_data_dir}")
else:
    logging.info(f"Found {len(csv_files)} CSV files in {raw_data_dir}")

create_transactions_table(db_path)

for path in csv_files:
    bank_name = detect_bank_name(path)
    try:
        df = load_csv_with_mapping(path, bank_name)
        save_to_sqlite(df, db_path=db_path)
        logging.info(f"Processed and saved: {os.path.basename(path)}")
    except Exception as e:
        logging.error(f"Error processing file {path}:\n{e}")