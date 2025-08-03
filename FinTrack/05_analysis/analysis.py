import logging
import sqlite3
import pandas as pd
import re
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
import seaborn as sns
import matplotlib.colors as mcolors
from datetime import datetime
import os
import json
import sys

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(ANALYSIS_DIR, "_build")
os.makedirs(BUILD_DIR, exist_ok=True)

AI_CATS_PATH = os.path.join(ANALYSIS_DIR, "..", "07_AI_categorisation", "outputs", "AI_Categorisation_cleaned.json")
if os.path.exists(AI_CATS_PATH):
    with open(AI_CATS_PATH, "r", encoding="utf-8") as f:
        ai_categories = json.load(f)
    ai_categories = [entry for entry in ai_categories if entry.get("Category") and entry.get("Keywords")]
    categories = {entry["Category"]: entry["Keywords"] for entry in ai_categories}
else:
    categories = {}

def main():

    # --- Logging configuration ---
    logging.basicConfig(
        filename='analysis.log',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s'
    )
    logging.info("Starting Analysis.py")

    # Use the same absolute path in both scripts
    DB_PATH = r"C:\public_projects\portfolio\FinTrack\03_data_cleaning\bank_statements.db"
    conn = sqlite3.connect(DB_PATH)

    # -------- Load data from the new database --------
    try:
        conn = sqlite3.connect(DB_PATH)
        logging.info(f"Connected to database: {DB_PATH}")
        query = """
        SELECT 
            date, 
            sender_receiver,
            booking_text, 
            purpose, 
            amount, 
            bank_name
        FROM transactions
        """
        df = pd.read_sql_query(query, conn)
        logging.info(f"Loaded {len(df)} transactions from database.")
    except Exception as e:
        logging.error(f"Error loading data from database: {e}")
        raise
    finally:
        conn.close()
        logging.info("Database connection closed.")

    # Convert date and amount columns
    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y', errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df['cost'] = df['amount'].apply(lambda x: x if x < 0 else 0)
    df['income'] = df['amount'].apply(lambda x: x if x > 0 else 0)
    logging.info("Converted date and amount columns.")

    # Add year, month, day columns
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['day'] = df['date'].dt.day
    
    # --- Fast categorization using vectorized string matching ---
    def fast_categorize(df, categories):
        text_col = (
            df['sender_receiver'].fillna('') + ' ' +
            df['booking_text'].fillna('') + ' ' +
            df['purpose'].fillna('')
        ).str.lower()
        result = pd.Series('Other', index=df.index)
        for cat, keywords in categories.items():
            for kw_obj in keywords:
                kw = kw_obj['keyword'] if isinstance(kw_obj, dict) and 'keyword' in kw_obj else str(kw_obj)
                mask = text_col.str.contains(re.escape(kw.lower()), regex=True)
                result[mask] = cat
        return result

    df['category'] = fast_categorize(df, categories)
    logging.info("Categorization completed using fast vectorized method.")

# -------- Export uncategorized transactions for review --------
    # Ensure the outputs directory exists
    uncategorized_dir = os.path.join(os.path.dirname(__file__), "..", "07_AI_categorisation", "outputs")
    os.makedirs(uncategorized_dir, exist_ok=True)
    uncategorized_path = os.path.join(uncategorized_dir, "uncategorized_transactions.json")
    other_df = df[df['category'] == 'Other']
    if not other_df.empty:
        uncategorized_path = os.path.join(ANALYSIS_DIR, "..", "07_AI_categorisation", "outputs", "uncategorized_transactions.json")
        other_df.to_json(uncategorized_path, orient="records", force_ascii=False)
        logging.info(f"Exported {len(other_df)} uncategorized transactions for review.")
    else:
        logging.info("No uncategorized transactions found.")

    # -------- Aggregations --------
    # Yearly summary
    yearly_result = df.groupby('year').agg(
        Total_Income=('income', 'sum'),
        Total_Expenditure=('cost', 'sum'),
        Net_Balance=('amount', 'sum')
    ).reset_index().round(2)

    # Add a total row
    total_row = pd.DataFrame({
        'year': ['Total'],
        'Total_Income': [yearly_result['Total_Income'].sum()],
        'Total_Expenditure': [yearly_result['Total_Expenditure'].sum()],
        'Net_Balance': [yearly_result['Net_Balance'].sum()]
    })
    yearly_result = pd.concat([yearly_result, total_row], ignore_index=True)

    # Monthly summary
    result = df.groupby(['year', 'month']).agg(
        Total_Income=('income', 'sum'),
        Total_Expenditure=('cost', 'sum'),
        Net_Balance=('amount', 'sum')
    ).reset_index().round(2)

    # Add a total row
    total_row = pd.DataFrame({
        'year': ['Total'],
        'month': [''],
        'Total_Income': [result['Total_Income'].sum()],
        'Total_Expenditure': [result['Total_Expenditure'].sum()],
        'Net_Balance': [result['Net_Balance'].sum()]
    })
    result = pd.concat([result, total_row], ignore_index=True)

    # Category summary
    category_sums = df.groupby('category').agg(
        Total_Income=('income', 'sum'),
        Total_Expenditure=('cost', 'sum'),
        Net_Balance=('amount', 'sum')
    ).reset_index().round(2)

    # -------- Unique sender_receiver and purpose pairs for 'Other' --------
    unique_other = df[df['category'] == 'Other'][['sender_receiver', 'purpose']].drop_duplicates()

    # -------- Yearly and Monthly Delta Tables --------
    yearly_expenses = df.groupby(['category', 'year'])['cost'].sum().unstack().fillna(0).abs()
    yearly_delta = yearly_expenses.diff(axis=1) / yearly_expenses.shift(axis=1) * 100
    yearly_delta = yearly_delta.fillna(0).map(lambda x: f"{x:.1f}")

    monthly_expenses = df.groupby(['category', 'month'])['cost'].sum().unstack().fillna(0).abs()
    monthly_delta = monthly_expenses.diff(axis=1) / monthly_expenses.shift(axis=1) * 100
    monthly_delta = monthly_delta.fillna(0).map(lambda x: f"{x:.1f}")

    # -------- Plots --------
    def plot_cumulative_area():
        try:
            df_filtered = df[df['cost'] != 0].copy()
            df_filtered['year'] = df_filtered['date'].dt.year
            df_filtered['month'] = df_filtered['date'].dt.month
            df_grouped = df_filtered.groupby(['year', 'month', 'category'])['cost'].sum().reset_index()
            df_grouped = df_grouped.sort_values(by=['year', 'month', 'category'])
            df_pivot = df_grouped.pivot_table(index=['year', 'month'], columns='category', values='cost', aggfunc='sum').fillna(0)
            df_cumulative = df_pivot.cumsum(axis=0)
            categories_list = df_cumulative.columns
            color_palette = list(mcolors.TABLEAU_COLORS.values()) * (len(categories_list) // 10 + 1)
            color_palette = color_palette[:len(categories_list)]
            fig, ax = plt.subplots(figsize=(8,6), dpi=150, constrained_layout=True)
            df_cumulative.plot.area(stacked=True, color=color_palette, ax=ax)
            plt.xlabel('Year-Month')
            plt.ylabel('Cumulative Spending (€)')
            plt.title('Stacked Cumulative Spending by Category')
            plt.legend(title='Categories', loc='upper left')
            plt.grid(True)
            plt.savefig(os.path.join(BUILD_DIR, "cumulative_spending_plot.png"), dpi=150, pad_inches=0.1)
            plt.close()
            logging.info("Cumulative area plot generated.")
        except Exception as e:
            logging.error(f"Error generating cumulative area plot: {e}")

    plot_cumulative_area()

    def plot_cumulative_area_by_keyword(category):
        try:
            plt.close('all')
            keywords = categories.get(category, [])
            df_category = df[df['category'] == category].copy()
            def find_keyword(row):
                text = normalize_text(f"{row['sender_receiver']} {row['booking_text']} {row['purpose']}")
                for kw_obj in keywords:
                    kw = kw_obj['keyword'] if isinstance(kw_obj, dict) and 'keyword' in kw_obj else str(kw_obj)
                    kw_norm = normalize_text(kw)
                    if kw_norm in text:
                        return kw
                return 'Other'
            df_category['Keyword'] = df_category.apply(find_keyword, axis=1)
            # Only keep expense rows
            df_category = df_category[df_category['cost'] != 0]
            if df_category.empty:
                return  # Nothing to plot
            df_grouped = df_category.groupby(['date', 'Keyword'])['cost'].sum().reset_index()
            df_pivot = df_grouped.pivot(index='date', columns='Keyword', values='cost').fillna(0)
            # Drop columns that are all zeros (no data)
            df_pivot = df_pivot.loc[:, (df_pivot != 0).any(axis=0)]
            if df_pivot.empty:
                return  # Nothing to plot
            df_cumulative = df_pivot.cumsum()
            fig, ax = plt.subplots(figsize=(12, 6))
            df_cumulative.plot.area(alpha=0.6, colormap='tab10', ax=ax)
            plt.xlabel("Date")
            plt.ylabel("Cumulative Spending (€)")
            plt.title(f"Cumulative Spending by Keyword in {category}")
            plt.legend(title="Keyword", bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.grid()
            plt.tight_layout()
            # For category plots:
            filename = os.path.join(BUILD_DIR, f"cumulative_spending_plot_{category}.png")
            fig.savefig(filename, dpi=150, bbox_inches="tight", pad_inches=0.1)
            plt.close(fig)
            logging.info(f"Cumulative area plot by keyword generated for category: {category}")
        except Exception as e:
            logging.error(f"Error generating cumulative area plot for category {category}: {e}")

    for category in categories:
        plot_cumulative_area_by_keyword(category)

    # -------- PDF Report --------

    class PDF(FPDF):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.table_counter = 1
            self.figure_counter = 1

        def header(self):
            self.set_font("Arial", "B", 16)
            self.cell(200, 10, "FinTrack Report", ln=True, align="C")
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 10)
            self.cell(0, 10, f'Page {self.page_no()}', align="C")

        def chapter_title(self, title):
            self.set_font("Arial", "B", 12)
            self.cell(0, 10, title, ln=True, align="L")

        def ensure_space(self, needed_height=40):
            # Add a new page if not enough space for table/figure
            if self.get_y() + needed_height > self.page_break_trigger:
                self.add_page()

        def add_table(self, df, col_names, table_title, summary_text, col_widths=None, font_size=10):
            # Estimate needed height (very rough, adjust as needed)
            needed_height = 20 + len(df) * 10
            self.ensure_space(needed_height)
            self.set_font("Arial", "", 12)
            self.multi_cell(0, 7, summary_text)
            self.ln(5)
            self.set_font("Arial", "B", 10)
            table_title_text = f"Table {self.table_counter}: {table_title}"
            self.chapter_title(table_title_text)
            if not col_widths:
                col_widths = [max(40, 200 // len(col_names))] * len(col_names)
                total_width = sum(col_widths)
                if total_width > 190:
                    scale_factor = 190 / total_width
                    col_widths = [w * scale_factor for w in col_widths]
            self.set_font("Arial", "B", font_size)
            for i, col_name in enumerate(col_names):
                self.cell(col_widths[i], 10, str(col_name), border=1)
            self.ln()
            self.set_font("Arial", "", font_size)
            # --- Fix: For 2-column tables, use simple cell printing ---
            if len(col_names) == 2 and table_title.startswith("Unique Transactions"):
                for _, row in df.iterrows():
                    for i, col_name in enumerate(col_names):
                        value = row[col_name] if col_name in row else "N/A"
                        value = str(value)
                        self.cell(col_widths[i], 10, value, border=1)
                    self.ln()
            else:
                for _, row in df.iterrows():
                    for i, col_name in enumerate(col_names):
                        value = row[col_name] if col_name in row else "N/A"
                        if isinstance(value, float) and value.is_integer():
                            value = int(value)
                        elif isinstance(value, float):
                            value = f"{value:.2f}"
                        self.cell(col_widths[i], 10, str(value), border=1)
                    self.ln()
            self.table_counter += 1
            self.ln(5)

        def add_figure(self, image_path):
            self.ensure_space(80)
            figure_title = f"Figure {self.figure_counter}: "
            self.chapter_title(figure_title + "Financial Overview by Category")
            self.image(image_path, x=10, y=None, w=180)
            self.ln(10)
            self.figure_counter += 1

        def add_multiple_plots(self, plots):
            plot_index = 2
            for plot in plots:
                if not os.path.isfile(plot):
                    logging.warning(f"Skipping missing plot: {plot}")
                    continue
                self.ensure_space(80)
                plot_title = f"Figure {plot_index+1}: "
                self.chapter_title(plot_title + "Financial Overview by Keyword")
                self.image(plot, x=10, y=None, w=180)
                self.ln(10)
                plot_index += 1

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=15, top=10, right=15)
    pdf.add_page()

    start_date = df['date'].min().strftime("%d.%m.%Y")
    end_date = df['date'].max().strftime("%d.%m.%Y")
    report_period = f"{start_date} - {end_date}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Database Used: {DB_PATH}", ln=True)
    pdf.cell(0, 10, f"Report Period: {report_period}", ln=True)
    pdf.cell(0, 10, f"Report Created On: {timestamp}", ln=True)
    pdf.ln(10)

    intro_text = (
        "This financial report provides a comprehensive overview of the income, expenditures, and net balance "
        "over the specified report period. It includes detailed insights into monthly financial results and categorized expenses."
    )
    pdf.multi_cell(0, 7, intro_text)
    pdf.ln(5)

    pdf.add_table(yearly_result, list(yearly_result.columns), "Yearly Financial Data (EUR)", "Table 1 presents total income, total expenditures, and net balance for the full report period.")
    pdf.add_table(result, list(result.columns), "Monthly Financial Results (EUR)", "Table 2: Income, expenditures, and net balance by month.")
    pdf.add_table(category_sums, list(category_sums.columns), "Category-wise Expense Summary (EUR)", "Table 3: Total amount by category.")

    # Add cumulative spending plot
    pdf.add_page()
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 7, "This stacked area chart visualizes the cumulative spending by category over time.")
    pdf.ln(5)
    pdf.add_figure(os.path.join(BUILD_DIR, "cumulative_spending_plot.png"))

    # Add cumulative spending plots for every category
    pdf.add_page()
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0,7, "These plots show how spending evolves over time for each category, based on predefined keywords in transaction descriptions.")
    pdf.ln(5)
    pdf.add_multiple_plots([os.path.join(BUILD_DIR, f"cumulative_spending_plot_{cat}.png") for cat in categories])

    # --- Monthly costs per category for every month in 1999 ---
    df_1999 = df[df['year'] == 1999]
    monthly_category_costs = df_1999.groupby(['category', 'month'])['amount'].sum().unstack(fill_value=0).round(2)
    monthly_category_costs['Total'] = monthly_category_costs.sum(axis=1)
    monthly_category_costs.loc['Total'] = monthly_category_costs.sum(axis=0)

    # --- Add to PDF ---
    col_names_5 = list(monthly_category_costs.reset_index().columns)
    if len(col_names_5) > 2:
        col_widths_5 = [35] + [max(20, 135 // (len(col_names_5)-2))]*(len(col_names_5)-2) + [25]
    else:
        col_widths_5 = [80 for _ in col_names_5]
    pdf.add_table(
        monthly_category_costs.reset_index(),
        col_names_5,
        "Monthly Costs per Category for 1999 (EUR)",
        "This table shows the sum of costs (amount) for each category and month in 1999. The last column is the total for the year.",
        col_widths=col_widths_5,
        font_size=8
    )

    # --- Add Monthly Details tables for every category with data in 1999 ---

    # Add a general explanation before all monthly details tables
    monthly_details_intro = (
        "The following tables show, for each category and keyword, the sum of costs (amount) for each month in 1999. "
        "The last column is the total for the year. Use these tables to analyze your spending patterns and identify which keywords contribute most to each category."
    )
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 7, monthly_details_intro)
    pdf.ln(5)

    for cat in sorted(df_1999['category'].unique()):
        cat_df = df_1999[df_1999['category'] == cat].copy()
        if cat_df.empty:
            continue
        keywords = categories.get(cat, [])
        def find_keyword(row):
            text = f"{row['sender_receiver']} {row['booking_text']} {row['purpose']}".lower()
            for kw_obj in keywords:
                kw = kw_obj['keyword'] if isinstance(kw_obj, dict) and 'keyword' in kw_obj else str(kw_obj)
                if kw.lower() in text.lower():
                    return kw
            return 'Other'
        cat_df['Keyword'] = cat_df.apply(find_keyword, axis=1)
        detail = cat_df.groupby(['Keyword', 'month'])['amount'].sum().unstack(fill_value=0).round(2)
        detail['Total'] = detail.sum(axis=1)
        detail.loc['Total'] = detail.sum(axis=0)
        col_names = list(detail.reset_index().columns)
        if len(col_names) > 2:
            col_widths = [40] + [max(20, 120 // (len(col_names)-2))]*(len(col_names)-2) + [25]
        else:
            col_widths = [80 for _ in col_names]
        
        pdf.add_table(
            detail.reset_index(),
            col_names,
            f"Monthly Details for {cat} (1999)",
            "",  # No per-table description
            col_widths=col_widths,
            font_size=8
        )

    col_names_6 = list(unique_other.columns)
    col_widths_6 = [40, 120]
    pdf.add_table(
        unique_other,
        col_names_6,
        "Unique Transactions in 'Other' Category (1999)",
        "This table lists all unique combinations of sender/receiver and purpose for transactions categorized as 'Other' in 1999. Ideally, this table should be empty. If there are entries here, it means some transactions could not be automatically categorized. Please review these transactions and consider updating your categorization rules if needed.",
        col_widths=col_widths_6,
        font_size=9
    )

    output_filename = os.path.join(BUILD_DIR, "FinTrack_Report.pdf")
    pdf.output(output_filename)

    logging.info(f"PDF report generated successfully: {output_filename}")
    print(f"PDF report generated successfully: {output_filename}")
    logging.info("Analysis completed successfully.")

def normalize_text(text):
    # Lowercase and remove all non-alphanumeric characters except spaces
    return re.sub(r'[^a-z0-9 ]', '', text.lower())

if __name__ == "__main__":
    main()