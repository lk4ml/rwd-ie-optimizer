"""
Database Catalog Tool

Provides complete schema information to agents.
MUST be called before any SQL generation.
"""

from typing import Dict, List, Any
import sqlite3
from src.utils.database import get_db_connection


def get_catalog() -> Dict[str, Any]:
    """
    Returns complete database schema for SQL generation.

    This tool provides agents with:
    - All tables and their columns
    - Data types
    - Row counts
    - Domain mappings (which tables contain diagnoses, drugs, etc.)
    - Relationships between tables

    Returns:
        Dictionary containing complete catalog information

    Example:
        catalog = get_catalog()
        print(catalog["tables"][0]["name"])  # "claims"
        print(catalog["domain_mappings"]["diagnosis"])  # {...}
    """

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_names = [row[0] for row in cursor.fetchall()]

        tables = []

        for table_name in table_names:
            # Get column information
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [
                {
                    "name": row[1],
                    "type": row[2],
                    "nullable": not row[3],
                    "primary_key": bool(row[5]),
                }
                for row in cursor.fetchall()
            ]

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]

            # Table description
            descriptions = {
                "claims": "Main claims table containing diagnoses, procedures, drugs, and services",
                "patients": "Patient demographics and enrollment periods",
                "ref_icd10": "ICD-10 diagnosis code reference",
                "ref_cpt": "CPT procedure code reference",
                "ref_ndc": "NDC drug code reference",
                "data_dictionary": "Data dictionary and field descriptions",
            }

            tables.append(
                {
                    "name": table_name,
                    "row_count": row_count,
                    "columns": columns,
                    "description": descriptions.get(table_name, ""),
                }
            )

    # Domain mappings - critical for agents to know where to find data
    domain_mappings = {
        "diagnosis": {
            "table": "claims",
            "code_columns": [
                "primary_diagnosis_code",
                "secondary_diagnosis_code",
                "tertiary_diagnosis_code",
            ],
            "desc_columns": [
                "primary_diagnosis_desc",
                "secondary_diagnosis_desc",
                "tertiary_diagnosis_desc",
            ],
            "date_column": "service_date",
            "reference_table": "ref_icd10",
            "reference_code_col": "icd_10_code",
            "reference_desc_col": "description",
        },
        "procedure": {
            "table": "claims",
            "code_columns": ["cpt_code", "hcpcs_code"],
            "desc_columns": ["cpt_description", "hcpcs_description"],
            "date_column": "service_date",
            "reference_table": "ref_cpt",
            "reference_code_col": "cpt_code",
            "reference_desc_col": "description",
        },
        "drug": {
            "table": "claims",
            "code_columns": ["ndc_code"],
            "desc_columns": ["drug_name"],
            "class_column": "drug_class",
            "date_column": "service_date",
            "supply_column": "days_supply",
            "quantity_column": "quantity_dispensed",
            "reference_table": "ref_ndc",
            "reference_code_col": "ndc_code",
            "reference_name_col": "drug_name",
            "reference_class_col": "drug_class",
        },
        "demographic": {
            "table": "patients",
            "columns": ["age", "gender", "race", "ethnicity", "state", "date_of_birth"],
        },
        "enrollment": {
            "table": "patients",
            "start_column": "enrollment_start_date",
            "end_column": "enrollment_end_date",
        },
    }

    # Relationships
    relationships = [
        {
            "from": "claims.patient_id",
            "to": "patients.patient_id",
            "type": "many-to-one",
            "description": "Claims belong to patients",
        }
    ]

    # Sample queries - examples for agents
    sample_queries = {
        "get_patients_with_diagnosis": """
            SELECT DISTINCT c.patient_id
            FROM claims c
            WHERE c.primary_diagnosis_code LIKE 'E11%'  -- Type 2 Diabetes
        """,
        "get_patients_on_drug": """
            SELECT DISTINCT c.patient_id
            FROM claims c
            WHERE c.ndc_code = '50090-2875-01'  -- Metformin
        """,
        "get_patients_by_age": """
            SELECT patient_id
            FROM patients
            WHERE age BETWEEN 18 AND 75
        """,
    }

    catalog = {
        "tables": tables,
        "domain_mappings": domain_mappings,
        "relationships": relationships,
        "sample_queries": sample_queries,
        "notes": [
            "All date columns are stored as TEXT in ISO format (YYYY-MM-DD)",
            "Use LIKE with % for ICD-10 wildcard matching (e.g., 'E11%' for all T2DM codes)",
            "Multiple diagnosis columns exist: primary, secondary, tertiary",
            "Claims table contains all clinical events (diagnoses, procedures, drugs)",
            "Always join claims to patients on patient_id",
        ],
    }

    return catalog


# For testing
if __name__ == "__main__":
    import json

    catalog = get_catalog()
    print(json.dumps(catalog, indent=2))
