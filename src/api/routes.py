"""
API Routes for RWD IE Optimizer
Clean, organized endpoint definitions
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from src.services.ai_service import get_ai_service
from src.services.funnel_service import get_funnel_service
from src.tools.sql_executor import run_sql

# Create router
router = APIRouter()

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CriteriaInput(BaseModel):
    criteria_text: str


class SQLQuery(BaseModel):
    sql: str


class SQLDebugRequest(BaseModel):
    sql: str
    error: str


class AIChatRequest(BaseModel):
    message: str
    sql: str
    chat_history: List[Dict[str, str]] = []
    last_execution_result: Optional[Dict[str, Any]] = None


class WhatIfRequest(BaseModel):
    enabled_inclusion: List[str]
    enabled_exclusion: List[str]
    criteria_dsl: Dict[str, Any]


# ============================================================================
# MAIN WORKFLOW ENDPOINT
# ============================================================================

@router.post("/api/process-criteria")
async def process_criteria(input_data: CriteriaInput):
    """
    Complete workflow: Parse → Resolve → Generate SQL → Execute
    Returns all results with stage information
    """
    try:
        ai_service = get_ai_service()
        funnel_service = get_funnel_service()

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

        criteria_dsl = ai_service.parse_criteria(input_data.criteria_text)
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

        resolved_concepts = ai_service.resolve_concepts(criteria_dsl)
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

        generated_sql = ai_service.generate_sql(criteria_dsl)
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

            funnel_steps = funnel_service.calculate_funnel(criteria_dsl, exec_result)
            results["funnel_data"] = funnel_steps
            results["stages"][-1]["status"] = "completed"
            results["stages"][-1]["result"] = funnel_steps

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SQL EXECUTION ENDPOINTS
# ============================================================================

@router.post("/api/execute-sql")
async def execute_sql(query: SQLQuery):
    """Execute custom SQL query"""
    try:
        result = run_sql(query.sql, mode="preview")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/database-info")
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


# ============================================================================
# AI ASSISTANCE ENDPOINTS
# ============================================================================

@router.post("/api/debug-sql")
async def debug_sql(request: SQLDebugRequest):
    """Get AI assistance for debugging SQL errors"""
    try:
        ai_service = get_ai_service()

        # Get available tables
        schema_result = run_sql("SELECT name FROM sqlite_master WHERE type='table'", mode="preview")
        tables = [row["name"] for row in schema_result["preview_rows"]] if schema_result["ok"] else []

        # Get AI analysis
        result = ai_service.debug_sql(request.sql, request.error, tables)

        return {
            "ok": True,
            "analysis": result["analysis"],
            "corrected_sql": result["corrected_sql"]
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


@router.post("/api/ai-chat")
async def ai_chat(request: AIChatRequest):
    """Interactive AI chat for SQL assistance using Claude API"""
    try:
        ai_service = get_ai_service()

        # Get available tables
        schema_result = run_sql("SELECT name FROM sqlite_master WHERE type='table'", mode="preview")
        tables = [row["name"] for row in schema_result["preview_rows"]] if schema_result["ok"] else []

        # Get AI response
        result = ai_service.chat(
            message=request.message,
            sql=request.sql,
            tables=tables,
            chat_history=request.chat_history
        )

        return {
            "ok": True,
            "response": result["response"],
            "corrected_sql": result["corrected_sql"]
        }

    except ValueError as e:
        return {
            "ok": False,
            "error": str(e)
        }
    except Exception as e:
        print(f"AI chat error: {str(e)}")
        return {
            "ok": False,
            "error": str(e)
        }


# ============================================================================
# FUNNEL ANALYSIS ENDPOINTS
# ============================================================================

@router.post("/api/funnel-whatif")
async def calculate_funnel_whatif(request: WhatIfRequest):
    """Calculate patient funnel based on selected criteria"""
    try:
        funnel_service = get_funnel_service()

        result = funnel_service.calculate_whatif(
            enabled_inclusion=request.enabled_inclusion,
            enabled_exclusion=request.enabled_exclusion,
            criteria_dsl=request.criteria_dsl
        )

        return {
            "ok": True,
            **result
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }
