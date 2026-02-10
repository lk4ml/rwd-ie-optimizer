# RWD IE Optimizer

Convert clinical trial inclusion/exclusion criteria into executable SQL queries over Real-World Data.

## Overview

This system uses a multi-agent architecture powered by the OpenAI SDK (tool-calling) via an internal agent runtime to transform natural language clinical trial eligibility criteria into validated SQL queries and patient funnels.

### Key Features

- 📝 **Natural Language Input** - Paste I/E criteria as plain text
- 🤖 **Multi-Agent Processing** - 6 specialized agents handle parsing, concept resolution, SQL generation, and validation
- 🔍 **Concept Resolution** - Automatic mapping to ICD-10, CPT, NDC codes
- 💾 **SQLite Backend** - Synthetic RWD claims database (500 patients, 3,500 claims)
- 📊 **Patient Funnels** - Step-by-step attrition analysis
- 🔄 **Iterative Refinement** - Interactive REPL for criteria adjustments
- ✅ **Validation** - Automatic SQL error detection and repair

## Architecture

```
User I/E Text
     ↓
AI Service (Pipeline Orchestrator)
     ↓
IE Interpreter Agent → Criteria DSL JSON
     ↓
Deep Research Agent → Concept Resolution
     ↓
Coding Agent → SQL Generation
     ↓
SQL Runner Agent → Query Execution
     ↓
Receiver Agent → Summary & Funnel
```

## Installation

### Prerequisites

- Python 3.11 or higher
- OpenAI API key

### Setup

1. **Clone the repository**
   ```bash
   cd /path/to/RWD_IE_FUNNEL_OPTIMIZER
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

5. **Create database** (already done if following from start)
   ```bash
   python scripts/create_database.py
   ```

## Quick Start

### Run the REPL

```bash
python src/main.py run
```

Or using the installed script:

```bash
rwd-ie run
```

### Example Session

```
Paste your I/E criteria below (press Ctrl+D when done):

INCLUSION CRITERIA:
1. Adults aged 18-75 years
2. Type 2 Diabetes Mellitus diagnosis in past 5 years
3. eGFR 30-59 mL/min/1.73m² (CKD Stage 3-4)

EXCLUSION CRITERIA:
1. History of heart failure
2. Active cancer diagnosis
^D

[System processes and displays:]
- Parsed criteria DSL
- Resolved concepts to codes
- Generated SQL queries
- Executed and returned funnel counts
```

## Project Structure

```
rwd-ie-optimizer/
├── data/
│   └── rwd_claims.db           # SQLite database
├── src/
│   ├── agents/                 # 6 specialized agents
│   │   ├── orchestrator.py
│   │   ├── ie_interpreter.py
│   │   ├── deep_research.py
│   │   ├── coding_agent.py
│   │   ├── sql_runner.py
│   │   └── receiver.py
│   ├── tools/                  # Agent functions
│   │   ├── catalog.py          # get_catalog()
│   │   ├── concept_search.py   # search_concepts()
│   │   ├── unit_resolver.py    # resolve_units()
│   │   ├── sql_executor.py     # run_sql()
│   │   └── artifact_store.py   # save_artifact()
│   ├── models/                 # Pydantic schemas
│   │   ├── criteria_dsl.py
│   │   ├── resolved_concepts.py
│   │   └── sql_bundle.py
│   ├── config/
│   │   ├── prompts/            # Agent system prompts
│   │   └── settings.py
│   ├── utils/
│   └── main.py                 # CLI entry point
├── scripts/
│   └── create_database.py
├── tests/
└── examples/
```

## Database Schema

The synthetic RWD database contains:

| Table | Rows | Description |
|-------|------|-------------|
| `patients` | 500 | Demographics and enrollment |
| `claims` | 3,500 | Diagnoses, procedures, drugs |
| `ref_icd10` | 29 | ICD-10 code reference |
| `ref_cpt` | 19 | CPT code reference |
| `ref_ndc` | 10 | NDC drug code reference |
| `data_dictionary` | 45 | Metadata |

## Core Concepts

### Criteria DSL

The system converts I/E text into a structured JSON format (Criteria DSL) that serves as the single source of truth throughout the workflow.

**Example:**
```json
{
  "study_id": "trial_001",
  "version": "1.0",
  "inclusion": [
    {
      "id": "I01",
      "description": "Adults aged 18-75 years",
      "domain": "demographic",
      "concept": "age",
      "value_constraint": {
        "operator": "between",
        "value": [18, 75]
      },
      "verifiability": "rwd"
    }
  ],
  "exclusion": [...]
}
```

### Concept Resolution

Medical concepts are mapped to database codes:

| Concept | Code System | Example Codes |
|---------|-------------|---------------|
| Type 2 Diabetes | ICD-10-CM | E11.% |
| Metformin | NDC | 50090-2875-01 |
| Office Visit | CPT | 99213, 99214 |

### SQL Generation

The Coding Agent generates CTE-based SQL with this structure:

```sql
WITH
-- One CTE per predicate
p_I01 AS (SELECT DISTINCT patient_id FROM patients WHERE age BETWEEN 18 AND 75),
p_I02 AS (SELECT DISTINCT patient_id FROM claims WHERE primary_diagnosis_code LIKE 'E11%'),

-- Combine inclusion criteria
included AS (
    SELECT patient_id FROM p_I01
    INTERSECT
    SELECT patient_id FROM p_I02
),

-- Combine exclusion criteria
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

## Development

### Running Tests

```bash
pytest tests/
```

### Adding New Agents

See `src/agents/` for examples of agent implementation using the internal agent runtime.

### Extending Concept Mappings

Add new code mappings to the reference tables in the database or extend `src/tools/concept_search.py`.

## Configuration

Environment variables (`.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `MODEL_DEFAULT` | Default GPT model | gpt-4o |
| `MODEL_RESEARCH` | Research agent model | gpt-4-turbo |
| `DATABASE_PATH` | SQLite database path | data/rwd_claims.db |
| `LOG_LEVEL` | Logging level | INFO |

## Documentation

- **[CLAUDE.md](claude.md)** - Comprehensive project guide and specifications
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Detailed build plan
- **[skills.md](skills.md)** - Skill definitions and workflows

## Troubleshooting

### Database not found
```bash
python scripts/create_database.py
```

### OpenAI API errors
Check that your API key is set in `.env` and has sufficient credits.

### SQL errors
The system attempts automatic repair. Check the REPL output for specific error messages.

## License

Internal use only.

## Contributing

This is a prototype system. For questions or enhancements, contact the development team.

---

**Version:** 0.1.0
**Last Updated:** December 17, 2025
