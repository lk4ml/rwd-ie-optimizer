"""
Demo run of the RWD IE Optimizer system
"""

from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from swarm import Swarm
from src.agents.agents import orchestrator_agent
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
import json

console = Console()

def display_section(title, content, syntax_type=None):
    """Display a formatted section"""
    console.print(f"\n{'=' * 70}")
    console.print(f"[bold cyan]{title}[/bold cyan]")
    console.print(f"{'=' * 70}")

    if syntax_type:
        console.print(Syntax(content, syntax_type, theme="monokai"))
    elif isinstance(content, dict):
        console.print_json(json.dumps(content, indent=2))
    else:
        console.print(content)

# Sample I/E criteria
sample_criteria = """
STUDY: Type 2 Diabetes with CKD Study

INCLUSION CRITERIA:
1. Adults aged 18 to 75 years
2. Type 2 Diabetes Mellitus diagnosis
3. Currently on Metformin therapy

EXCLUSION CRITERIA:
1. History of heart failure
2. Active cancer diagnosis
"""

console.print(Panel.fit(
    "[bold cyan]RWD IE Optimizer - Demo Run[/bold cyan]\n"
    "Powered by OpenAI Agent SDK (Swarm)",
    border_style="cyan"
))

console.print("\n[bold]Sample I/E Criteria:[/bold]")
console.print(sample_criteria)

console.print("\n[bold cyan]Starting multi-agent workflow...[/bold cyan]\n")

# Initialize Swarm client
client = Swarm()

# Initial message
messages = [
    {
        "role": "user",
        "content": f"""I need help converting the following clinical trial I/E criteria into SQL over our RWD database.

Please follow this workflow:
1. Parse the criteria into Criteria DSL JSON format
2. Resolve medical concepts to database codes using search_concepts()
3. Generate SQL queries for cohort identification
4. Show me the results

Here are the I/E criteria:

{sample_criteria}

Please start by parsing these criteria into structured Criteria DSL format. Extract all predicates with their domains, concepts, and constraints."""
    }
]

context = {
    "criteria_dsl": {},
    "resolved_concepts": {},
    "sql_cohort": "",
    "finalized": False
}

try:
    console.print("[dim]Running orchestrator agent...[/dim]\n")

    # Run the orchestrator
    response = client.run(
        agent=orchestrator_agent,
        messages=messages,
        context_variables=context
    )

    # Display response
    if hasattr(response, 'messages'):
        for msg in response.messages:
            if msg.get("role") == "assistant" and msg.get("content"):
                console.print("[bold green]Agent Response:[/bold green]")
                console.print(msg["content"])
                console.print()

    # Update context
    if hasattr(response, 'context_variables'):
        context.update(response.context_variables)

    # Display results
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]WORKFLOW RESULTS[/bold cyan]")
    console.print("=" * 70)

    if context.get("criteria_dsl"):
        display_section("Criteria DSL (Structured Format)", context["criteria_dsl"])

    if context.get("resolved_concepts"):
        display_section("Resolved Concepts", context["resolved_concepts"])

    if context.get("sql_cohort"):
        display_section("Generated SQL", context["sql_cohort"], "sql")

    console.print("\n[bold green]✓ Demo completed successfully![/bold green]")

except Exception as e:
    console.print(f"\n[bold red]Error:[/bold red] {e}")
    import traceback
    console.print(traceback.format_exc())
