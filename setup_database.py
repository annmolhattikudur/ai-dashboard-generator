"""
setup_database.py
Loads all CSV files from data/raw/ into SQLite database at database/fmcg_warehouse.db
"""

import sqlite3
import pandas as pd
from pathlib import Path
import re
import sys

from config import DATA_RAW_DIR, DATABASE_PATH


def clean_column_name(col: str) -> str:
    """Lowercase and replace spaces/special chars with underscores."""
    col = col.lower().strip()
    col = re.sub(r'[\s\-\.]+', '_', col)
    col = re.sub(r'[^\w]', '', col)
    col = re.sub(r'_+', '_', col)
    return col.strip('_')


def deduplicate_columns(columns: list) -> list:
    """Ensure column names are unique by appending _1, _2, etc."""
    seen = {}
    result = []
    for col in columns:
        if col in seen:
            seen[col] += 1
            result.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            result.append(col)
    return result


def read_csv_robust(path: Path) -> pd.DataFrame:
    """Try multiple encodings to read a CSV file."""
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv(path, encoding=encoding, low_memory=False)
            return df
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not read {path} with any supported encoding")


def is_id_or_key_column(col_name: str) -> bool:
    """Heuristic: column looks like an ID/key if it ends with _id, _key, _code, _prefix."""
    keywords = ['_id', '_key', '_code', '_prefix', '_num', '_number']
    return any(col_name.endswith(kw) for kw in keywords)


def load_csv_to_sqlite(csv_path: Path, conn: sqlite3.Connection) -> dict:
    """Load a single CSV into SQLite and return a summary dict."""
    table_name = csv_path.stem  # filename without extension

    df = read_csv_robust(csv_path)

    # Clean column names
    df.columns = [clean_column_name(c) for c in df.columns]
    df.columns = deduplicate_columns(list(df.columns))

    # Load into SQLite (replace if exists)
    df.to_sql(table_name, conn, if_exists='replace', index=False)

    # Create indexes on ID/key columns
    cursor = conn.cursor()
    indexed_cols = []
    for col in df.columns:
        if is_id_or_key_column(col):
            idx_name = f"idx_{table_name}_{col}"
            try:
                cursor.execute(
                    f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table_name}" ("{col}")'
                )
                indexed_cols.append(col)
            except sqlite3.OperationalError:
                pass  # Skip if index already exists or column issue
    conn.commit()

    return {
        'table_name': table_name,
        'row_count': len(df),
        'column_count': len(df.columns),
        'columns': list(df.columns),
        'indexed_columns': indexed_cols,
    }


def main():
    print("=" * 60)
    print("AI Dashboard Generator — Database Setup")
    print("=" * 60)

    # Ensure database directory exists
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Find all CSV files
    csv_files = sorted(DATA_RAW_DIR.glob("*.csv"))
    if not csv_files:
        print(f"ERROR: No CSV files found in {DATA_RAW_DIR}")
        sys.exit(1)

    print(f"\nFound {len(csv_files)} CSV file(s) in {DATA_RAW_DIR}\n")

    # Connect to SQLite
    conn = sqlite3.connect(DATABASE_PATH)

    summaries = []
    for csv_path in csv_files:
        print(f"  Loading: {csv_path.name}...")
        try:
            summary = load_csv_to_sqlite(csv_path, conn)
            summaries.append(summary)
            print(f"    ✓ Table: {summary['table_name']}")
            print(f"      Rows: {summary['row_count']:,}  |  Columns: {summary['column_count']}")
            if summary['indexed_columns']:
                print(f"      Indexed: {', '.join(summary['indexed_columns'])}")
        except Exception as e:
            print(f"    ✗ FAILED: {e}")

    conn.close()

    print("\n" + "=" * 60)
    print("DATABASE SUMMARY")
    print("=" * 60)
    print(f"{'Table Name':<45} {'Rows':>10} {'Cols':>6}")
    print("-" * 63)
    for s in summaries:
        print(f"{s['table_name']:<45} {s['row_count']:>10,} {s['column_count']:>6}")
    print("-" * 63)
    total_rows = sum(s['row_count'] for s in summaries)
    print(f"{'TOTAL':<45} {total_rows:>10,}")
    print(f"\nDatabase saved to: {DATABASE_PATH}")
    print("Setup complete!")


if __name__ == "__main__":
    main()
