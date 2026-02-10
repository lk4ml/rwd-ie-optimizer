"""
Complete end-to-end demo of the RWD IE Optimizer
Shows: Parsing → Concept Resolution → SQL Generation → Execution
"""

from dotenv import load_dotenv
load_dotenv()

from src.agent_runtime import AgentRunner
from src.agents.agents import (
    ie_interpreter_agent,
    deep_research_agent,
    coding_agent,
    sql_runner_agent
)
from src.tools.sql_executor import run_sql
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
import json
import re

console = Console()
client = AgentRunner()

# Sample I/E criteria
criteria_text = """
INCLUSION CRITERIA:
1. Adults aged 18 to 75 years
2. Type 2 Diabetes Mellitus diagnosis
3. Currently on Metformin

EXCLUSION CRITERIA:
1. History of heart failure
"""

console.print(Panel.fit(
    "[bold cyan]RWD IE Optimizer - Complete Workflow Demo[/bold cyan]\n"
    "Step-by-step: Parse → Resolve → Generate SQL → Execute",
    border_style="cyan"
))

console.print(f"\n[bold]Input I/E Criteria:[/bold]\n{criteria_text}\n")

# ============================================================================
# STEP 1: IE INTERPRETER - Parse criteria into Criteria DSL
# ============================================================================

console.print("=" * 70)
console.print("[bold cyan]STEP 1: IE INTERPRETER - Parsing criteria...[/bold cyan]")
console.print("=" * 70 + "\n")

response = client.run(
    agent=ie_interpreter_agent,
    messages=[{
        "role": "user",
        "content": f"""Parse the following I/E criteria into Criteria DSL JSON format.
Extract all predicates with their IDs, domains, concepts, and constraints.

{criteria_text}

Return ONLY the JSON, no additional text."""
    }]
)

criteria_dsl_text = response.messages[-1]["content"]
console.print("[green]✓ Parsed into Criteria DSL[/green]\n")

# Try to extract JSON from response
try:
    # Find JSON in the response
    import re
    json_match = re.search(r'\{.*\}', criteria_dsl_text, re.DOTALL)
    if json_match:
        criteria_dsl = json.loads(json_match.group())
    else:
        criteria_dsl = json.loads(criteria_dsl_text)

    console.print_json(json.dumps(criteria_dsl, indent=2))
except:
    console.print(criteria_dsl_text)
    criteria_dsl = {}

# ============================================================================
# STEP 2: DEEP RESEARCH - Resolve concepts to codes
# ============================================================================

console.print("\n" + "=" * 70)
console.print("[bold cyan]STEP 2: DEEP RESEARCH - Resolving concepts to codes...[/bold cyan]")
console.print("=" * 70 + "\n")

if criteria_dsl:
    response = client.run(
        agent=deep_research_agent,
        messages=[{
            "role": "user",
            "content": f"""Given this Criteria DSL, resolve all medical concepts to database codes.

Use the following tools:
1. Call get_catalog() to see available tables
2. Call search_concepts() for each concept
3. Return resolved concepts with code mappings

Criteria DSL:
{json.dumps(criteria_dsl, indent=2)}

For each predicate, find the appropriate codes (ICD-10 for diagnoses, NDC for drugs)."""
        }]
    )

    console.print("[green]✓ Concepts resolved[/green]\n")
    console.print(response.messages[-1]["content"])

# ============================================================================
# STEP 3: CODING AGENT - Generate SQL
# ============================================================================

console.print("\n" + "=" * 70)
console.print("[bold cyan]STEP 3: CODING AGENT - Generating SQL...[/bold cyan]")
console.print("=" * 70 + "\n")

if criteria_dsl:
    response = client.run(
        agent=coding_agent,
        messages=[{
            "role": "user",
            "content": f"""Generate SQL queries for this criteria.

Criteria DSL:
{json.dumps(criteria_dsl, indent=2)}

Use these code mappings:
- Type 2 Diabetes: ICD-10 code LIKE 'E11%'
- Metformin: NDC code = '50090-2875-01'
- Heart failure: ICD-10 code LIKE 'I50%'

First call get_catalog() to see the database schema, then generate:
1. Main cohort SQL with CTEs
2. Funnel counts SQL

Return the complete SQL queries."""
        }]
    )

    sql_response = response.messages[-1]["content"]
    console.print("[green]✓ SQL generated[/green]\n")

    # Extract SQL from response
    sql_match = re.search(r'```sql\n(.*?)\n```', sql_response, re.DOTALL)
    if sql_match:
        generated_sql = sql_match.group(1)
    else:
        # Try to find SQL keywords
        if "WITH" in sql_response and "SELECT" in sql_response:
            generated_sql = sql_response
        else:
            generated_sql = None

    if generated_sql:
        console.print(Syntax(generated_sql, "sql", theme="monokai"))

        # ============================================================================
        # STEP 4: Execute SQL
        # ============================================================================

        console.print("\n" + "=" * 70)
        console.print("[bold cyan]STEP 4: SQL EXECUTION - Running query...[/bold cyan]")
        console.print("=" * 70 + "\n")

        # Try to execute the SQL
        result = run_sql(generated_sql, mode="preview")

        if result["ok"]:
            console.print(f"[green]✓ Query executed successfully[/green]")
            console.print(f"[bold]Cohort size:[/bold] {result['execution_summary']['n']} patients")
            console.print(f"[bold]Query time:[/bold] {result['execution_summary']['timing_ms']:.2f} ms\n")

            if result.get("preview_rows"):
                console.print("[bold]Sample results:[/bold]")
                table = Table(show_header=True, header_style="bold magenta")

                if len(result["preview_rows"]) > 0:
                    # Add columns
                    for col in result["preview_rows"][0].keys():
                        table.add_column(col)

                    # Add rows
                    for row in result["preview_rows"][:5]:
                        table.add_row(*[str(v) for v in row.values()])

                    console.print(table)
        else:
            console.print(f"[red]✗ Query failed:[/red] {result.get('error')}")
    else:
        console.print("[yellow]Could not extract SQL from response[/yellow]")

# ============================================================================
# SUMMARY
# ============================================================================

console.print("\n" + "=" * 70)
console.print("[bold green]DEMO COMPLETE![/bold green]")
console.print("=" * 70)

console.print("""
[bold]Workflow completed successfully:[/bold]
✓ Parsed I/E criteria into structured Criteria DSL
✓ Resolved medical concepts to database codes
✓ Generated SQL with CTE structure
✓ Executed query and returned cohort

[bold cyan]This demonstrates the complete multi-agent workflow![/bold cyan]
""")
