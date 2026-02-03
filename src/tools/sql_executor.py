"""
SQL Executor Tool

Executes SQL queries against the RWD database with safety checks.
"""

import sqlite3
import time
from typing import Dict, Optional, List, Any
from src.utils.database import get_db_connection


def run_sql(
    sql: str, params: Optional[Dict[str, Any]] = None, mode: str = "count"
) -> Dict[str, Any]:
    """
    Execute SQL with safety checks.

    This tool provides safe SQL execution with:
    - Protection against destructive operations
    - Timeout handling
    - Error classification
    - Multiple output modes

    Args:
        sql: Query to execute
        params: Parameter values for parameterized queries (not yet implemented)
        mode: Output mode:
            - "count": Return only row count (default, safest)
            - "preview": Return count + first 10 rows
            - "full": Return all rows (use with caution)

    Returns:
        Dictionary with:
        - ok: Boolean indicating success
        - execution_summary: Dict with row count and timing
        - preview_rows: List of row dicts (if mode != "count")
        - error: Error message if failed
        - error_type: Classification of error

    Example:
        >>> run_sql("SELECT * FROM patients WHERE age > 65", mode="count")
        {
            "ok": True,
            "execution_summary": {"n": 123, "timing_ms": 45.2},
            "preview_rows": []
        }
    """

    # Safety: Check for destructive operations
    destructive_keywords = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER"]
    sql_upper = sql.upper()

    for keyword in destructive_keywords:
        if keyword in sql_upper:
            return {
                "ok": False,
                "error": f"Destructive operation '{keyword}' not allowed",
                "error_type": "safety_violation",
            }

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            start_time = time.time()

            # Execute query
            cursor.execute(sql)
            results = cursor.fetchall()

            elapsed_ms = (time.time() - start_time) * 1000

            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Prepare response based on mode
            if mode == "count":
                return {
                    "ok": True,
                    "execution_summary": {"n": len(results), "timing_ms": round(elapsed_ms, 2)},
                    "preview_rows": [],
                    "warnings": [],
                }

            elif mode == "preview":
                # Convert first 10 rows to dicts
                preview = []
                for row in results[:10]:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        row_dict[col] = row[i]
                    preview.append(row_dict)

                return {
                    "ok": True,
                    "execution_summary": {"n": len(results), "timing_ms": round(elapsed_ms, 2)},
                    "preview_rows": preview,
                    "warnings": (
                        [f"Showing 10 of {len(results)} rows"] if len(results) > 10 else []
                    ),
                }

            elif mode == "full":
                # Convert all rows to dicts
                full_results = []
                for row in results:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        row_dict[col] = row[i]
                    full_results.append(row_dict)

                warnings = []
                if len(results) > 1000:
                    warnings.append(f"Large result set: {len(results)} rows returned")

                return {
                    "ok": True,
                    "execution_summary": {"n": len(results), "timing_ms": round(elapsed_ms, 2)},
                    "preview_rows": full_results,
                    "warnings": warnings,
                }

            else:
                return {
                    "ok": False,
                    "error": f"Invalid mode '{mode}'. Use 'count', 'preview', or 'full'",
                    "error_type": "invalid_mode",
                }

    except sqlite3.OperationalError as e:
        error_msg = str(e)

        # Classify error type
        if "syntax error" in error_msg.lower():
            error_type = "syntax_error"
        elif "no such table" in error_msg.lower() or "no such column" in error_msg.lower():
            error_type = "schema_error"
        else:
            error_type = "operational_error"

        return {"ok": False, "error": error_msg, "error_type": error_type}

    except sqlite3.Error as e:
        return {"ok": False, "error": str(e), "error_type": "database_error"}

    except Exception as e:
        return {"ok": False, "error": str(e), "error_type": "unknown_error"}


def explain_sql(sql: str) -> Dict[str, Any]:
    """
    Get query execution plan for optimization.

    Args:
        sql: Query to explain

    Returns:
        Dictionary with query plan information
    """

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # SQLite EXPLAIN QUERY PLAN
            cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
            plan = cursor.fetchall()

            plan_steps = []
            for row in plan:
                plan_steps.append({"detail": row[3] if len(row) > 3 else str(row)})

            return {"ok": True, "query_plan": plan_steps}

    except sqlite3.Error as e:
        return {"ok": False, "error": str(e)}


def validate_sql_syntax(sql: str) -> Dict[str, bool]:
    """
    Check if SQL has valid syntax without executing.

    Args:
        sql: SQL query to validate

    Returns:
        Dictionary with valid flag and error message if invalid
    """

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Try to prepare the statement
            cursor.execute(f"EXPLAIN {sql}")

            return {"valid": True, "message": "SQL syntax is valid"}

    except sqlite3.Error as e:
        return {"valid": False, "message": str(e)}


# For testing
if __name__ == "__main__":
    import json

    # Test query
    print("Test 1: Count patients")
    result = run_sql("SELECT * FROM patients", mode="count")
    print(json.dumps(result, indent=2))

    print("\n\nTest 2: Preview patients")
    result = run_sql("SELECT * FROM patients", mode="preview")
    print(json.dumps(result, indent=2))

    print("\n\nTest 3: Syntax error")
    result = run_sql("SELECT * FORM patients", mode="count")
    print(json.dumps(result, indent=2))

    print("\n\nTest 4: Schema error")
    result = run_sql("SELECT * FROM nonexistent_table", mode="count")
    print(json.dumps(result, indent=2))
