"""
Funnel Service
Handles patient funnel calculations and "What If" analysis
"""

from typing import Dict, Any, List
from src.tools.sql_executor import run_sql


class FunnelService:
    """Service for calculating patient funnels and what-if scenarios"""

    def calculate_funnel(self, criteria_dsl: Dict[str, Any], exec_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculate patient funnel steps

        Args:
            criteria_dsl: Parsed criteria DSL
            exec_result: SQL execution result

        Returns:
            List of funnel steps with counts and percentages
        """
        funnel_steps = []

        # Get base population
        base_result = run_sql("SELECT COUNT(*) as cnt FROM patients", mode="preview")
        base_count = base_result["preview_rows"][0]["cnt"] if base_result["ok"] else 500

        # Add base population
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

        return funnel_steps

    def calculate_whatif(
        self,
        enabled_inclusion: List[str],
        enabled_exclusion: List[str],
        criteria_dsl: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate what-if scenario based on selected criteria

        Args:
            enabled_inclusion: List of enabled inclusion criterion IDs
            enabled_exclusion: List of enabled exclusion criterion IDs
            criteria_dsl: Parsed criteria DSL

        Returns:
            Funnel steps with counts and percentages
        """
        steps = []

        # Get base population
        base_result = run_sql("SELECT COUNT(*) as cnt FROM patients", mode="preview")
        base_count = base_result["preview_rows"][0]["cnt"] if base_result["ok"] else 500

        current_count = base_count

        # Process inclusion criteria
        for criterion in criteria_dsl.get("inclusion", []):
            criterion_id = criterion.get("id", "unknown")

            # Skip if not enabled
            if criterion_id not in enabled_inclusion:
                continue

            # Build SQL based on criterion
            sql = self._build_criterion_sql(criterion, base_count)

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
        for criterion in criteria_dsl.get("exclusion", []):
            criterion_id = criterion.get("id", "unknown")

            # Skip if not enabled
            if criterion_id not in enabled_exclusion:
                continue

            # Build SQL for exclusion
            sql = self._build_exclusion_sql(criterion, current_count)

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
            "base_count": base_count,
            "final_count": current_count,
            "steps": steps
        }

    def _build_criterion_sql(self, criterion: Dict[str, Any], base_count: int) -> str:
        """Build SQL for a single inclusion criterion"""
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

    def _build_exclusion_sql(self, criterion: Dict[str, Any], current_count: int) -> str:
        """Build SQL for a single exclusion criterion"""
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


# Singleton instance
_funnel_service = None

def get_funnel_service() -> FunnelService:
    """Get singleton funnel service instance"""
    global _funnel_service
    if _funnel_service is None:
        _funnel_service = FunnelService()
    return _funnel_service
