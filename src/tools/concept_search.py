"""
Concept Search Tool

Searches for clinical concepts in the reference tables.
Used by the Deep Research Agent to resolve concepts to codes.
"""

from typing import List, Dict, Optional, Any
from src.utils.database import get_db_connection


def search_concepts(term: str, code_system: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search for clinical concepts in reference tables.

    This tool searches across ICD-10, CPT, and NDC reference tables
    to find matching codes for a clinical concept.

    Args:
        term: Clinical concept to search (e.g., "diabetes", "metformin", "office visit")
        code_system: Optional filter - "ICD10CM", "CPT", "NDC", or None for all

    Returns:
        List of matches with:
        - code: The medical code
        - description: Full description
        - code_system: Which coding system
        - match_score: Relevance score (1.0 = exact match)
        - additional_info: Extra context (e.g., drug class)

    Example:
        >>> search_concepts("diabetes", "ICD10CM")
        [
            {
                "code": "E11.9",
                "description": "Type 2 diabetes mellitus without complications",
                "code_system": "ICD10CM",
                "match_score": 0.9
            },
            ...
        ]
    """

    results = []
    search_term = term.lower()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Search ICD-10 codes (diagnoses)
        if code_system in [None, "ICD10CM", "ICD10"]:
            query = """
                SELECT icd_10_code, description
                FROM ref_icd10
                WHERE LOWER(description) LIKE ?
                ORDER BY description
            """
            cursor.execute(query, (f"%{search_term}%",))

            for row in cursor.fetchall():
                # Calculate simple match score
                desc_lower = row[1].lower()
                if search_term == desc_lower:
                    score = 1.0
                elif desc_lower.startswith(search_term):
                    score = 0.9
                else:
                    score = 0.7

                results.append(
                    {
                        "code": row[0],
                        "description": row[1],
                        "code_system": "ICD10CM",
                        "match_score": score,
                        "matching_logic": "wildcard_supported",
                    }
                )

        # Search CPT codes (procedures)
        if code_system in [None, "CPT"]:
            query = """
                SELECT cpt_code, description
                FROM ref_cpt
                WHERE LOWER(description) LIKE ?
                ORDER BY description
            """
            cursor.execute(query, (f"%{search_term}%",))

            for row in cursor.fetchall():
                desc_lower = row[1].lower()
                if search_term in desc_lower:
                    score = 0.8
                else:
                    score = 0.6

                results.append(
                    {
                        "code": str(row[0]),
                        "description": row[1],
                        "code_system": "CPT",
                        "match_score": score,
                        "matching_logic": "exact_only",
                    }
                )

        # Search NDC codes (drugs)
        if code_system in [None, "NDC"]:
            query = """
                SELECT ndc_code, drug_name, drug_class
                FROM ref_ndc
                WHERE LOWER(drug_name) LIKE ?
                   OR LOWER(drug_class) LIKE ?
                ORDER BY drug_name
            """
            cursor.execute(query, (f"%{search_term}%", f"%{search_term}%"))

            for row in cursor.fetchall():
                name_match = search_term in row[1].lower()
                class_match = search_term in row[2].lower()

                if name_match and class_match:
                    score = 1.0
                elif name_match:
                    score = 0.9
                else:
                    score = 0.7

                results.append(
                    {
                        "code": row[0],
                        "description": f"{row[1]} ({row[2]})",
                        "drug_name": row[1],
                        "drug_class": row[2],
                        "code_system": "NDC",
                        "match_score": score,
                        "matching_logic": "ingredient_or_class",
                    }
                )

        # Also search in actual claims data for additional context
        if code_system in [None, "ICD10CM", "ICD10"]:
            query = """
                SELECT DISTINCT primary_diagnosis_code, primary_diagnosis_desc
                FROM claims
                WHERE LOWER(primary_diagnosis_desc) LIKE ?
                  AND primary_diagnosis_code IS NOT NULL
                LIMIT 10
            """
            cursor.execute(query, (f"%{search_term}%",))

            for row in cursor.fetchall():
                # Only add if not already in results
                if not any(r["code"] == row[0] for r in results):
                    results.append(
                        {
                            "code": row[0],
                            "description": row[1],
                            "code_system": "ICD10CM",
                            "match_score": 0.6,
                            "matching_logic": "wildcard_supported",
                            "source": "claims_data",
                        }
                    )

    # Sort by match score
    results.sort(key=lambda x: x["match_score"], reverse=True)

    return results


def get_concept_hierarchy(code: str, code_system: str) -> Dict[str, Any]:
    """
    Get hierarchical relationships for a concept code.

    For ICD-10, this includes parent and child codes.

    Args:
        code: Medical code
        code_system: Code system (ICD10CM, CPT, NDC)

    Returns:
        Dictionary with parent, children, and related codes
    """

    if code_system == "ICD10CM":
        # For ICD-10, use prefix matching for hierarchy
        # E11 (T2DM) → E11.9 (without complications), E11.65 (with hyperglycemia), etc.

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get parent code (remove last character)
            parent_code = code[:-1] if len(code) > 3 else None

            # Get children codes (add character)
            cursor.execute(
                "SELECT icd_10_code, description FROM ref_icd10 WHERE icd_10_code LIKE ?",
                (f"{code}%",),
            )
            children = [{"code": row[0], "description": row[1]} for row in cursor.fetchall()]

            # Get siblings (same parent)
            if parent_code:
                cursor.execute(
                    "SELECT icd_10_code, description FROM ref_icd10 WHERE icd_10_code LIKE ?",
                    (f"{parent_code}%",),
                )
                siblings = [{"code": row[0], "description": row[1]} for row in cursor.fetchall()]
            else:
                siblings = []

            return {
                "code": code,
                "code_system": code_system,
                "parent": parent_code,
                "children": children,
                "siblings": siblings,
            }

    return {"code": code, "code_system": code_system, "message": "Hierarchy not supported"}


# For testing
if __name__ == "__main__":
    import json

    print("Searching for 'diabetes':")
    results = search_concepts("diabetes")
    print(json.dumps(results, indent=2))

    print("\n\nSearching for 'metformin':")
    results = search_concepts("metformin", "NDC")
    print(json.dumps(results, indent=2))
