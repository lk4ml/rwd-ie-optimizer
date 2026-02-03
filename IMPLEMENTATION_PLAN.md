# RWD IE Optimizer - Implementation Plan
## Using OpenAI Agent SDK (Swarm) with SQLite Backend

**Date:** December 17, 2025
**Database:** SQLite with synthetic claims data (6 tables, 500 patients, 3,500 claims)
**AI Models:** GPT-4o, GPT-4-turbo
**Framework:** OpenAI Agent SDK (Swarm)

---

## Executive Summary

This plan outlines building a multi-agent system that converts clinical trial I/E criteria into executable SQL queries over your synthetic RWD claims database. The system uses 6 specialized agents orchestrated via OpenAI's Swarm framework.

**Timeline:** 7-10 days for MVP, 14-18 days for full system
**Architecture:** Multi-agent with shared state (Criteria DSL)
**Output:** Interactive REPL that generates SQL and patient funnels

---

## Phase 1: Database & Foundation Setup (Days 1-2)

### 1.1 SQLite Database Creation

**Script: `scripts/create_database.py`**

```python
import pandas as pd
import sqlite3
from pathlib import Path

def create_rwd_database():
    """Convert Excel sheets to SQLite tables"""

    excel_file = "synthetic_rwd_claims_data (1).xlsx"
    db_file = "data/rwd_claims.db"

    # Create database
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

    for sheet_name, table_name in sheets.items():
        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        # Clean column names (lowercase, replace spaces with underscores)
        df.columns = [col.lower().replace(' ', '_').replace('-', '_')
                      for col in df.columns]

        # Convert dates
        date_columns = [col for col in df.columns if 'date' in col]
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

        # Write to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)

        print(f"✓ Created table: {table_name} ({len(df)} rows)")

    # Create indexes for performance
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX idx_claims_patient ON claims(patient_id)")
    cursor.execute("CREATE INDEX idx_claims_service_date ON claims(service_date)")
    cursor.execute("CREATE INDEX idx_claims_primary_dx ON claims(primary_diagnosis_code)")
    cursor.execute("CREATE INDEX idx_patients_id ON patients(patient_id)")

    conn.commit()
    conn.close()

    print("\n✓ Database created: data/rwd_claims.db")
```

**Database Schema Mapping:**

| Excel Sheet | SQLite Table | Primary Use |
|-------------|--------------|-------------|
| Claims | `claims` | Main fact table (diagnoses, procedures, drugs) |
| Patient_Demographics | `patients` | Demographics + enrollment |
| Ref_ICD10_Codes | `ref_icd10` | Diagnosis code lookup |
| Ref_CPT_Codes | `ref_cpt` | Procedure code lookup |
| Ref_NDC_Codes | `ref_ndc` | Drug code lookup |
| Data_Dictionary | `data_dictionary` | Metadata reference |

---

### 1.2 Project Structure

```
rwd-ie-optimizer/
├── .env                            # API keys
├── .gitignore
├── README.md
├── IMPLEMENTATION_PLAN.md          # This file
├── pyproject.toml                  # Dependencies
│
├── data/
│   ├── rwd_claims.db              # SQLite database (generated)
│   └── synthetic_rwd_claims_data (1).xlsx
│
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   │
│   ├── models/                    # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── criteria_dsl.py        # Core DSL models
│   │   ├── resolved_concepts.py   # Concept resolution
│   │   └── sql_bundle.py          # SQL output
│   │
│   ├── agents/                    # OpenAI Swarm agents
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # Main controller
│   │   ├── ie_interpreter.py      # Text → DSL
│   │   ├── deep_research.py       # Concept resolver
│   │   ├── coding_agent.py        # SQL generator
│   │   ├── sql_runner.py          # Query executor
│   │   └── receiver.py            # Summarizer
│   │
│   ├── tools/                     # Agent functions
│   │   ├── __init__.py
│   │   ├── catalog.py             # get_catalog()
│   │   ├── concept_search.py      # search_concepts()
│   │   ├── unit_resolver.py       # resolve_units()
│   │   ├── sql_executor.py        # run_sql()
│   │   └── artifact_store.py      # save_artifact()
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py            # Environment config
│   │   └── prompts/               # Agent system prompts
│   │       ├── orchestrator.txt
│   │       ├── ie_interpreter.txt
│   │       ├── deep_research.txt
│   │       ├── coding_agent.txt
│   │       ├── sql_runner.txt
│   │       └── receiver.txt
│   │
│   └── utils/
│       ├── __init__.py
│       ├── display.py             # REPL formatting
│       ├── database.py            # DB connection
│       └── validators.py          # DSL validation
│
├── scripts/
│   ├── create_database.py         # Excel → SQLite
│   └── test_database.py           # DB validation
│
├── tests/
│   ├── __init__.py
│   ├── test_agents/
│   ├── test_tools/
│   └── fixtures/
│       └── sample_criteria.txt    # Test I/E criteria
│
└── examples/
    ├── sample_session.md
    └── sample_output.json

```

---

### 1.3 Dependencies (`pyproject.toml`)

```toml
[project]
name = "rwd-ie-optimizer"
version = "0.1.0"
description = "Convert clinical trial I/E criteria to SQL over RWD"
requires-python = ">=3.11"

dependencies = [
    "openai>=1.55.0",              # OpenAI SDK with Swarm
    "pydantic>=2.9.0",             # Data validation
    "pandas>=2.2.0",               # Data manipulation
    "openpyxl>=3.1.0",             # Excel reading
    "sqlalchemy>=2.0.0",           # SQL toolkit
    "rich>=13.9.0",                # Terminal formatting
    "typer>=0.13.0",               # CLI framework
    "python-dotenv>=1.0.0",        # Environment variables
    "pytest>=8.3.0",               # Testing
]

[project.scripts]
rwd-ie = "src.main:app"
```

---

## Phase 2: Core Data Models (Day 3)

### 2.1 Criteria DSL (`src/models/criteria_dsl.py`)

**Based on claude.md specification:**

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import date

class TemporalWindow(BaseModel):
    reference: str = Field(..., description="index_date, enrollment_start, etc.")
    before_days: Optional[int] = None
    after_days: Optional[int] = None
    during: Optional[str] = None

class ValueConstraint(BaseModel):
    operator: Literal[">=", "<=", ">", "<", "=", "between"]
    value: float | tuple[float, float]
    unit: Optional[str] = None

class CountConstraint(BaseModel):
    operator: Literal[">=", "<=", "=", "between"]
    count: int | tuple[int, int]
    within_days: Optional[int] = None
    proportion: Optional[float] = None

class ConceptResolution(BaseModel):
    resolved: bool
    concept_ids: List[str]
    code_system: Literal["ICD10CM", "ICD9CM", "CPT", "HCPCS", "NDC", "RxNorm", "LOINC"]
    matching_logic: Literal["exact", "wildcard", "hierarchy", "ingredient"]
    confidence: Literal["high", "medium", "low"]

class Predicate(BaseModel):
    id: str
    description: str
    domain: Literal["demographic", "diagnosis", "procedure", "drug", "lab", "enrollment", "observation"]
    concept: str
    concept_resolution: Optional[ConceptResolution] = None
    temporal: Optional[TemporalWindow] = None
    value_constraint: Optional[ValueConstraint] = None
    count_constraint: Optional[CountConstraint] = None
    verifiability: Literal["rwd", "partial_rwd", "non_rwd"]
    needs_definition: bool = False

class Gap(BaseModel):
    predicate_id: str
    issue: str
    proposed_resolution: Optional[str] = None
    requires_user_input: bool

class CriteriaDSL(BaseModel):
    study_id: str
    version: str
    anchors: dict
    inclusion: List[Predicate]
    exclusion: List[Predicate]
    assumptions_and_gaps: List[Gap] = []
    non_rwd_gates: List[str] = []
```

### 2.2 SQL Bundle Model

```python
class CTEInfo(BaseModel):
    name: str
    predicate_id: str
    description: str
    row_estimate: Optional[int] = None

class SQLBundle(BaseModel):
    sql_cohort: str
    sql_funnel_counts: str
    parameters: dict = {}
    cte_manifest: List[CTEInfo]
    assumptions: List[str]
    repair_notes: Optional[str] = None
```

---

## Phase 3: Tool Implementation (Days 4-5)

### 3.1 Database Catalog Tool (`src/tools/catalog.py`)

```python
import sqlite3
import json
from typing import Dict, List

def get_catalog() -> Dict:
    """
    Returns complete database schema for SQL generation.

    Returns:
        {
            "tables": [
                {
                    "name": "claims",
                    "row_count": 3500,
                    "columns": [
                        {"name": "claim_id", "type": "TEXT", "nullable": False},
                        {"name": "patient_id", "type": "TEXT", "nullable": False},
                        ...
                    ],
                    "description": "Main claims table with diagnoses, procedures, drugs"
                },
                ...
            ],
            "relationships": [
                {"from": "claims.patient_id", "to": "patients.patient_id", "type": "many-to-one"}
            ],
            "domain_mappings": {
                "diagnosis": {
                    "table": "claims",
                    "code_columns": ["primary_diagnosis_code", "secondary_diagnosis_code", "tertiary_diagnosis_code"],
                    "desc_columns": ["primary_diagnosis_desc", "secondary_diagnosis_desc", "tertiary_diagnosis_desc"],
                    "date_column": "service_date"
                },
                "procedure": {
                    "table": "claims",
                    "code_columns": ["cpt_code", "hcpcs_code"],
                    "desc_columns": ["cpt_description", "hcpcs_description"],
                    "date_column": "service_date"
                },
                "drug": {
                    "table": "claims",
                    "code_columns": ["ndc_code"],
                    "desc_columns": ["drug_name"],
                    "date_column": "service_date",
                    "supply_column": "days_supply"
                },
                "demographic": {
                    "table": "patients",
                    "columns": ["age", "gender", "race", "ethnicity", "state"]
                },
                "enrollment": {
                    "table": "patients",
                    "start_column": "enrollment_start_date",
                    "end_column": "enrollment_end_date"
                }
            }
        }
    """
    conn = sqlite3.connect("data/rwd_claims.db")
    cursor = conn.cursor()

    # Introspect schema
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = []

    for (table_name,) in cursor.fetchall():
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [
            {"name": row[1], "type": row[2], "nullable": not row[3]}
            for row in cursor.fetchall()
        ]

        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]

        tables.append({
            "name": table_name,
            "row_count": row_count,
            "columns": columns
        })

    catalog = {
        "tables": tables,
        "relationships": [
            {"from": "claims.patient_id", "to": "patients.patient_id", "type": "many-to-one"}
        ],
        "domain_mappings": {
            # ... as defined above
        }
    }

    conn.close()
    return catalog
```

### 3.2 Concept Search Tool (`src/tools/concept_search.py`)

```python
def search_concepts(term: str, code_system: str = None) -> List[Dict]:
    """
    Search for clinical concepts in reference tables.

    Args:
        term: Search term (e.g., "diabetes", "metformin")
        code_system: Filter by ICD10CM, CPT, NDC

    Returns:
        List of matches with codes and descriptions
    """
    conn = sqlite3.connect("data/rwd_claims.db")
    results = []

    if code_system in [None, "ICD10CM"]:
        # Search ICD-10 codes
        query = """
            SELECT icd_10_code as code, description, 'ICD10CM' as system
            FROM ref_icd10
            WHERE LOWER(description) LIKE ?
        """
        cursor = conn.execute(query, (f"%{term.lower()}%",))
        results.extend([
            {"code": row[0], "description": row[1], "code_system": row[2]}
            for row in cursor.fetchall()
        ])

    if code_system in [None, "NDC"]:
        # Search drug codes
        query = """
            SELECT ndc_code as code, drug_name, drug_class, 'NDC' as system
            FROM ref_ndc
            WHERE LOWER(drug_name) LIKE ? OR LOWER(drug_class) LIKE ?
        """
        cursor = conn.execute(query, (f"%{term.lower()}%", f"%{term.lower()}%"))
        results.extend([
            {"code": row[0], "description": f"{row[1]} ({row[2]})", "code_system": row[3]}
            for row in cursor.fetchall()
        ])

    # Similar for CPT codes...

    conn.close()
    return results
```

### 3.3 SQL Executor Tool (`src/tools/sql_executor.py`)

```python
def run_sql(sql: str, params: dict = None, mode: str = "count") -> Dict:
    """
    Execute SQL with safety checks.

    Args:
        sql: Query to execute
        params: Parameter values (unused for now)
        mode: "count" (default), "preview", "full"

    Returns:
        ExecutionResult with row count, timing, preview rows
    """
    import time

    conn = sqlite3.connect("data/rwd_claims.db")
    cursor = conn.cursor()

    # Safety: Check for destructive operations
    if any(keyword in sql.upper() for keyword in ["DROP", "DELETE", "TRUNCATE", "UPDATE"]):
        return {"ok": False, "error": "Destructive operations not allowed"}

    try:
        start = time.time()
        cursor.execute(sql)
        results = cursor.fetchall()
        elapsed_ms = (time.time() - start) * 1000

        if mode == "count":
            # Return only count
            return {
                "ok": True,
                "execution_summary": {"n": len(results), "timing_ms": elapsed_ms},
                "preview_rows": []
            }

        elif mode == "preview":
            # Return limited rows
            columns = [desc[0] for desc in cursor.description]
            rows = [dict(zip(columns, row)) for row in results[:10]]
            return {
                "ok": True,
                "execution_summary": {"n": len(results), "timing_ms": elapsed_ms},
                "preview_rows": rows
            }

    except sqlite3.Error as e:
        return {
            "ok": False,
            "error": str(e),
            "error_type": "syntax_error" if "syntax" in str(e).lower() else "schema_error"
        }

    finally:
        conn.close()
```

---

## Phase 4: Agent Development with OpenAI Swarm (Days 6-10)

### 4.1 OpenAI Swarm Setup

**Install:** `pip install git+https://github.com/openai/swarm.git`

**Basic Pattern:**

```python
from swarm import Swarm, Agent
import os

client = Swarm()

# Define agents
orchestrator = Agent(
    name="Orchestrator",
    model="gpt-4o",
    instructions="""You are the orchestrator for the RWD IE Optimizer.
    Your role is to coordinate other agents and manage the workflow...""",
    functions=[transfer_to_ie_interpreter, transfer_to_deep_research, ...]
)

ie_interpreter = Agent(
    name="IE_Interpreter",
    model="gpt-4o",
    instructions="""Parse raw I/E criteria text into structured Criteria DSL JSON...""",
    functions=[]  # No tools needed for parsing
)

deep_research = Agent(
    name="Deep_Research",
    model="gpt-4-turbo",
    instructions="""Resolve medical concepts using available tools...""",
    functions=[get_catalog, search_concepts, resolve_units]
)

# Run workflow
response = client.run(
    agent=orchestrator,
    messages=[{"role": "user", "content": user_ie_text}],
    context_variables={"criteria_dsl": {}}
)
```

### 4.2 Agent Implementations

**4.2.1 Orchestrator Agent** (`src/agents/orchestrator.py`)

```python
from swarm import Agent
from typing import Dict

def transfer_to_ie_interpreter():
    """Handoff to IE Interpreter for parsing"""
    return ie_interpreter_agent

def transfer_to_deep_research(criteria_dsl: dict):
    """Handoff to Deep Research with DSL"""
    return deep_research_agent

def transfer_to_coding_agent(criteria_dsl: dict, resolved_concepts: dict):
    """Handoff to Coding Agent with DSL + concepts"""
    return coding_agent

def transfer_to_receiver():
    """Handoff to Receiver for final summary"""
    return receiver_agent

orchestrator_instructions = """
You are the Orchestrator for the RWD IE Optimizer system.

Your responsibilities:
1. Parse user's I/E criteria text
2. Coordinate agent invocations in sequence
3. Maintain Criteria DSL as source of truth
4. Present results in REPL format
5. Handle iteration loops until user approval

Workflow:
1. Transfer to IE_Interpreter to parse raw text → Criteria DSL
2. Transfer to Deep_Research to resolve concepts → ResolvedConcepts
3. Transfer to Coding_Agent to generate SQL → SQLBundle
4. Execute SQL and check results
5. If error: repair or suggest edits
6. Present to user for approval
7. If approved: transfer to Receiver for summary
8. If not approved: go back to appropriate step

Stop conditions: User says "finalize", "good", "approve", "ship it"
"""

orchestrator_agent = Agent(
    name="Orchestrator",
    model="gpt-4o",
    instructions=orchestrator_instructions,
    functions=[
        transfer_to_ie_interpreter,
        transfer_to_deep_research,
        transfer_to_coding_agent,
        transfer_to_receiver
    ]
)
```

**4.2.2 IE Interpreter Agent** (`src/agents/ie_interpreter.py`)

```python
ie_interpreter_instructions = """
You are the IE Interpreter Agent. Your job is to parse raw inclusion/exclusion
criteria text into structured Criteria DSL JSON.

Rules:
1. Extract ALL predicates with thresholds, units, timing windows
2. Classify domain: demographic, diagnosis, procedure, drug, lab, enrollment
3. Classify verifiability: rwd, partial_rwd, non_rwd
4. Flag ambiguous items with needs_definition: true
5. Do NOT map to codes (Deep Research Agent does that)
6. Do NOT reference database tables

Example Input:
"Inclusion:
- Adults 18-75 years
- Type 2 diabetes diagnosed in past 12 months
- HbA1c ≥7.0% and ≤10.0%

Exclusion:
- eGFR <30 mL/min"

Example Output:
{
  "study_id": "trial_001",
  "version": "1.0",
  "anchors": {
    "index_event": "enrollment_date"
  },
  "inclusion": [
    {
      "id": "I01",
      "description": "Adults 18-75 years",
      "domain": "demographic",
      "concept": "age",
      "value_constraint": {"operator": "between", "value": [18, 75], "unit": "years"},
      "verifiability": "rwd",
      "needs_definition": false
    },
    {
      "id": "I02",
      "description": "Type 2 diabetes diagnosed in past 12 months",
      "domain": "diagnosis",
      "concept": "Type 2 Diabetes",
      "temporal": {"reference": "index_date", "before_days": 365, "after_days": 0},
      "verifiability": "rwd",
      "needs_definition": false
    }
  ],
  "exclusion": [...],
  "assumptions_and_gaps": [],
  "non_rwd_gates": []
}
"""

ie_interpreter_agent = Agent(
    name="IE_Interpreter",
    model="gpt-4o",
    instructions=ie_interpreter_instructions,
    functions=[]
)
```

**4.2.3 Deep Research Agent** (`src/agents/deep_research.py`)

```python
from src.tools.catalog import get_catalog
from src.tools.concept_search import search_concepts
from src.tools.unit_resolver import resolve_units

deep_research_instructions = """
You are the Deep Research Agent. Your job is to resolve medical concepts
into dataset-specific codes.

Rules:
1. ALWAYS call get_catalog() first
2. Use search_concepts() for each unresolved concept
3. Provide alternatives with confidence scores
4. Do NOT write SQL
5. For ambiguous items, propose 2-3 implementable definitions

Example:
Input: Predicate with concept="Type 2 Diabetes", domain="diagnosis"

Your process:
1. Call get_catalog() to see available diagnosis tables
2. Call search_concepts("type 2 diabetes", "ICD10CM")
3. Return concept resolution:
{
  "resolved": true,
  "concept_ids": ["E11.9", "E11.0", "E11.1", "E11.2", ...],
  "code_system": "ICD10CM",
  "matching_logic": "wildcard",
  "confidence": "high"
}
"""

deep_research_agent = Agent(
    name="Deep_Research",
    model="gpt-4-turbo",
    instructions=deep_research_instructions,
    functions=[get_catalog, search_concepts, resolve_units]
)
```

**4.2.4 Coding Agent** (`src/agents/coding_agent.py`)

```python
from src.tools.catalog import get_catalog

coding_agent_instructions = """
You are the Coding Agent. Generate SQL from Criteria DSL + Resolved Concepts.

SQL Structure (MANDATORY):
```sql
WITH
-- One CTE per predicate
p_I01 AS (
    SELECT DISTINCT patient_id
    FROM patients
    WHERE age BETWEEN 18 AND 75
),

p_I02 AS (
    SELECT DISTINCT c.patient_id
    FROM claims c
    WHERE c.primary_diagnosis_code LIKE 'E11%'
      AND c.service_date >= DATE(p.enrollment_start_date, '-365 days')
),

-- Combine inclusion (INTERSECT)
included AS (
    SELECT patient_id FROM p_I01
    INTERSECT
    SELECT patient_id FROM p_I02
),

-- Combine exclusion (UNION)
excluded AS (
    SELECT patient_id FROM p_E01
),

-- Final cohort
cohort AS (
    SELECT i.patient_id, p.enrollment_start_date as index_date
    FROM included i
    JOIN patients p ON i.patient_id = p.patient_id
    WHERE i.patient_id NOT IN (SELECT patient_id FROM excluded)
)

SELECT * FROM cohort;
```

Also generate sql_funnel_counts:
```sql
SELECT 'Base Population' AS step, COUNT(DISTINCT patient_id) AS n FROM patients
UNION ALL
SELECT 'After I01 (Age 18-75)', COUNT(DISTINCT patient_id) FROM p_I01
UNION ALL
SELECT 'After I02 (T2DM)', COUNT(DISTINCT patient_id) FROM p_I01 INTERSECT SELECT patient_id FROM p_I02
...
```

CRITICAL RULES:
1. NEVER assume tables not in get_catalog()
2. NEVER hard-code clinical concepts
3. Handle temporal windows with DATE functions
4. Use LIKE for ICD-10 wildcards (E11%)
5. On error: diagnose, repair, explain in repair_notes
"""

coding_agent = Agent(
    name="Coding_Agent",
    model="gpt-4o",
    instructions=coding_agent_instructions,
    functions=[get_catalog]
)
```

**4.2.5 SQL Runner Agent** (`src/agents/sql_runner.py`)

```python
from src.tools.sql_executor import run_sql

sql_runner_instructions = """
You are the SQL Runner/Validator Agent. Execute SQL and validate results.

Process:
1. Call run_sql(sql, mode="count") first
2. Check for errors
3. If error: diagnose type (syntax, schema, logic) and return to Coding Agent
4. If success: check for suspicious patterns
5. Call run_sql(sql, mode="preview") for funnel query

Error Handling:
- syntax_error → Return to Coding Agent with error message
- schema_error → Return to Coding Agent with catalog info
- empty_cohort (n=0) → Flag to Orchestrator
- suspicious_drop (>95% loss) → Flag for review

Output format:
{
  "ok": true,
  "execution_summary": {"n": 245, "timing_ms": 123},
  "funnel_steps": [
    {"step": "Base Population", "n": 500, "pct_of_base": 100},
    {"step": "After I01 (Age)", "n": 380, "pct_of_base": 76},
    ...
  ]
}
"""

sql_runner_agent = Agent(
    name="SQL_Runner",
    model="gpt-4o",
    instructions=sql_runner_instructions,
    functions=[run_sql]
)
```

**4.2.6 Receiver Agent** (`src/agents/receiver.py`)

```python
receiver_instructions = """
You are the Receiver Agent. Generate final summary and validation checklist.

Create:
1. Executive Summary
   - Final cohort size
   - Key inclusion/exclusion drivers
   - Major attrition points

2. Funnel Narrative
   - Where patients drop off
   - Unexpected patterns
   - Data quality notes

3. Validation Checklist
   - What to manually verify
   - Assumptions made
   - Non-RWD criteria to check separately

Example Output:
## Executive Summary
Final cohort: 234 patients identified from 500 in database

Key drivers:
- Age 18-75: 380 patients (76% of base)
- Type 2 Diabetes: 245 patients (49% of base)
- HbA1c in range: 234 patients (47% of base)

## Funnel Narrative
Major attrition at HbA1c step (11 patients excluded, 4.5% drop).
This suggests ~95% of T2DM patients in database have acceptable HbA1c control.

## Data Quality Notes
- HbA1c values found in claims data (assumed from lab tests)
- Central lab confirmation not available in this dataset

## Validation Checklist
☐ Manually verify T2DM diagnosis codes are complete
☐ Check if HbA1c extraction logic is clinically sound
☐ Confirm enrollment periods align with study timeline
"""

receiver_agent = Agent(
    name="Receiver",
    model="gpt-4o",
    instructions=receiver_instructions,
    functions=[]
)
```

---

## Phase 5: REPL Interface (Days 11-12)

### 5.1 Main CLI (`src/main.py`)

```python
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from swarm import Swarm
from src.agents.orchestrator import orchestrator_agent
import json

app = typer.Typer()
console = Console()
client = Swarm()

def display_repl_output(state: dict):
    """Format and display REPL output"""

    console.print("\n" + "=" * 70)
    console.print("[bold cyan]CURRENT CRITERIA (JSON)[/bold cyan]")
    console.print("=" * 70)
    console.print_json(json.dumps(state.get("criteria_dsl", {}), indent=2))

    console.print("\n" + "=" * 70)
    console.print("[bold cyan]CURRENT SQL (COHORT)[/bold cyan]")
    console.print("=" * 70)
    sql = state.get("sql_cohort", "pending build")
    if sql != "pending build":
        console.print(Syntax(sql, "sql", theme="monokai"))
    else:
        console.print("[yellow]Pending SQL generation...[/yellow]")

    console.print("\n" + "=" * 70)
    console.print("[bold cyan]FUNNEL STEPS (COUNTS)[/bold cyan]")
    console.print("=" * 70)

    funnel = state.get("funnel_steps", [])
    if funnel:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Step", style="dim")
        table.add_column("Count", justify="right")
        table.add_column("% of Base", justify="right")

        for step in funnel:
            table.add_row(
                step["step"],
                str(step["n"]),
                f"{step['pct_of_base']:.1f}%"
            )
        console.print(table)
    else:
        console.print("[yellow]Pending execution...[/yellow]")

    # Warnings
    warnings = state.get("warnings", [])
    if warnings:
        console.print("\n" + "=" * 70)
        console.print("[bold red]WARNINGS / UNVERIFIABLE GATES[/bold red]")
        console.print("=" * 70)
        for warning in warnings:
            console.print(f"⚠️  {warning}")

    console.print("\n" + "=" * 70)
    console.print("[bold green]NEXT ACTION[/bold green]")
    console.print("=" * 70)
    console.print(state.get("next_action", "Awaiting user input..."))
    console.print()

@app.command()
def run():
    """Start RWD IE Optimizer REPL"""

    console.print(Panel.fit(
        "[bold cyan]RWD IE Optimizer[/bold cyan]\n"
        "Convert clinical trial I/E criteria to SQL over real-world data",
        border_style="cyan"
    ))

    console.print("\nPaste your I/E criteria below (press Ctrl+D when done):\n")

    # Read multi-line input
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    user_ie_text = "\n".join(lines)

    if not user_ie_text.strip():
        console.print("[red]No input provided. Exiting.[/red]")
        return

    # Run orchestrator
    context = {
        "criteria_dsl": {},
        "resolved_concepts": {},
        "sql_bundle": {},
        "funnel_steps": [],
        "warnings": [],
        "iteration": 0
    }

    messages = [{"role": "user", "content": user_ie_text}]

    while True:
        response = client.run(
            agent=orchestrator_agent,
            messages=messages,
            context_variables=context
        )

        # Update context from response
        context.update(response.context_variables)

        # Display REPL output
        display_repl_output(context)

        # Check for completion
        if context.get("finalized", False):
            console.print("[bold green]✓ Workflow complete![/bold green]")
            break

        # Get user feedback
        feedback = console.input("\n[bold]Your feedback (or 'finalize' to complete):[/bold] ")

        if feedback.lower() in ["finalize", "good", "approve", "ship it"]:
            context["finalized"] = True
            # Transfer to Receiver for final summary
            continue

        # Add user feedback to messages
        messages.append({"role": "user", "content": feedback})

if __name__ == "__main__":
    app()
```

---

## Phase 6: Testing & Validation (Days 13-14)

### 6.1 Sample Test Criteria (`tests/fixtures/sample_criteria.txt`)

```
STUDY: Chronic Kidney Disease Progression Trial

INCLUSION CRITERIA:
1. Adults aged 18-75 years at enrollment
2. Diagnosis of Type 2 Diabetes Mellitus in the past 5 years
3. Chronic Kidney Disease Stage 3 or 4 (eGFR 15-59 mL/min/1.73m²)
4. Currently prescribed Metformin for at least 90 days

EXCLUSION CRITERIA:
1. History of heart failure or acute myocardial infarction
2. eGFR <15 mL/min/1.73m² (Stage 5 CKD)
3. Active malignancy (cancer diagnosis in past 2 years)
4. Pregnancy
```

### 6.2 Integration Test (`tests/test_integration.py`)

```python
import pytest
from swarm import Swarm
from src.agents.orchestrator import orchestrator_agent

def test_full_workflow():
    """Test complete workflow from I/E text to SQL"""

    client = Swarm()

    ie_text = """
    Inclusion:
    - Adults 18-75 years
    - Type 2 Diabetes

    Exclusion:
    - Heart failure history
    """

    context = {"criteria_dsl": {}}
    response = client.run(
        agent=orchestrator_agent,
        messages=[{"role": "user", "content": ie_text}],
        context_variables=context
    )

    # Verify DSL generated
    assert "criteria_dsl" in response.context_variables
    dsl = response.context_variables["criteria_dsl"]
    assert len(dsl["inclusion"]) == 2
    assert len(dsl["exclusion"]) == 1

    # Verify SQL generated
    assert "sql_bundle" in response.context_variables
    sql = response.context_variables["sql_bundle"]["sql_cohort"]
    assert "SELECT" in sql
    assert "FROM" in sql

    # Verify funnel computed
    assert "funnel_steps" in response.context_variables
    assert len(response.context_variables["funnel_steps"]) > 0
```

---

## Phase 7: Documentation & Deployment (Day 15)

### 7.1 Environment Setup

```bash
# .env.example
OPENAI_API_KEY=sk-...
MODEL_DEFAULT=gpt-4o
MODEL_RESEARCH=gpt-4-turbo
DATABASE_PATH=data/rwd_claims.db
LOG_LEVEL=INFO
```

### 7.2 Running the System

```bash
# Setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .

# Create database
python scripts/create_database.py

# Run REPL
rwd-ie run

# Or directly
python src/main.py run
```

---

## Success Metrics

### MVP (Phase 1-5, Days 1-10)
- ✅ Parse basic I/E criteria into DSL
- ✅ Generate valid SQL for demographics + diagnosis criteria
- ✅ Execute queries and return counts
- ✅ Display funnel in REPL

### Full System (Phase 1-7, Days 1-15)
- ✅ Handle complex temporal logic (lookback windows, duration)
- ✅ Resolve concepts with confidence scoring
- ✅ Generate CTE-based SQL with proper structure
- ✅ Detect and repair SQL errors
- ✅ Interactive iteration loop
- ✅ Final summary with validation checklist

---

## Next Steps After Approval

Once you approve this plan, we'll proceed in this order:

**Day 1:**
1. Create SQLite database from Excel
2. Set up project structure
3. Install dependencies

**Day 2:**
4. Implement Pydantic models
5. Build tool functions (catalog, concept search, SQL executor)

**Day 3-5:**
6. Implement all 6 agents with prompts
7. Set up OpenAI Swarm orchestration

**Day 6-7:**
8. Build REPL interface
9. Integration testing

**Day 8:**
10. Documentation and polish

---

## Questions for You

1. **Model Access:** You mentioned GPT-5.2 and 5.1 - did you mean GPT-4o and GPT-4-turbo, or do you have access to newer models?

2. **Excel File:** Confirmed the file is `synthetic_rwd_claims_data (1).xlsx` in the project directory?

3. **Priority Features:** For MVP, should we focus on:
   - Basic criteria (age, diagnosis, drugs) first?
   - Or full temporal logic from the start?

4. **Iteration Approach:** Should we build:
   - **Option A:** Quick MVP (Days 1-7) → Get your feedback → Enhance
   - **Option B:** Full system upfront (Days 1-15)?

**Please review and approve this plan, or let me know what adjustments you'd like!**
