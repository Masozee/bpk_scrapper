import sqlite3
import csv
import os
from pathlib import Path

def export_table_to_csv(db_path, table_name, output_csv, chunk_size=10000):
    """Export a SQLite table to CSV file with chunked reading"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]

    # Get total count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_rows = cursor.fetchone()[0]
    print(f"Exporting {total_rows} rows from {table_name}...")

    # Write to CSV with chunked reading
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)  # Write header

        # Read and write in chunks
        cursor.execute(f"SELECT * FROM {table_name}")
        rows_written = 0
        while True:
            rows = cursor.fetchmany(chunk_size)
            if not rows:
                break
            writer.writerows(rows)
            rows_written += len(rows)
            print(f"  Progress: {rows_written}/{total_rows} rows", end='\r')

    conn.close()
    print(f"\nExported {rows_written} rows to {output_csv}")

def convert_db_to_csv(db_path, output_dir='csv_output'):
    """Convert all tables in a SQLite database to CSV files"""
    os.makedirs(output_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all table names (excluding SQLite internal tables)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    db_name = Path(db_path).stem
    print(f"\nProcessing: {db_name}")
    print(f"Tables found: {', '.join(tables)}")

    # Export each table
    for table in tables:
        output_csv = os.path.join(output_dir, f"{db_name}_{table}.csv")
        export_table_to_csv(db_path, table, output_csv)

if __name__ == "__main__":
    # Convert main database
    if os.path.exists('database/perda.db'):
        convert_db_to_csv('database/perda.db')

    # Convert all worker databases
    for i in range(10):
        db_path = f'database/perda_worker_{i}.db'
        if os.path.exists(db_path):
            convert_db_to_csv(db_path)

    print("\n" + "="*50)
    print("All databases converted to CSV successfully!")
    print(f"Output directory: csv_output/")
