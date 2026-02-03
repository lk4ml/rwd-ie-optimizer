"""
Create SQLite database from Excel synthetic RWD data.

Converts all 6 sheets from the Excel file into SQLite tables with proper
indexing for query performance.
"""

import pandas as pd
import sqlite3
from pathlib import Path
import sys

def create_rwd_database():
    """Convert Excel sheets to SQLite tables"""

    # Paths
    project_root = Path(__file__).parent.parent
    excel_file = project_root / "synthetic_rwd_claims_data (1).xlsx"
    db_file = project_root / "data" / "rwd_claims.db"

    if not excel_file.exists():
        print(f"❌ Error: Excel file not found at {excel_file}")
        sys.exit(1)

    print("=" * 70)
    print("Creating RWD SQLite Database")
    print("=" * 70)
    print(f"\nSource: {excel_file.name}")
    print(f"Target: {db_file}\n")

    # Remove existing database
    if db_file.exists():
        db_file.unlink()
        print("🗑️  Removed existing database\n")

    # Create database connection
    conn = sqlite3.connect(db_file)

    # Sheet to table mapping
    sheets = {
        'Claims': 'claims',
        'Patient_Demographics': 'patients',
        'Ref_ICD10_Codes': 'ref_icd10',
        'Ref_CPT_Codes': 'ref_cpt',
        'Ref_NDC_Codes': 'ref_ndc',
        'Data_Dictionary': 'data_dictionary'
    }

    print("Loading sheets and creating tables:\n")

    for sheet_name, table_name in sheets.items():
        print(f"  📄 Processing: {sheet_name} → {table_name}...", end=" ")

        # Read Excel sheet
        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        # Clean column names (lowercase, replace spaces/hyphens with underscores)
        df.columns = [
            col.lower()
            .replace(' ', '_')
            .replace('-', '_')
            .replace('(', '')
            .replace(')', '')
            for col in df.columns
        ]

        # Convert date columns to proper format
        date_columns = [col for col in df.columns if 'date' in col]
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

        # Write to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)

        print(f"✅ {len(df)} rows")

    print("\n" + "=" * 70)
    print("Creating Indexes for Query Performance")
    print("=" * 70 + "\n")

    # Create indexes for performance
    indexes = [
        ("idx_claims_patient", "claims", "patient_id"),
        ("idx_claims_service_date", "claims", "service_date"),
        ("idx_claims_primary_dx", "claims", "primary_diagnosis_code"),
        ("idx_claims_secondary_dx", "claims", "secondary_diagnosis_code"),
        ("idx_claims_ndc", "claims", "ndc_code"),
        ("idx_claims_cpt", "claims", "cpt_code"),
        ("idx_patients_id", "patients", "patient_id"),
        ("idx_patients_age", "patients", "age"),
        ("idx_patients_enrollment_start", "patients", "enrollment_start_date"),
    ]

    cursor = conn.cursor()

    for idx_name, table, column in indexes:
        try:
            cursor.execute(f"CREATE INDEX {idx_name} ON {table}({column})")
            print(f"  ✅ Created index: {idx_name} on {table}({column})")
        except sqlite3.OperationalError as e:
            print(f"  ⚠️  Warning: {idx_name} - {e}")

    conn.commit()

    print("\n" + "=" * 70)
    print("Database Summary")
    print("=" * 70 + "\n")

    # Print summary
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    for (table_name,) in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  📊 {table_name}: {count:,} rows")

    conn.close()

    print("\n" + "=" * 70)
    print("✅ Database created successfully!")
    print("=" * 70)
    print(f"\nLocation: {db_file}")
    print(f"Size: {db_file.stat().st_size / 1024:.2f} KB\n")

if __name__ == "__main__":
    create_rwd_database()
