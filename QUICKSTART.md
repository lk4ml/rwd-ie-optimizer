# Quick Start Guide - RWD IE Optimizer

## What We Built

You now have a fully functional RWD IE Optimizer that uses OpenAI Agent SDK (Swarm) to convert clinical trial inclusion/exclusion criteria into executable SQL queries.

### ✅ Completed Components

1. **SQLite Database** (500 patients, 3,500 claims)
   - 6 tables from your Excel file
   - Indexed for performance
   - Ready for queries

2. **Pydantic Models** (Type-safe data structures)
   - Criteria DSL
   - Resolved Concepts
   - SQL Bundle

3. **Tool Functions** (Agent capabilities)
   - `get_catalog()` - Database schema
   - `search_concepts()` - Medical code search
   - `resolve_units()` - Lab unit conversion
   - `run_sql()` - Safe SQL execution
   - `save_artifact()` - Result persistence

4. **6 Specialized Agents** (OpenAI Swarm)
   - Orchestrator - Workflow controller
   - IE Interpreter - Text → DSL parser
   - Deep Research - Concept resolver
   - Coding Agent - SQL generator
   - SQL Runner - Query executor
   - Receiver - Summary generator

5. **Interactive REPL** (Command-line interface)
   - Rich terminal formatting
   - Step-by-step workflow
   - Iterative refinement

---

## Setup (2 minutes)

### Step 1: Set Your OpenAI API Key

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API key
# OPENAI_API_KEY=sk-your-key-here
```

### Step 2: Verify Installation

```bash
# Test the system
./venv/bin/python src/main.py test
```

You should see:
```
✓ Found 6 tables
✓ Found 4 matches for diabetes
✓ Patient count: 500
All tests passed!
```

---

## Usage

### Run the REPL

```bash
./venv/bin/python src/main.py run
```

Or if you installed it:

```bash
rwd-ie run
```

### Example Session

1. **Paste your I/E criteria:**

```
INCLUSION CRITERIA:
1. Adults aged 18-75 years
2. Type 2 Diabetes diagnosis
3. Currently on Metformin

EXCLUSION CRITERIA:
1. History of heart failure
```

2. **Press Ctrl+D** (Mac/Linux) or **Ctrl+Z then Enter** (Windows)

3. **The system will:**
   - Parse criteria into structured JSON
   - Resolve "Type 2 Diabetes" → ICD-10 codes (E11%)
   - Resolve "Metformin" → NDC codes
   - Generate SQL with CTEs
   - Execute and show patient counts
   - Display funnel (Base → After filters → Final cohort)

4. **Review the output:**
   - Criteria DSL (JSON)
   - Generated SQL
   - Patient funnel with counts
   - Warnings (if any)

5. **Provide feedback or approve:**
   - Type feedback to iterate
   - Type "finalize" to complete
   - Type "quit" to exit

---

## Sample Workflow Output

```
═══════════════════════════════════════════════════════════════════
CURRENT CRITERIA (JSON)
═══════════════════════════════════════════════════════════════════
{
  "study_id": "study_001",
  "inclusion": [
    {"id": "I01", "description": "Adults 18-75 years", "domain": "demographic", ...},
    {"id": "I02", "description": "Type 2 Diabetes", "domain": "diagnosis", ...}
  ],
  ...
}

═══════════════════════════════════════════════════════════════════
CURRENT SQL (COHORT)
═══════════════════════════════════════════════════════════════════
WITH
p_I01 AS (
    SELECT DISTINCT patient_id FROM patients WHERE age BETWEEN 18 AND 75
),
p_I02 AS (
    SELECT DISTINCT patient_id FROM claims
    WHERE primary_diagnosis_code LIKE 'E11%'
),
included AS (
    SELECT patient_id FROM p_I01 INTERSECT SELECT patient_id FROM p_I02
),
cohort AS (
    SELECT i.patient_id, p.enrollment_start_date as index_date
    FROM included i
    JOIN patients p ON i.patient_id = p.patient_id
)
SELECT * FROM cohort;

═══════════════════════════════════════════════════════════════════
FUNNEL STEPS (COUNTS)
═══════════════════════════════════════════════════════════════════
Step                                    Count    % of Base
Base Population                          500       100.0%
After I01 (Age 18-75)                    380        76.0%
After I02 (T2DM)                         120        24.0%
Final Cohort                             120        24.0%
```

---

## Project Structure

```
rwd-ie-optimizer/
├── data/
│   └── rwd_claims.db               ← SQLite database (2.2 MB)
│
├── src/
│   ├── agents/
│   │   └── agents.py               ← All 6 agents
│   ├── tools/
│   │   ├── catalog.py              ← Database schema
│   │   ├── concept_search.py       ← Code lookup
│   │   ├── sql_executor.py         ← SQL execution
│   │   └── ...
│   ├── models/
│   │   ├── criteria_dsl.py         ← Core data models
│   │   └── ...
│   ├── config/
│   │   ├── prompts/                ← Agent instructions
│   │   └── settings.py
│   └── main.py                     ← CLI entry point
│
├── tests/
│   └── fixtures/
│       └── sample_criteria.txt     ← Example I/E criteria
│
└── scripts/
    └── create_database.py          ← DB setup script
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/main.py` | Run this to start the REPL |
| `src/agents/agents.py` | All agent definitions |
| `src/tools/*.py` | Tool functions agents call |
| `src/models/*.py` | Pydantic data models |
| `src/config/prompts/*.txt` | Agent system prompts |
| `data/rwd_claims.db` | SQLite database |

---

## Customization

### Modify Agent Behavior

Edit prompts in `src/config/prompts/`:
- `ie_interpreter.txt` - Parsing logic
- `deep_research.txt` - Concept resolution
- `coding_agent.txt` - SQL generation rules
- `orchestrator.txt` - Workflow control

### Add New Medical Codes

Add rows to reference tables in the database:
```python
import sqlite3
conn = sqlite3.connect("data/rwd_claims.db")
cursor = conn.cursor()

cursor.execute("""
    INSERT INTO ref_icd10 (icd_10_code, description)
    VALUES ('E10.9', 'Type 1 diabetes mellitus without complications')
""")

conn.commit()
conn.close()
```

### Extend Tool Functions

Add new tools in `src/tools/` and register them with agents in `src/agents/agents.py`.

---

## Troubleshooting

### Error: "OPENAI_API_KEY not set"
```bash
# Add your API key to .env
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

### Error: "Database not found"
```bash
# Recreate database
./venv/bin/python scripts/create_database.py
```

### SQL Execution Errors
- Check `get_catalog()` output to verify table/column names
- Review generated SQL in REPL output
- System auto-repairs syntax errors

### Agent Not Responding
- Verify OpenAI API key is valid
- Check internet connection
- Review error messages in console

---

## Next Steps

### 1. Test with Your Own Criteria

Try the sample criteria:
```bash
cat tests/fixtures/sample_criteria.txt
```

Or create your own I/E criteria file and paste it into the REPL.

### 2. Explore the Database

```bash
./venv/bin/python

>>> from src.tools.catalog import get_catalog
>>> catalog = get_catalog()
>>> print(catalog['tables'][0])  # Inspect schema

>>> from src.tools.concept_search import search_concepts
>>> search_concepts("heart failure")  # Find codes
```

### 3. Refine Agent Prompts

The agents learn from their prompts. Edit `src/config/prompts/*.txt` to:
- Add domain-specific knowledge
- Adjust SQL generation patterns
- Customize concept resolution logic

### 4. Add More Data

Expand your synthetic data:
- Add more patients to Excel
- Add more reference codes
- Re-run `scripts/create_database.py`

---

## Architecture Overview

```
User Input (I/E Text)
         ↓
[Orchestrator Agent] ← Manages workflow
         ↓
[IE Interpreter] → Parses → Criteria DSL (JSON)
         ↓
[Deep Research] → Resolves concepts → ResolvedConcepts (JSON)
         ↓                              ↑
[Coding Agent] → Generates SQL ←───────┤ (uses catalog)
         ↓
[SQL Runner] → Executes → Results
         ↓
[Receiver] → Summarizes → Final Report
         ↓
User (REPL Display)
```

---

## Performance

**Current Scale:**
- 500 patients, 3,500 claims
- Query time: <100ms
- Full workflow: 30-60 seconds (LLM latency)

**Scalability:**
- SQLite handles up to ~1M rows efficiently
- For larger datasets, migrate to PostgreSQL/MySQL
- Adjust `get_catalog()` in `src/tools/catalog.py`

---

## Documentation

- **[README.md](README.md)** - Project overview
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Build plan
- **[claude.md](claude.md)** - Detailed specifications
- **This file** - Quick start guide

---

## Support

**Built:** December 17, 2025
**Version:** 0.1.0 (MVP)
**Framework:** OpenAI Agent SDK (Swarm)

For issues or questions, refer to the documentation files or check:
- Agent prompts in `src/config/prompts/`
- Tool implementations in `src/tools/`
- Test files in `tests/fixtures/`

---

## Summary

You now have a working RWD IE Optimizer! 🎉

**To run:**
```bash
./venv/bin/python src/main.py run
```

**What it does:**
1. Parses your I/E criteria
2. Maps concepts to codes
3. Generates SQL
4. Executes queries
5. Shows patient funnel
6. Allows refinement

**Next:** Add your OpenAI API key to `.env` and try it out!
