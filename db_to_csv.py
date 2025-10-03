import sqlite3
import csv
import os
from pathlib import Path

def export_table_to_csv(db_path, table_name, output_csv):
    """Export a SQLite table to CSV file"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all data from table
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()

    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]

    # Write to CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)  # Write header
        writer.writerows(rows)    # Write data

    conn.close()
    print(f"Exported {len(rows)} rows from {table_name} to {output_csv}")

def convert_db_to_csv(db_path, output_dir='csv_output'):
    """Convert all tables in a SQLite database to CSV files"""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    db_name = Path(db_path).stem

    # Export each table
    for table in tables:
        output_csv = os.path.join(output_dir, f"{db_name}_{table}.csv")
        export_table_to_csv(db_path, table, output_csv)

if __name__ == "__main__":
    # Convert main database
    convert_db_to_csv('database/perda.db')

    # Convert all worker databases
    for i in range(10):
        db_path = f'database/perda_worker_{i}.db'
        if os.path.exists(db_path):
            convert_db_to_csv(db_path)

    print("\nAll databases converted to CSV successfully!")
