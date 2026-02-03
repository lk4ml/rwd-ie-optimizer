"""
SQL Bundle Models

Output from the Coding Agent after SQL generation.
Contains generated queries, metadata, and documentation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class CTEInfo(BaseModel):
    """
    Documentation for a single Common Table Expression (CTE) in the generated SQL.
    """

    name: str = Field(..., description="CTE name (e.g., 'p_I01')")
    predicate_id: str = Field(..., description="Related predicate ID")
    description: str = Field(..., description="What this CTE computes")
    row_estimate: Optional[int] = Field(None, description="Estimated row count")
    logic_summary: Optional[str] = Field(None, description="Summary of SQL logic")


class FunnelStep(BaseModel):
    """
    One step in the patient funnel with count and percentage.
    """

    step_name: str = Field(..., description="Step description")
    n: int = Field(..., description="Patient count after this step")
    pct_of_base: float = Field(..., description="Percentage of base population")
    criteria_ids: List[str] = Field(
        default_factory=list, description="Criteria IDs applied at this step"
    )


class SQLBundle(BaseModel):
    """
    Complete SQL output from Coding Agent.

    Contains both the cohort query and funnel query, along with
    documentation and metadata.
    """

    study_id: str = Field(..., description="Study identifier")

    # Main SQL queries
    sql_cohort: str = Field(..., description="Main cohort selection query")
    sql_funnel_counts: str = Field(..., description="Funnel attrition query")

    # Query metadata
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Parameterized values (if any)"
    )

    cte_manifest: List[CTEInfo] = Field(
        default_factory=list, description="Documentation of each CTE"
    )

    # Assumptions and notes
    assumptions: List[str] = Field(
        default_factory=list, description="Assumptions made during SQL generation"
    )

    repair_notes: Optional[str] = Field(
        None, description="Notes from repair iteration (if this is a repair)"
    )

    # Execution metadata (filled after running)
    execution_result: Optional[Dict[str, Any]] = Field(
        None, description="Results from SQL execution"
    )

    funnel_steps: List[FunnelStep] = Field(
        default_factory=list, description="Funnel steps with counts"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "study_id": "trial_001",
                "sql_cohort": """
WITH
p_I01 AS (
    SELECT DISTINCT patient_id
    FROM patients
    WHERE age BETWEEN 18 AND 75
),
p_I02 AS (
    SELECT DISTINCT patient_id
    FROM claims
    WHERE primary_diagnosis_code LIKE 'E11%'
),
included AS (
    SELECT patient_id FROM p_I01
    INTERSECT
    SELECT patient_id FROM p_I02
),
cohort AS (
    SELECT i.patient_id, p.enrollment_start_date as index_date
    FROM included i
    JOIN patients p ON i.patient_id = p.patient_id
)
SELECT * FROM cohort;
                """,
                "sql_funnel_counts": """
SELECT 'Base Population' AS step, COUNT(DISTINCT patient_id) AS n FROM patients
UNION ALL
SELECT 'After I01 (Age 18-75)', COUNT(DISTINCT patient_id) FROM p_I01
UNION ALL
SELECT 'After I02 (T2DM)', COUNT(DISTINCT patient_id) FROM p_I01 INTERSECT SELECT patient_id FROM p_I02;
                """,
                "cte_manifest": [
                    {
                        "name": "p_I01",
                        "predicate_id": "I01",
                        "description": "Age between 18 and 75 years",
                    },
                    {
                        "name": "p_I02",
                        "predicate_id": "I02",
                        "description": "Type 2 Diabetes diagnosis",
                    },
                ],
                "assumptions": [
                    "Using enrollment_start_date as index_date",
                    "ICD-10 E11% wildcard captures all T2DM codes",
                ],
                "funnel_steps": [],
            }
        }


class ExecutionResult(BaseModel):
    """
    Result of SQL query execution.
    """

    ok: bool = Field(..., description="Whether execution succeeded")

    # Success case
    execution_summary: Optional[Dict[str, Any]] = Field(
        None, description="Summary: row count, timing, etc."
    )
    preview_rows: List[Dict[str, Any]] = Field(
        default_factory=list, description="Sample rows (if requested)"
    )

    # Error case
    error: Optional[str] = Field(None, description="Error message if failed")
    error_type: Optional[str] = Field(
        None, description="Error classification: syntax_error, schema_error, etc."
    )

    # Warnings
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")

    class Config:
        json_schema_extra = {
            "example": {
                "ok": True,
                "execution_summary": {"n": 234, "timing_ms": 145},
                "preview_rows": [
                    {"patient_id": "PAT123", "index_date": "2024-01-15"},
                    {"patient_id": "PAT456", "index_date": "2024-02-20"},
                ],
                "warnings": [],
            }
        }
