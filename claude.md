# RWE Inclusion/Exclusion Optimizer

## Project Overview

This system converts clinical trial protocol I/E (Inclusion/Exclusion) criteria text into executable SQL cohort queries over Real-World Data (RWD). It uses a multi-agent architecture where specialized agents handle parsing, concept resolution, SQL generation, execution, and summarization.

**Core Problem Solved:** Clinical trial protocols define patient eligibility in natural language. Translating these into database queries requires:
- Medical concept resolution (drug classes, lab tests, diagnoses)
- Schema-aware SQL generation
- Temporal logic handling
- Iterative refinement based on cohort counts

**Key Principle:** The system NEVER hard-codes clinical knowledge. All mappings come from tools and catalog queries.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR AGENT                           │
│                     (REPL Controller / Brain)                       │
│                                                                     │
│  Manages workflow, user interaction, agent coordination, looping    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ IE INTERPRETER│       │  DEEP RESEARCH  │       │  CODING AGENT   │
│    AGENT      │       │     AGENT       │       │                 │
│               │       │                 │       │                 │
│ Text → DSL    │       │ Concept Resolver│       │ DSL → SQL       │
│ JSON          │       │ Phenotype Defs  │       │ Query Repair    │
└───────────────┘       └─────────────────┘       └─────────────────┘
                                                          │
                                                          ▼
                                                  ┌─────────────────┐
                                                  │  SQL RUNNER     │
                                                  │  VALIDATOR      │
                                                  │                 │
                                                  │ Execute & Check │
                                                  └─────────────────┘
                                                          │
                                                          ▼
                                                  ┌─────────────────┐
                                                  │    RECEIVER     │
                                                  │     AGENT       │
                                                  │                 │
                                                  │ Summary & Funnel│
                                                  └─────────────────┘
```

---

## Core Data Structures

### Criteria DSL JSON Schema

The Criteria DSL is the **single source of truth** throughout the workflow. All agents read from and contribute to this structure.

```typescript
interface CriteriaDSL {
  study_id: string;
  version: string;
  
  anchors: {
    index_event: AnchorDefinition;      // e.g., screening_date, first_diagnosis
    study_period?: { start: string; end: string };
  };
  
  inclusion: Predicate[];
  exclusion: Predicate[];
  
  assumptions_and_gaps: Gap[];
  non_rwd_gates: string[];              // Criteria that cannot be verified in RWD
}

interface Predicate {
  id: string;                           // e.g., "I01", "E03"
  description: string;                  // Original text from protocol
  
  domain: "demographic" | "diagnosis" | "procedure" | "drug" | "lab" | "enrollment" | "observation";
  
  concept: string;                      // Human-readable concept name
  concept_resolution?: ConceptResolution;  // Filled by Deep Research Agent
  
  temporal?: TemporalWindow;
  value_constraint?: ValueConstraint;
  count_constraint?: CountConstraint;
  
  verifiability: "rwd" | "partial_rwd" | "non_rwd";
  
  needs_definition?: boolean;           // Flag for ambiguous criteria
  candidate_definitions?: string[];     // Proposed interpretations
}

interface ConceptResolution {
  resolved: boolean;
  concept_ids: string[];
  code_system: "ICD10CM" | "ICD9CM" | "CPT" | "HCPCS" | "NDC" | "RxNorm" | "LOINC" | "SNOMED" | "local";
  matching_logic: "exact" | "wildcard" | "hierarchy" | "ingredient";
  unit_rules?: UnitConversion;
  confidence: "high" | "medium" | "low";
  alternatives?: AlternativeMapping[];
}

interface TemporalWindow {
  reference: string;                    // "index_date" | "enrollment_start" | custom anchor
  before_days?: number;
  after_days?: number;
  during?: string;                      // e.g., "baseline", "follow_up"
}

interface ValueConstraint {
  operator: ">=" | "<=" | ">" | "<" | "=" | "between";
  value: number | [number, number];
  unit?: string;
}

interface CountConstraint {
  operator: ">=" | "<=" | "=" | "between";
  count: number | [number, number];
  within_days?: number;
  proportion?: number;                  // e.g., 0.75 for "≥75% of readings"
}

interface Gap {
  predicate_id: string;
  issue: string;
  proposed_resolution?: string;
  requires_user_input: boolean;
}
```

### Resolved Concepts JSON

Output from Deep Research Agent:

```typescript
interface ResolvedConcepts {
  resolved_concepts: {
    [predicate_id: string]: ConceptResolution;
  };
  
  phenotype_definitions: {
    [predicate_id: string]: PhenotypeDefinition[];
  };
  
  open_questions: Question[];
  assumptions: string[];
}

interface PhenotypeDefinition {
  name: string;
  description: string;
  implementation: string;               // How to compute in SQL
  required_fields: string[];
  confidence: "high" | "medium" | "low";
}
```

### SQL Output Bundle

Output from Coding Agent:

```typescript
interface SQLBundle {
  sql_cohort: string;                   // Main cohort query
  sql_funnel_counts: string;            // Step-by-step attrition query
  parameters?: Record<string, any>;     // Parameterized values
  cte_manifest: CTEInfo[];              // Documentation of each CTE
  assumptions: string[];
  repair_notes?: string;                // If this was a repair iteration
}

interface CTEInfo {
  name: string;                         // e.g., "p_I01", "p_E03"
  predicate_id: string;
  description: string;
  row_estimate?: number;
}
```

---

## Agent Specifications

### 1. Orchestrator Agent

**Role:** REPL controller that manages the workflow, coordinates agents, and handles user interaction.

**Responsibilities:**
- Parse user's I/E text input
- Coordinate agent invocations in correct sequence
- Maintain Criteria DSL as source of truth
- Present results in consistent REPL format
- Handle iteration loops until user satisfaction
- Trigger finalization and handoff

**REPL Output Contract:**
```
═══════════════════════════════════════════════════════
CURRENT CRITERIA (JSON)
═══════════════════════════════════════════════════════
{criteria_dsl}

═══════════════════════════════════════════════════════
CURRENT SQL (COHORT)
═══════════════════════════════════════════════════════
{sql_cohort or "pending build"}

═══════════════════════════════════════════════════════
FUNNEL STEPS (COUNTS)
═══════════════════════════════════════════════════════
{funnel_table or "pending run"}

═══════════════════════════════════════════════════════
WARNINGS / UNVERIFIABLE GATES
═══════════════════════════════════════════════════════
{warnings}

═══════════════════════════════════════════════════════
NEXT ACTION
═══════════════════════════════════════════════════════
{what_needed_from_user OR suggested_edit}
```

**Stop Conditions:** User says "finalize", "good", "ship it", or equivalent approval.

---

### 2. IE Interpreter Agent

**Role:** Parse raw I/E text into structured Criteria DSL.

**Input:** Raw inclusion/exclusion text from protocol
**Output:** Criteria DSL JSON (without concept codes - those come from Deep Research)

**Rules:**
- Extract ALL thresholds, units, timing windows, sequencing requirements
- Extract proportion rules (e.g., "≥75% of readings")
- Mark ambiguous items with `needs_definition: true`
- Classify verifiability: `rwd`, `partial_rwd`, `non_rwd`
- Do NOT reference database tables/columns
- Do NOT map to codes (that's Deep Research Agent's job)

**Example Ambiguous Items to Flag:**
- "Rapid deterioration" → needs operational definition
- "Clinically relevant comorbidities" → needs specific list
- "Willingness to comply" → mark as `non_rwd`
- "Central lab confirmation" → check if field exists

---

### 3. Deep Research Agent

**Role:** Resolve concept labels into dataset-specific codes and phenotype definitions.

**Input:** Criteria DSL with unresolved concepts
**Output:** ResolvedConcepts JSON

**Rules:**
- MUST call `get_catalog()` first to understand available data
- Use `search_concepts()` for code set proposals
- Use `resolve_units()` for unit conversions
- Do NOT write SQL
- Provide alternatives with pros/cons when multiple mappings exist
- For `needs_definition` items, propose 1-3 implementable definitions

**Concept Categories to Resolve:**
- Medication classes (ACEi/ARB, SGLT2i, MRA, GLP-1 RA, etc.)
- Lab tests (eGFR, HbA1c, proteinuria, anti-PLA2R, etc.)
- Diagnoses/phenotypes (T2DM, CKD, heart failure, nephrotic syndrome)
- Procedures (dialysis, transplant, biopsy)

---

### 4. Coding Agent

**Role:** Compile Criteria DSL + Resolved Concepts into executable SQL.

**Input:** 
- Criteria DSL JSON
- Resolved Concepts JSON
- Catalog (from `get_catalog()`)
- Optional: error messages from previous run

**Output:** SQLBundle JSON

**SQL Structure (MANDATORY):**
```sql
WITH
-- One CTE per predicate
p_I01 AS (...),
p_I02 AS (...),
p_E01 AS (...),
p_E02 AS (...),

-- Combine inclusion predicates (intersection)
included AS (
    SELECT person_id FROM p_I01
    INTERSECT
    SELECT person_id FROM p_I02
    -- ... all inclusion CTEs
),

-- Combine exclusion predicates (union)
excluded AS (
    SELECT person_id FROM p_E01
    UNION
    SELECT person_id FROM p_E02
    -- ... all exclusion CTEs
),

-- Final cohort
cohort AS (
    SELECT i.person_id, {index_date_logic} AS index_date
    FROM included i
    WHERE i.person_id NOT IN (SELECT person_id FROM excluded)
)

SELECT * FROM cohort;
```

**Rules (STRICT):**
- NEVER assume tables/columns not in `get_catalog()`
- NEVER hard-code clinical code lists; use resolved_concepts only
- ALWAYS derive index_date from anchor rules
- ALWAYS produce both `sql_cohort` and `sql_funnel_counts`
- Handle complex logic: two-measurement relationships, proportion rules, exposure duration
- On error: diagnose, repair with minimal changes, explain in repair_notes

---

### 5. SQL Runner/Validator Agent

**Role:** Execute SQL safely and validate results.

**Input:** SQL queries from Coding Agent
**Output:** Execution results or error diagnosis

**Execution Rules:**
- ALWAYS run in count-first mode before returning rows
- NEVER expose PHI in error messages or debug context

**Flag Conditions:**
| Condition | Action |
|-----------|--------|
| `syntax_error` | Return to Coding Agent for repair |
| `schema_error` | Return to Coding Agent for repair |
| `empty_cohort` (n=0) | Flag, suggest criteria revision |
| `huge_cohort` (n > threshold) | Flag, may need tighter criteria |
| `suspicious_drop` (>95% loss in one step) | Flag for review |

**Success Output:**
```typescript
{
  ok: true,
  execution_summary: { n: number, timing_ms?: number },
  funnel_steps: Array<{ step_name: string, n: number, pct_of_base: number }>,
  preview_rows: Array<any>  // Limited, de-identified
}
```

---

### 6. Receiver Agent

**Role:** Summarize final cohort and build funnel narrative.

**Input:** Final bundle (criteria, mappings, SQL, funnel counts, warnings)

**Output:**
1. **Executive Summary:** Cohort size, key drivers of inclusion/exclusion
2. **Funnel Narrative:** Where attrition happens, unexpected drops
3. **Data Quality Notes:** Central lab issues, missing fields, partial verifiability
4. **Validation Checklist:** What to manually verify next

---

## Required Tools/Functions

Every agent MUST use these tools rather than inventing data:

```python
def get_catalog() -> CatalogSchema:
    """
    Returns complete schema: tables, columns, data types, join keys, 
    row counts, and data dictionary descriptions.
    
    MUST be called before any SQL generation.
    """

def search_concepts(term: str, code_system: str = None) -> List[ConceptMatch]:
    """
    Search for clinical concepts by term.
    Returns candidate code sets with metadata.
    
    Args:
        term: Clinical concept to search (e.g., "metformin", "eGFR")
        code_system: Optional filter (ICD10CM, RxNorm, LOINC, etc.)
    
    Returns:
        List of matches with concept_id, code_system, description, 
        match_score, and related concepts.
    """

def resolve_units(test_name: str) -> UnitInfo:
    """
    Get known units and conversion rules for a lab test.
    
    Returns:
        Standard unit, alternative units, conversion formulas,
        or "cannot_convert" warning.
    """

def run_sql(sql: str, params: dict = None, mode: str = "count") -> ExecutionResult:
    """
    Execute SQL against the RWD warehouse.
    
    Args:
        sql: Query to execute
        params: Parameter values for parameterized queries
        mode: "count" (default, safe), "preview" (limited rows), "full"
    
    Returns:
        Row count, timing, preview rows (if mode allows), or error details.
    """

def explain_sql(sql: str) -> QueryPlan:
    """
    Get query execution plan for optimization.
    Optional but useful for complex queries.
    """

def save_artifact(name: str, payload: dict) -> ArtifactRef:
    """
    Persist criteria/SQL/funnel bundle for versioning and audit.
    
    Returns reference ID for retrieval.
    """
```

---

## Workflow Sequence

```
1. USER → Provides I/E criteria text

2. ORCHESTRATOR → Invokes IE_INTERPRETER
   └─ Output: Draft Criteria DSL + gaps list

3. ORCHESTRATOR → Invokes DEEP_RESEARCH (with Criteria DSL)
   └─ Deep Research calls: get_catalog(), search_concepts(), resolve_units()
   └─ Output: Resolved concepts + phenotype definitions

4. ORCHESTRATOR → Invokes CODING_AGENT (with DSL + Resolved Concepts)
   └─ Coding Agent calls: get_catalog()
   └─ Output: sql_cohort + sql_funnel_counts

5. ORCHESTRATOR → Invokes SQL_RUNNER (with SQL)
   └─ Runner calls: run_sql()
   └─ Output: Counts, funnel, or error

6. IF ERROR or EMPTY:
   └─ ORCHESTRATOR → Invokes CODING_AGENT for repair
   └─ OR → Suggests criteria edits to user
   └─ GOTO step 5

7. ORCHESTRATOR → Presents REPL output to user
   └─ User provides feedback / edits / approval

8. IF NOT APPROVED:
   └─ GOTO step 2 or 3 depending on change type

9. IF APPROVED:
   └─ ORCHESTRATOR → Handoff to RECEIVER_AGENT
   └─ Output: Final summary, funnel narrative, validation checklist
   └─ Call save_artifact() to persist bundle
```

---

## Hard Constraints (ALL AGENTS)

These rules are **non-negotiable** and must never be violated:

1. **No Hard-Coded Clinical Logic**
   - Never embed drug lists, diagnosis codes, lab values in prompts
   - All clinical mappings must come from tools or Deep Research Agent

2. **Schema-First**
   - Always call `get_catalog()` before generating or validating SQL
   - Never assume table/column existence

3. **Verifiability Classification**
   - Always classify criteria as `rwd`, `partial_rwd`, or `non_rwd`
   - Non-RWD criteria stay in funnel documentation but don't filter data

4. **Count-First Execution**
   - Never return full result sets before confirming counts
   - Protect against runaway queries

5. **Criteria DSL as Source of Truth**
   - All changes must update the DSL
   - Show diffs when DSL changes

6. **Minimal Assumptions**
   - Document every assumption explicitly
   - Prefer asking user over guessing

---

## Common Clinical Concepts Reference

This is a **reference only** - actual codes must come from `search_concepts()`:

| Concept Category | Examples |
|-----------------|----------|
| **Diabetes Drugs** | Metformin, SGLT2i (empagliflozin, dapagliflozin), GLP-1 RA (semaglutide, dulaglutide), DPP-4i, Insulin |
| **CV Drugs** | ACEi, ARB, Beta-blockers, MRA (spironolactone), Statins |
| **Renal** | Dialysis, Transplant, eGFR stages, Proteinuria, UACR |
| **Labs** | HbA1c, eGFR, Creatinine, LDL, ALT/AST, BNP |
| **Conditions** | T2DM, T1DM, CKD, Heart Failure, ASCVD, Hypertension |

---

## Error Handling Patterns

### SQL Syntax Error
```
Coding Agent: Diagnose error, fix syntax, return repair_notes
```

### Schema Error (missing table/column)
```
1. Coding Agent: Check get_catalog() output
2. If truly missing: Flag to user, suggest alternative or mark non_rwd
```

### Empty Cohort
```
1. SQL Runner: Flag empty_cohort
2. Orchestrator: Show funnel to identify where attrition happens
3. Suggest: Relax criteria at high-attrition step
```

### Suspicious Drop (>95% in one step)
```
1. SQL Runner: Flag suspicious_drop with step name
2. Orchestrator: Present to user for validation
3. May indicate: Data quality issue, overly strict criterion, coding error
```

---

## File Structure

```
ie-optimizer/
├── claude.md                    # This file - project guide
├── agents/
│   ├── orchestrator.py          # Main REPL controller
│   ├── ie_interpreter.py        # Text → DSL parser
│   ├── deep_research.py         # Concept resolver
│   ├── coding_agent.py          # SQL compiler
│   ├── sql_runner.py            # Query executor
│   └── receiver.py              # Summary generator
├── tools/
│   ├── catalog.py               # get_catalog() implementation
│   ├── concept_search.py        # search_concepts() implementation
│   ├── unit_resolver.py         # resolve_units() implementation
│   ├── sql_executor.py          # run_sql() implementation
│   └── artifact_store.py        # save_artifact() implementation
├── models/
│   ├── criteria_dsl.py          # Pydantic models for DSL
│   ├── resolved_concepts.py     # Concept resolution models
│   └── sql_bundle.py            # SQL output models
├── config/
│   ├── data_models/             # OMOP, Sentinel, PCORnet schemas
│   └── prompts/                 # Agent system prompts
└── tests/
    ├── test_ie_interpreter.py
    ├── test_concept_resolution.py
    └── test_sql_generation.py
```

---

## Development Guidelines

### When Adding New Features
1. Update Criteria DSL schema if new predicate types needed
2. Update Deep Research Agent if new concept categories
3. Update Coding Agent SQL patterns if new query logic
4. Add tests for new paths

### When Debugging
1. Check Criteria DSL state at each step
2. Verify `get_catalog()` returns expected schema
3. Check `search_concepts()` returns for concept resolution
4. Examine CTE-by-CTE in SQL for logic errors

### When Optimizing
1. Use `explain_sql()` for query plan analysis
2. Consider materializing common CTEs
3. Check index usage on join columns

---

## Example Session

```
USER: Here are my I/E criteria for a T2DM study:

Inclusion:
- Adults 18-75 years
- Diagnosis of T2DM in past 12 months
- HbA1c ≥7.0% and ≤10.0%
- On stable metformin dose for ≥90 days

Exclusion:
- Type 1 diabetes
- eGFR <30 mL/min
- History of pancreatitis
- Pregnant or nursing

---

ORCHESTRATOR: Processing criteria...

[Invokes IE_INTERPRETER]
→ Parsed 4 inclusion, 4 exclusion predicates
→ Gaps identified: "stable dose" needs definition

[Invokes DEEP_RESEARCH]
→ Resolved: T2DM → ICD10CM E11.%
→ Resolved: HbA1c → LOINC 17856-6, 4548-4
→ Resolved: Metformin → RxNorm 1503297 descendants
→ Resolved: eGFR → LOINC 98979-8, 77147-7
→ Proposed: "stable dose" = no dose change in window (requires dose field)

[Invokes CODING_AGENT]
→ Generated sql_cohort with 8 CTEs
→ Generated sql_funnel_counts

[Invokes SQL_RUNNER]
→ Base population: 1,245,678
→ After I01 (Age): 892,456
→ After I02 (T2DM): 156,789
→ After I03 (HbA1c): 45,678
→ After I04 (Metformin): 23,456
→ After E01 (T1DM): 23,012
→ After E02 (eGFR): 21,890
→ After E03 (Pancreatitis): 21,456
→ After E04 (Pregnancy): 21,234
→ Final cohort: 21,234

═══════════════════════════════════════════════════════
WARNINGS / UNVERIFIABLE GATES
═══════════════════════════════════════════════════════
- "Stable dose" approximated as continuous metformin fills
- Pregnancy detection limited to diagnosis codes (no lab confirmation)

═══════════════════════════════════════════════════════
NEXT ACTION
═══════════════════════════════════════════════════════
Cohort of 21,234 patients identified. 
- Major attrition at HbA1c step (65% drop) - verify lab coverage
- Ready to finalize or adjust criteria?

USER: Looks good, finalize it.

[Handoff to RECEIVER]
→ Executive summary generated
→ Funnel narrative created
→ Artifact saved: study_t2dm_v1_20250615
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01 | Initial architecture |

---

## Contact & Ownership

**Project:** RWE I/E Optimizer  
**Domain:** Clinical Trial Feasibility & Cohort Identification  
**Data Models Supported:** OMOP CDM, Sentinel, PCORnet, Custom