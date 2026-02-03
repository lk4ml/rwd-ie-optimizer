"""
Resolved Concepts Models

Output from the Deep Research Agent after concept resolution.
Contains mappings from clinical concepts to dataset-specific codes.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal


class AlternativeMapping(BaseModel):
    """
    Alternative way to map a concept with pros/cons.
    """

    concept_ids: List[str] = Field(..., description="Alternative code set")
    description: str = Field(..., description="Description of this mapping")
    pros: List[str] = Field(default_factory=list, description="Advantages")
    cons: List[str] = Field(default_factory=list, description="Disadvantages")
    confidence: Literal["high", "medium", "low"] = Field(..., description="Confidence level")


class PhenotypeDefinition(BaseModel):
    """
    Operational definition of a clinical phenotype or derived variable.

    Examples:
    - "Continuous metformin use" = no gap >30 days in fills
    - "Rapid eGFR decline" = >5 mL/min/1.73m² decrease per year
    """

    name: str = Field(..., description="Phenotype name")
    description: str = Field(..., description="Clinical definition")
    implementation: str = Field(..., description="How to compute in SQL")
    required_fields: List[str] = Field(
        default_factory=list, description="Database fields needed"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ..., description="Confidence in implementation"
    )


class Question(BaseModel):
    """
    Open question that needs user input for concept resolution.
    """

    predicate_id: str = Field(..., description="Related predicate ID")
    question: str = Field(..., description="Question to ask user")
    options: Optional[List[str]] = Field(None, description="Suggested options")
    rationale: str = Field(..., description="Why this question is needed")


class ConceptResolutionDetail(BaseModel):
    """
    Detailed resolution for a single concept with alternatives.
    """

    predicate_id: str = Field(..., description="Predicate ID from Criteria DSL")
    concept_name: str = Field(..., description="Original concept name")

    # Primary resolution
    resolved: bool = Field(..., description="Successfully resolved?")
    concept_ids: List[str] = Field(default_factory=list, description="Primary code set")
    code_system: Literal[
        "ICD10CM", "ICD9CM", "CPT", "HCPCS", "NDC", "RxNorm", "LOINC", "SNOMED", "local"
    ] = Field(..., description="Code system")
    matching_logic: Literal["exact", "wildcard", "hierarchy", "ingredient"] = Field(
        ..., description="Matching strategy"
    )

    # Metadata
    confidence: Literal["high", "medium", "low"] = Field(..., description="Confidence level")
    notes: Optional[str] = Field(None, description="Additional notes")

    # Alternatives
    alternatives: List[AlternativeMapping] = Field(
        default_factory=list, description="Alternative mappings"
    )


class ResolvedConcepts(BaseModel):
    """
    Complete output from Deep Research Agent.

    Contains all concept resolutions, phenotype definitions, open questions,
    and assumptions made during resolution.
    """

    study_id: str = Field(..., description="Study identifier")

    resolved_concepts: Dict[str, ConceptResolutionDetail] = Field(
        default_factory=dict,
        description="Map of predicate_id → concept resolution",
    )

    phenotype_definitions: Dict[str, List[PhenotypeDefinition]] = Field(
        default_factory=dict,
        description="Map of predicate_id → phenotype definitions",
    )

    open_questions: List[Question] = Field(
        default_factory=list, description="Questions needing user input"
    )

    assumptions: List[str] = Field(
        default_factory=list, description="Assumptions made during resolution"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "study_id": "trial_001",
                "resolved_concepts": {
                    "I02": {
                        "predicate_id": "I02",
                        "concept_name": "Type 2 Diabetes",
                        "resolved": True,
                        "concept_ids": ["E11.9", "E11.0", "E11.1", "E11.2"],
                        "code_system": "ICD10CM",
                        "matching_logic": "wildcard",
                        "confidence": "high",
                        "alternatives": [],
                    }
                },
                "phenotype_definitions": {},
                "open_questions": [],
                "assumptions": ["Using ICD-10-CM codes only (no ICD-9-CM mapping)"],
            }
        }
