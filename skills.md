---
name: rwd-patient-funnel
description: |
  Translates clinical trial inclusion/exclusion criteria into executable SQL queries for real-world data (RWD) patient funnels. Use when: (1) Converting I/E criteria text to SQL, (2) Building patient cohort funnels, (3) Estimating eligible patient counts from claims/EHR data, (4) Generating attrition tables, (5) Working with OMOP CDM, Sentinel, PCORnet, or custom RWD schemas. Supports temporal logic, lookback windows, code mappings (ICD/CPT/NDC/LOINC), and stepwise funnel visualization.
---

# RWD Patient Funnel SQL Generator

Generates SQL from clinical I/E criteria for patient cohort identification in real-world databases.

## Core Workflow

### Step 1: Parse Criteria into Structured Components

Transform free-text I/E criteria into structured criterion objects:

```yaml
criterion:
  id: "I01"
  type: "inclusion" | "exclusion"
  domain: "diagnosis" | "procedure" | "drug" | "lab" | "demographic" | "enrollment" | "observation"
  concept: "Type 2 Diabetes"
  codes:
    system: "ICD10CM"
    values: ["E11.%"]
  temporal:
    reference: "index_date" | "enrollment_start" | "first_diagnosis"
    window: 
      before: 365  # days
      after: 0
  logic: "any" | "all" | "count>=N"
  count_threshold: null  # for count-based criteria
```

### Step 2: Identify Index Event

Determine patient anchor point before applying criteria:

| Index Type | Description | SQL Pattern |
|------------|-------------|-------------|
| `first_diagnosis` | First occurrence of qualifying dx | `MIN(condition_start_date)` |
| `first_drug` | First dispensing of study drug | `MIN(drug_exposure_start_date)` |
| `enrollment_start` | Insurance enrollment begin | `MIN(enrollment_start_date)` |
| `custom_event` | Protocol-defined event | User-specified |

### Step 3: Generate SQL Building Blocks

Each criterion maps to a CTE (Common Table Expression):

```sql
-- Pattern: Criterion CTE
WITH criterion_{id} AS (
    SELECT DISTINCT person_id
    FROM {domain_table}
    WHERE {code_filter}
      AND {temporal_filter}
      AND {additional_logic}
)
```

### Step 4: Assemble Funnel Query

Combine CTEs with sequential filtering:

```sql
WITH 
-- Base population
base_population AS (...),

-- Index date assignment
index_dates AS (...),

-- Inclusion criteria (INNER JOIN = must have)
inc_01 AS (...),
inc_02 AS (...),

-- Exclusion criteria (LEFT JOIN + IS NULL = must not have)
exc_01 AS (...),

-- Final cohort assembly
final_cohort AS (
    SELECT b.person_id, i.index_date
    FROM base_population b
    INNER JOIN index_dates i ON b.person_id = i.person_id
    INNER JOIN inc_01 ON b.person_id = inc_01.person_id
    INNER JOIN inc_02 ON b.person_id = inc_02.person_id
    LEFT JOIN exc_01 ON b.person_id = exc_01.person_id
    WHERE exc_01.person_id IS NULL
)

-- Attrition counts
SELECT 'Base Population' AS step, COUNT(DISTINCT person_id) AS n FROM base_population
UNION ALL
SELECT 'After Inc 01', COUNT(DISTINCT person_id) FROM base_population 
    INNER JOIN inc_01 USING (person_id)
-- ... continue for each step
```

## Domain-to-Table Mapping

Reference `references/data-models.md` for schema-specific mappings:

| Domain | OMOP CDM | Sentinel | PCORnet |
|--------|----------|----------|---------|
| Diagnosis | condition_occurrence | diagnosis | diagnosis |
| Procedure | procedure_occurrence | procedure | procedures |
| Drug | drug_exposure | dispensing | dispensing |
| Lab | measurement | lab_result_cm | lab_result_cm |
| Demographics | person | demographic | demographic |
| Enrollment | observation_period | enrollment | enrollment |

## Code System Reference

See `references/clinical-concepts.md` for code mapping patterns:

| Concept Type | Code Systems | Wildcard Support |
|--------------|--------------|------------------|
| Diagnosis | ICD-9-CM, ICD-10-CM, SNOMED | Yes (`E11.%`) |
| Procedure | CPT, HCPCS, ICD-10-PCS | Yes |
| Drug | NDC, RxNorm, ATC | NDC: first 9 digits |
| Lab | LOINC | No |

## Temporal Logic Patterns

```sql
-- Lookback window (N days before index)
WHERE event_date BETWEEN DATE_ADD(index_date, INTERVAL -{lookback} DAY) 
                     AND index_date

-- Washout period (no events in window)
WHERE NOT EXISTS (
    SELECT 1 FROM events e2 
    WHERE e2.person_id = e1.person_id
      AND e2.event_date BETWEEN ... AND ...
)

-- Persistent use (continuous exposure)
WHERE exposure_days >= {min_days}
  AND gap_days <= {max_gap}
```

## SQL Dialect Considerations

Adjust syntax for target database:

| Function | BigQuery | Snowflake | Redshift | SQL Server |
|----------|----------|-----------|----------|------------|
| Date diff | DATE_DIFF(d1,d2,DAY) | DATEDIFF('day',d2,d1) | DATEDIFF(day,d2,d1) | DATEDIFF(day,d2,d1) |
| Date add | DATE_ADD(d, INTERVAL n DAY) | DATEADD(day,n,d) | DATEADD(day,n,d) | DATEADD(day,n,d) |
| Wildcard | LIKE 'E11%' | LIKE 'E11%' | LIKE 'E11%' | LIKE 'E11%' |

## Output Artifacts

1. **Structured Criteria JSON** - Machine-readable criterion definitions
2. **SQL Query** - Executable funnel query with CTEs
3. **Attrition Table Query** - Step-by-step patient counts
4. **Criteria Documentation** - Human-readable logic description

## Critical Rules

1. **Always qualify dates** - Every clinical event must have temporal bounds relative to index
2. **Handle code hierarchies** - Use wildcards for ICD parent codes (E11.% captures E11.0, E11.1, etc.)
3. **Account for data latency** - RWD has 30-90 day claims lag; adjust study periods
4. **Validate code mappings** - Cross-reference codes with concept sets before deployment
5. **Document assumptions** - Every criterion should have clear clinical rationale

## Reference Files

- `references/data-models.md` - Detailed schema for OMOP, Sentinel, PCORnet
- `references/clinical-concepts.md` - Code mapping patterns and concept set examples
- `references/sql-patterns.md` - Reusable SQL templates for common criteria types
- `scripts/criteria_parser.py` - Parse free-text criteria to structured format
- `scripts/sql_generator.py` - Generate SQL from structured criteria