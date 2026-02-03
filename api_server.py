"""
FastAPI Backend for RWD IE Optimizer
Provides API endpoints for the React frontend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from swarm import Swarm
from src.agents.agents import (
    ie_interpreter_agent,
    deep_research_agent,
    coding_agent
)
from src.tools.sql_executor import run_sql
import anthropic
import os

app = FastAPI(title="RWD IE Optimizer API")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Swarm client
client = Swarm()


class CriteriaInput(BaseModel):
    criteria_text: str


class SQLQuery(BaseModel):
    sql: str


@app.get("/")
def read_root():
    """Serve the React UI"""
    return FileResponse("static/index.html")


@app.post("/api/process-criteria")
async def process_criteria(input_data: CriteriaInput):
    """
    Complete workflow: Parse → Resolve → Generate SQL → Execute
    Returns all results with stage information
    """

    try:
        results = {
            "stages": [],
            "criteria_dsl": None,
            "resolved_concepts": None,
            "generated_sql": None,
            "execution_result": None,
            "funnel_data": None
        }

        # STAGE 1: IE INTERPRETER
        results["stages"].append({
            "stage": 1,
            "name": "IE Interpreter",
            "status": "processing",
            "description": "Parsing I/E criteria into structured format..."
        })

        response = client.run(
            agent=ie_interpreter_agent,
            messages=[{
                "role": "user",
                "content": f"""Parse the following I/E criteria into Criteria DSL JSON format.
Return ONLY the JSON, no additional text.

{input_data.criteria_text}"""
            }]
        )

        criteria_dsl_text = response.messages[-1]["content"]

        # Extract JSON
        json_match = re.search(r'\{.*\}', criteria_dsl_text, re.DOTALL)
        if json_match:
            criteria_dsl = json.loads(json_match.group())
        else:
            criteria_dsl = json.loads(criteria_dsl_text)

        results["criteria_dsl"] = criteria_dsl
        results["stages"][-1]["status"] = "completed"
        results["stages"][-1]["result"] = criteria_dsl

        # STAGE 2: DEEP RESEARCH
        results["stages"].append({
            "stage": 2,
            "name": "Deep Research",
            "status": "processing",
            "description": "Resolving medical concepts to database codes..."
        })

        response = client.run(
            agent=deep_research_agent,
            messages=[{
                "role": "user",
                "content": f"""Resolve all medical concepts to database codes.
Use get_catalog() and search_concepts() for each concept.

Criteria DSL:
{json.dumps(criteria_dsl, indent=2)}

Return the resolved concepts with code mappings."""
            }]
        )

        resolved_concepts = response.messages[-1]["content"]
        results["resolved_concepts"] = resolved_concepts
        results["stages"][-1]["status"] = "completed"
        results["stages"][-1]["result"] = resolved_concepts

        # STAGE 3: CODING AGENT
        results["stages"].append({
            "stage": 3,
            "name": "Coding Agent",
            "status": "processing",
            "description": "Generating SQL queries from criteria..."
        })

        response = client.run(
            agent=coding_agent,
            messages=[{
                "role": "user",
                "content": f"""Generate SQL for this criteria.

Criteria DSL:
{json.dumps(criteria_dsl, indent=2)}

Code mappings:
- Type 2 Diabetes: primary_diagnosis_code LIKE 'E11%' OR secondary_diagnosis_code LIKE 'E11%' OR tertiary_diagnosis_code LIKE 'E11%'
- Metformin: drug_name LIKE '%Metformin%'
- Heart failure: primary_diagnosis_code LIKE 'I50%' OR secondary_diagnosis_code LIKE 'I50%' OR tertiary_diagnosis_code LIKE 'I50%'
- Cancer: primary_diagnosis_code LIKE 'C%' OR secondary_diagnosis_code LIKE 'C%' OR tertiary_diagnosis_code LIKE 'C%'

Call get_catalog() first, then generate SQL with CTEs. Return ONLY the SQL in a code block."""
            }]
        )

        sql_response = response.messages[-1]["content"]

        # Extract SQL
        sql_match = re.search(r'```sql\n(.*?)\n```', sql_response, re.DOTALL)
        if sql_match:
            generated_sql = sql_match.group(1)
        elif "WITH" in sql_response and "SELECT" in sql_response:
            generated_sql = sql_response.strip()
        else:
            generated_sql = sql_response

        results["generated_sql"] = generated_sql
        results["stages"][-1]["status"] = "completed"
        results["stages"][-1]["result"] = generated_sql

        # STAGE 4: SQL EXECUTION
        results["stages"].append({
            "stage": 4,
            "name": "SQL Runner",
            "status": "processing",
            "description": "Executing SQL against database..."
        })

        exec_result = run_sql(generated_sql, mode="preview")
        results["execution_result"] = exec_result
        results["stages"][-1]["status"] = "completed" if exec_result["ok"] else "error"
        results["stages"][-1]["result"] = exec_result

        # STAGE 5: FUNNEL CALCULATION
        if exec_result["ok"]:
            results["stages"].append({
                "stage": 5,
                "name": "Funnel Analysis",
                "status": "processing",
                "description": "Calculating patient funnel..."
            })

            funnel_steps = []

            # Base population
            base_result = run_sql("SELECT COUNT(*) as cnt FROM patients", mode="preview")
            base_count = base_result["preview_rows"][0]["cnt"] if base_result["ok"] else 500
            funnel_steps.append({
                "step": "Base Population",
                "count": base_count,
                "pct": 100.0
            })

            # Age filter (if exists in criteria)
            if any(p.get("domain") == "demographic" for p in criteria_dsl.get("inclusion", [])):
                age_sql = "SELECT COUNT(*) as cnt FROM patients WHERE age BETWEEN 18 AND 75"
                age_result = run_sql(age_sql, mode="preview")
                if age_result["ok"]:
                    age_count = age_result["preview_rows"][0]["cnt"]
                    funnel_steps.append({
                        "step": "Age Filter (18-75)",
                        "count": age_count,
                        "pct": round((age_count / base_count * 100), 1)
                    })

            # Diagnosis filter
            if any(p.get("domain") == "diagnosis" for p in criteria_dsl.get("inclusion", [])):
                dx_sql = """SELECT COUNT(DISTINCT patient_id) as cnt FROM claims
                           WHERE primary_diagnosis_code LIKE 'E11%'"""
                dx_result = run_sql(dx_sql, mode="preview")
                if dx_result["ok"]:
                    dx_count = dx_result["preview_rows"][0]["cnt"]
                    funnel_steps.append({
                        "step": "Type 2 Diabetes",
                        "count": dx_count,
                        "pct": round((dx_count / base_count * 100), 1)
                    })

            # Final cohort
            final_count = exec_result["execution_summary"]["n"]
            funnel_steps.append({
                "step": "Final Cohort",
                "count": final_count,
                "pct": round((final_count / base_count * 100), 1)
            })

            results["funnel_data"] = funnel_steps
            results["stages"][-1]["status"] = "completed"
            results["stages"][-1]["result"] = funnel_steps

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/execute-sql")
async def execute_sql(query: SQLQuery):
    """Execute custom SQL query"""
    try:
        result = run_sql(query.sql, mode="preview")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/database-info")
async def get_database_info():
    """Get database statistics"""
    try:
        stats = {}

        # Patient count
        result = run_sql("SELECT COUNT(*) as cnt FROM patients", mode="preview")
        if result["ok"]:
            stats["patient_count"] = result["preview_rows"][0]["cnt"]

        # Claims count
        result = run_sql("SELECT COUNT(*) as cnt FROM claims", mode="preview")
        if result["ok"]:
            stats["claims_count"] = result["preview_rows"][0]["cnt"]

        # Tables
        result = run_sql("SELECT name FROM sqlite_master WHERE type='table'", mode="preview")
        if result["ok"]:
            stats["tables"] = [row["name"] for row in result["preview_rows"]]

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SQLDebugRequest(BaseModel):
    sql: str
    error: str


@app.post("/api/debug-sql")
async def debug_sql(request: SQLDebugRequest):
    """Get AI assistance for debugging SQL errors"""
    try:
        # Get database schema for context
        schema_result = run_sql("SELECT name FROM sqlite_master WHERE type='table'", mode="preview")
        tables = [row["name"] for row in schema_result["preview_rows"]] if schema_result["ok"] else []

        # Use coding agent to analyze the error
        response = client.run(
            agent=coding_agent,
            messages=[{
                "role": "user",
                "content": f"""You are a SQL debugging expert. Analyze this SQL error and provide helpful guidance.

DATABASE SCHEMA:
Available tables: {', '.join(tables)}

Key columns:
- patients: patient_id, age, gender
- claims: claim_id, patient_id, primary_diagnosis_code, secondary_diagnosis_code, tertiary_diagnosis_code, drug_name

FAILED SQL QUERY:
{request.sql}

ERROR MESSAGE:
{request.error}

Please provide:
1. **What went wrong**: Clear explanation of the error
2. **Why it happened**: Root cause analysis
3. **How to fix it**: Specific steps to correct the query
4. **Corrected SQL**: Provide the fixed SQL query

Format your response in a clear, structured way."""
            }]
        )

        ai_response = response.messages[-1]["content"]

        # Extract corrected SQL if present
        import re
        sql_match = re.search(r'```sql\n(.*?)\n```', ai_response, re.DOTALL)
        corrected_sql = sql_match.group(1) if sql_match else None

        return {
            "ok": True,
            "analysis": ai_response,
            "corrected_sql": corrected_sql
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


class AIChatRequest(BaseModel):
    message: str
    sql: str
    chat_history: List[Dict[str, str]] = []
    last_execution_result: Optional[Dict[str, Any]] = None


@app.post("/api/ai-chat")
async def ai_chat(request: AIChatRequest):
    """Interactive AI chat for SQL assistance using Claude API"""
    try:
        # Initialize Anthropic client
        anthropic_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not anthropic_key:
            return {
                "ok": False,
                "error": "No API key configured. Please set ANTHROPIC_API_KEY in your .env file."
            }

        claude_client = anthropic.Anthropic(api_key=anthropic_key)

        # Get database schema
        schema_result = run_sql("SELECT name FROM sqlite_master WHERE type='table'", mode="preview")
        tables = [row["name"] for row in schema_result["preview_rows"]] if schema_result["ok"] else []

        # Build system prompt
        system_prompt = f"""You are Claude, an expert SQL assistant helping debug and improve SQL queries.

DATABASE SCHEMA:
Available tables: {', '.join(tables)}

Key columns:
- patients: patient_id, age, gender
- claims: claim_id, patient_id, primary_diagnosis_code, secondary_diagnosis_code, tertiary_diagnosis_code, drug_name, procedure_code

CURRENT SQL QUERY:
```sql
{request.sql}
```

Your role:
1. Analyze the SQL query for potential issues
2. Explain errors clearly and suggest fixes
3. Answer questions about the query
4. Provide corrected SQL when needed
5. Test your suggestions by running the query if requested

Be conversational, helpful, and concise."""

        # Build messages for Claude API
        messages = []

        # Add chat history (skip system messages)
        for msg in request.chat_history:
            if msg["role"] in ["user", "assistant"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Add current message
        messages.append({
            "role": "user",
            "content": request.message
        })

        # Call Claude API
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=messages
        )

        ai_response = response.content[0].text

        # Extract SQL if present
        import re
        sql_match = re.search(r'```sql\n(.*?)\n```', ai_response, re.DOTALL)
        corrected_sql = sql_match.group(1) if sql_match else None

        return {
            "ok": True,
            "response": ai_response,
            "corrected_sql": corrected_sql
        }

    except Exception as e:
        print(f"AI chat error: {str(e)}")
        return {
            "ok": False,
            "error": str(e)
        }


class WhatIfRequest(BaseModel):
    enabled_inclusion: List[str]
    enabled_exclusion: List[str]
    criteria_dsl: Dict[str, Any]


@app.post("/api/funnel-whatif")
async def calculate_funnel_whatif(request: WhatIfRequest):
    """Calculate patient funnel based on selected criteria"""
    try:
        steps = []

        # Get base population
        base_result = run_sql("SELECT COUNT(*) as cnt FROM patients", mode="preview")
        base_count = base_result["preview_rows"][0]["cnt"] if base_result["ok"] else 500

        current_count = base_count

        # Process inclusion criteria
        for criterion in request.criteria_dsl.get("inclusion", []):
            criterion_id = criterion.get("id", "unknown")

            # Skip if not enabled
            if criterion_id not in request.enabled_inclusion:
                continue

            # Build SQL based on criterion
            sql = build_criterion_sql(criterion, base_count)

            if sql:
                result = run_sql(sql, mode="preview")
                if result["ok"] and result["preview_rows"]:
                    new_count = result["preview_rows"][0]["cnt"]
                    drop_count = current_count - new_count
                    drop_pct = (drop_count / current_count * 100) if current_count > 0 else 0

                    steps.append({
                        "id": criterion_id,
                        "name": criterion.get("description", criterion.get("concept", "Unknown")),
                        "type": "inclusion",
                        "count": new_count,
                        "percentage": (new_count / base_count * 100) if base_count > 0 else 0,
                        "drop_count": drop_count,
                        "drop_pct": drop_pct
                    })

                    current_count = new_count

        # Process exclusion criteria
        for criterion in request.criteria_dsl.get("exclusion", []):
            criterion_id = criterion.get("id", "unknown")

            # Skip if not enabled
            if criterion_id not in request.enabled_exclusion:
                continue

            # Build SQL for exclusion
            sql = build_exclusion_sql(criterion, current_count)

            if sql:
                result = run_sql(sql, mode="preview")
                if result["ok"] and result["preview_rows"]:
                    excluded_count = result["preview_rows"][0]["cnt"]
                    new_count = current_count - excluded_count
                    drop_pct = (excluded_count / current_count * 100) if current_count > 0 else 0

                    steps.append({
                        "id": criterion_id,
                        "name": "Exclude: " + criterion.get("description", criterion.get("concept", "Unknown")),
                        "type": "exclusion",
                        "count": new_count,
                        "percentage": (new_count / base_count * 100) if base_count > 0 else 0,
                        "drop_count": excluded_count,
                        "drop_pct": drop_pct
                    })

                    current_count = new_count

        return {
            "ok": True,
            "base_count": base_count,
            "final_count": current_count,
            "steps": steps
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


def build_criterion_sql(criterion, base_count):
    """Build SQL for a single criterion"""
    domain = criterion.get("domain", "").lower()
    concept = criterion.get("concept", "").lower()

    # Demographic filters
    if domain == "demographic" or "age" in concept:
        return "SELECT COUNT(*) as cnt FROM patients WHERE age BETWEEN 18 AND 75"

    # Diagnosis filters
    elif domain == "diagnosis" or "diabetes" in concept or "type 2" in concept:
        return """
            SELECT COUNT(DISTINCT patient_id) as cnt FROM claims
            WHERE primary_diagnosis_code LIKE 'E11%'
            OR secondary_diagnosis_code LIKE 'E11%'
            OR tertiary_diagnosis_code LIKE 'E11%'
        """

    # Medication filters
    elif domain == "drug" or "metformin" in concept:
        return """
            SELECT COUNT(DISTINCT patient_id) as cnt FROM claims
            WHERE drug_name LIKE '%Metformin%'
        """

    # Default: return base count
    return f"SELECT {base_count} as cnt"


def build_exclusion_sql(criterion, current_count):
    """Build SQL for exclusion criterion"""
    concept = criterion.get("concept", "").lower()

    # Heart failure exclusion
    if "heart failure" in concept or "heart" in concept:
        return """
            SELECT COUNT(DISTINCT patient_id) as cnt FROM claims
            WHERE primary_diagnosis_code LIKE 'I50%'
            OR secondary_diagnosis_code LIKE 'I50%'
            OR tertiary_diagnosis_code LIKE 'I50%'
        """

    # Cancer exclusion
    elif "cancer" in concept:
        return """
            SELECT COUNT(DISTINCT patient_id) as cnt FROM claims
            WHERE primary_diagnosis_code LIKE 'C%'
            OR secondary_diagnosis_code LIKE 'C%'
            OR tertiary_diagnosis_code LIKE 'C%'
        """

    # Default: no exclusion
    return "SELECT 0 as cnt"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
