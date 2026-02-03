"""
AI Service Layer
Handles all AI/LLM interactions for the RWD IE Optimizer
"""

from typing import Dict, Any, List, Optional
from swarm import Swarm
import anthropic
import os
import re
import json

from src.agents.agents import (
    ie_interpreter_agent,
    deep_research_agent,
    coding_agent
)


class AIService:
    """Centralized service for all AI operations"""

    def __init__(self):
        self.swarm_client = Swarm()
        self.anthropic_client = None
        self._init_anthropic()

    def _init_anthropic(self):
        """Initialize Anthropic client if API key is available"""
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=api_key)

    # =========================================================================
    # SWARM AGENT OPERATIONS
    # =========================================================================

    def parse_criteria(self, criteria_text: str) -> Dict[str, Any]:
        """
        Parse I/E criteria text into structured Criteria DSL

        Args:
            criteria_text: Raw inclusion/exclusion criteria text

        Returns:
            Parsed criteria DSL as JSON
        """
        prompt = f"""Parse the following I/E criteria into Criteria DSL JSON format.
Return ONLY the JSON, no additional text.

{criteria_text}"""

        response = self.swarm_client.run(
            agent=ie_interpreter_agent,
            messages=[{"role": "user", "content": prompt}]
        )

        criteria_dsl_text = response.messages[-1]["content"]

        # Extract JSON from response
        json_match = re.search(r'\{.*\}', criteria_dsl_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return json.loads(criteria_dsl_text)

    def resolve_concepts(self, criteria_dsl: Dict[str, Any]) -> str:
        """
        Resolve medical concepts to database codes

        Args:
            criteria_dsl: Parsed criteria DSL

        Returns:
            Resolved concepts with code mappings
        """
        prompt = f"""Resolve all medical concepts to database codes.
Use get_catalog() and search_concepts() for each concept.

Criteria DSL:
{json.dumps(criteria_dsl, indent=2)}

Return the resolved concepts with code mappings."""

        response = self.swarm_client.run(
            agent=deep_research_agent,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.messages[-1]["content"]

    def generate_sql(self, criteria_dsl: Dict[str, Any]) -> str:
        """
        Generate SQL queries from criteria DSL

        Args:
            criteria_dsl: Parsed criteria DSL

        Returns:
            Generated SQL query
        """
        prompt = f"""Generate SQL for this criteria.

Criteria DSL:
{json.dumps(criteria_dsl, indent=2)}

Code mappings:
- Type 2 Diabetes: primary_diagnosis_code LIKE 'E11%' OR secondary_diagnosis_code LIKE 'E11%' OR tertiary_diagnosis_code LIKE 'E11%'
- Metformin: drug_name LIKE '%Metformin%'
- Heart failure: primary_diagnosis_code LIKE 'I50%' OR secondary_diagnosis_code LIKE 'I50%' OR tertiary_diagnosis_code LIKE 'I50%'
- Cancer: primary_diagnosis_code LIKE 'C%' OR secondary_diagnosis_code LIKE 'C%' OR tertiary_diagnosis_code LIKE 'C%'

Call get_catalog() first, then generate SQL with CTEs. Return ONLY the SQL in a code block."""

        response = self.swarm_client.run(
            agent=coding_agent,
            messages=[{"role": "user", "content": prompt}]
        )

        sql_response = response.messages[-1]["content"]

        # Extract SQL from code block
        sql_match = re.search(r'```sql\n(.*?)\n```', sql_response, re.DOTALL)
        if sql_match:
            return sql_match.group(1)
        elif "WITH" in sql_response and "SELECT" in sql_response:
            return sql_response.strip()
        else:
            return sql_response

    # =========================================================================
    # SQL DEBUGGING & ASSISTANCE
    # =========================================================================

    def debug_sql(self, sql: str, error: str, tables: List[str]) -> Dict[str, Any]:
        """
        Get AI assistance for debugging SQL errors

        Args:
            sql: Failed SQL query
            error: Error message
            tables: Available database tables

        Returns:
            Analysis and corrected SQL
        """
        prompt = f"""You are a SQL debugging expert. Analyze this SQL error and provide helpful guidance.

DATABASE SCHEMA:
Available tables: {', '.join(tables)}

Key columns:
- patients: patient_id, age, gender
- claims: claim_id, patient_id, primary_diagnosis_code, secondary_diagnosis_code, tertiary_diagnosis_code, drug_name

FAILED SQL QUERY:
{sql}

ERROR MESSAGE:
{error}

Please provide:
1. **What went wrong**: Clear explanation of the error
2. **Why it happened**: Root cause analysis
3. **How to fix it**: Specific steps to correct the query
4. **Corrected SQL**: Provide the fixed SQL query

Format your response in a clear, structured way."""

        response = self.swarm_client.run(
            agent=coding_agent,
            messages=[{"role": "user", "content": prompt}]
        )

        ai_response = response.messages[-1]["content"]

        # Extract corrected SQL if present
        sql_match = re.search(r'```sql\n(.*?)\n```', ai_response, re.DOTALL)
        corrected_sql = sql_match.group(1) if sql_match else None

        return {
            "analysis": ai_response,
            "corrected_sql": corrected_sql
        }

    # =========================================================================
    # INTERACTIVE CHAT (CLAUDE API)
    # =========================================================================

    def chat(
        self,
        message: str,
        sql: str,
        tables: List[str],
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Interactive AI chat for SQL assistance

        Args:
            message: User's message
            sql: Current SQL query
            tables: Available database tables
            chat_history: Previous chat messages

        Returns:
            AI response and any corrected SQL
        """
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured")

        # Build system prompt
        system_prompt = f"""You are Claude, an expert SQL assistant helping debug and improve SQL queries.

DATABASE SCHEMA:
Available tables: {', '.join(tables)}

Key columns:
- patients: patient_id, age, gender
- claims: claim_id, patient_id, primary_diagnosis_code, secondary_diagnosis_code, tertiary_diagnosis_code, drug_name, procedure_code

CURRENT SQL QUERY:
```sql
{sql}
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

        # Add chat history
        if chat_history:
            for msg in chat_history:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

        # Add current message
        messages.append({
            "role": "user",
            "content": message
        })

        # Call Claude API
        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=messages
        )

        ai_response = response.content[0].text

        # Extract SQL if present
        sql_match = re.search(r'```sql\n(.*?)\n```', ai_response, re.DOTALL)
        corrected_sql = sql_match.group(1) if sql_match else None

        return {
            "response": ai_response,
            "corrected_sql": corrected_sql
        }


# Singleton instance
_ai_service = None

def get_ai_service() -> AIService:
    """Get singleton AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
