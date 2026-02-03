"""
Criteria DSL (Domain Specific Language) Models

Defines the structured representation of clinical trial inclusion/exclusion criteria.
This is the single source of truth throughout the workflow.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union
from datetime import date


class TemporalWindow(BaseModel):
    """
    Defines a time window relative to a reference date.

    Examples:
    - Last 365 days before index: {reference: "index_date", before_days: 365, after_days: 0}
    - During baseline period: {reference: "index_date", during: "baseline"}
    """

    reference: str = Field(
        ..., description="Reference date: 'index_date', 'enrollment_start', or custom anchor"
    )
    before_days: Optional[int] = Field(None, description="Number of days before reference")
    after_days: Optional[int] = Field(None, description="Number of days after reference")
    during: Optional[str] = Field(None, description="Named period: 'baseline', 'follow_up', etc.")


class ValueConstraint(BaseModel):
    """
    Defines numeric value constraints for lab results, measurements, etc.

    Examples:
    - Age 18-75: {operator: "between", value: [18, 75], unit: "years"}
    - HbA1c ≥7.0%: {operator: ">=", value: 7.0, unit: "%"}
    """

    operator: Literal[">=", "<=", ">", "<", "=", "between"] = Field(
        ..., description="Comparison operator"
    )
    value: Union[float, tuple[float, float]] = Field(..., description="Value or range")
    unit: Optional[str] = Field(None, description="Unit of measurement")


class CountConstraint(BaseModel):
    """
    Defines count-based constraints for events.

    Examples:
    - At least 2 visits: {operator: ">=", count: 2}
    - Between 3-5 readings: {operator: "between", count: [3, 5]}
    - ≥75% of readings: {operator: ">=", count: 1, proportion: 0.75}
    """

    operator: Literal[">=", "<=", "=", "between"] = Field(..., description="Comparison operator")
    count: Union[int, tuple[int, int]] = Field(..., description="Count value or range")
    within_days: Optional[int] = Field(None, description="Time window for counting")
    proportion: Optional[float] = Field(
        None, description="Proportion of events (0.0-1.0) instead of absolute count"
    )


class ConceptResolution(BaseModel):
    """
    Stores the mapping from clinical concept to dataset-specific codes.

    Filled by the Deep Research Agent after concept resolution.
    """

    resolved: bool = Field(..., description="Whether concept was successfully resolved")
    concept_ids: List[str] = Field(default_factory=list, description="List of codes")
    code_system: Literal[
        "ICD10CM", "ICD9CM", "CPT", "HCPCS", "NDC", "RxNorm", "LOINC", "SNOMED", "local"
    ] = Field(..., description="Code system used")
    matching_logic: Literal["exact", "wildcard", "hierarchy", "ingredient"] = Field(
        ..., description="How codes should be matched"
    )
    unit_rules: Optional[dict] = Field(None, description="Unit conversion rules for labs")
    confidence: Literal["high", "medium", "low"] = Field(..., description="Confidence level")
    alternatives: Optional[List[dict]] = Field(
        None, description="Alternative mappings with pros/cons"
    )


class Predicate(BaseModel):
    """
    A single inclusion or exclusion criterion.

    Represents one logical condition that patients must meet (inclusion)
    or must not meet (exclusion).
    """

    id: str = Field(..., description="Unique predicate ID (e.g., 'I01', 'E03')")
    description: str = Field(..., description="Original text from protocol")

    domain: Literal[
        "demographic", "diagnosis", "procedure", "drug", "lab", "enrollment", "observation"
    ] = Field(..., description="Clinical domain")

    concept: str = Field(..., description="Human-readable concept name")
    concept_resolution: Optional[ConceptResolution] = Field(
        None, description="Resolved codes (filled by Deep Research Agent)"
    )

    temporal: Optional[TemporalWindow] = Field(None, description="Time window constraint")
    value_constraint: Optional[ValueConstraint] = Field(None, description="Numeric value constraint")
    count_constraint: Optional[CountConstraint] = Field(None, description="Count-based constraint")

    verifiability: Literal["rwd", "partial_rwd", "non_rwd"] = Field(
        ..., description="Can this be verified in RWD?"
    )

    needs_definition: bool = Field(
        False, description="Whether this criterion is ambiguous and needs clarification"
    )
    candidate_definitions: Optional[List[str]] = Field(
        None, description="Proposed operational definitions for ambiguous criteria"
    )


class Gap(BaseModel):
    """
    Represents an assumption or gap in the criteria that requires attention.

    Examples:
    - Missing operational definition
    - Data not available in RWD
    - Ambiguous temporal logic
    """

    predicate_id: str = Field(..., description="Related predicate ID")
    issue: str = Field(..., description="Description of the gap or assumption")
    proposed_resolution: Optional[str] = Field(None, description="Suggested way to handle it")
    requires_user_input: bool = Field(
        ..., description="Whether user input is needed to resolve"
    )


class AnchorDefinition(BaseModel):
    """
    Defines the index event or anchor point for temporal logic.

    Examples:
    - enrollment_date
    - first_diagnosis_of_t2dm
    - screening_visit_date
    """

    name: str = Field(..., description="Anchor name")
    description: str = Field(..., description="How to compute this date")
    derivation_logic: Optional[str] = Field(
        None, description="SQL logic or rule for deriving the anchor"
    )


class CriteriaDSL(BaseModel):
    """
    Complete structured representation of I/E criteria.

    This is the single source of truth throughout the workflow.
    All agents read from and contribute to this structure.
    """

    study_id: str = Field(..., description="Study identifier")
    version: str = Field(default="1.0", description="Criteria version")

    anchors: dict = Field(
        ...,
        description="Index events and temporal anchors",
        example={
            "index_event": {"name": "enrollment_date", "description": "Patient enrollment date"}
        },
    )

    inclusion: List[Predicate] = Field(default_factory=list, description="Inclusion criteria")
    exclusion: List[Predicate] = Field(default_factory=list, description="Exclusion criteria")

    assumptions_and_gaps: List[Gap] = Field(
        default_factory=list, description="Known gaps and assumptions"
    )
    non_rwd_gates: List[str] = Field(
        default_factory=list, description="Criteria that cannot be verified in RWD"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "study_id": "trial_001",
                "version": "1.0",
                "anchors": {
                    "index_event": {
                        "name": "enrollment_date",
                        "description": "Date of study enrollment",
                    }
                },
                "inclusion": [
                    {
                        "id": "I01",
                        "description": "Adults aged 18-75 years",
                        "domain": "demographic",
                        "concept": "age",
                        "value_constraint": {"operator": "between", "value": [18, 75]},
                        "verifiability": "rwd",
                        "needs_definition": False,
                    }
                ],
                "exclusion": [],
                "assumptions_and_gaps": [],
                "non_rwd_gates": [],
            }
        }
