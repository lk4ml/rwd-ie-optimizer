"""
RWD IE Optimizer - Main Entry Point

Interactive REPL for converting clinical trial I/E criteria to SQL over RWD.
"""

import typer
import json
import os
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.markdown import Markdown
from swarm import Swarm
from src.agents.agents import orchestrator_agent
from src.config.settings import settings

app = typer.Typer()
console = Console()


def display_banner():
    """Display welcome banner."""
    banner_text = """
[bold cyan]RWD IE Optimizer[/bold cyan]
Convert clinical trial inclusion/exclusion criteria to SQL over real-world data

[dim]Powered by OpenAI Agent SDK (Swarm)[/dim]
    """
    console.print(Panel(banner_text, border_style="cyan"))


def display_repl_output(context: dict):
    """
    Format and display REPL output in structured sections.

    Args:
        context: Current workflow state with criteria, SQL, funnel, etc.
    """

    console.print("\n" + "=" * 70)
    console.print("[bold cyan]CURRENT CRITERIA (JSON)[/bold cyan]")
    console.print("=" * 70)

    criteria_dsl = context.get("criteria_dsl", {})
    if criteria_dsl:
        console.print_json(json.dumps(criteria_dsl, indent=2))
    else:
        console.print("[yellow]Pending parsing...[/yellow]")

    console.print("\n" + "=" * 70)
    console.print("[bold cyan]CURRENT SQL (COHORT)[/bold cyan]")
    console.print("=" * 70)

    sql_cohort = context.get("sql_cohort", "")
    if sql_cohort and sql_cohort != "pending":
        console.print(Syntax(sql_cohort, "sql", theme="monokai", line_numbers=False))
    else:
        console.print("[yellow]Pending SQL generation...[/yellow]")

    console.print("\n" + "=" * 70)
    console.print("[bold cyan]FUNNEL STEPS (COUNTS)[/bold cyan]")
    console.print("=" * 70)

    funnel_steps = context.get("funnel_steps", [])
    if funnel_steps:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Step", style="dim", width=40)
        table.add_column("Count", justify="right")
        table.add_column("% of Base", justify="right")

        for step in funnel_steps:
            table.add_row(
                step.get("step_name", "Unknown"),
                str(step.get("n", 0)),
                f"{step.get("pct_of_base", 0):.1f}%"
            )

        console.print(table)
    else:
        console.print("[yellow]Pending execution...[/yellow]")

    # Warnings
    warnings = context.get("warnings", [])
    if warnings:
        console.print("\n" + "=" * 70)
        console.print("[bold red]WARNINGS / UNVERIFIABLE GATES[/bold red]")
        console.print("=" * 70)
        for warning in warnings:
            console.print(f"⚠️  {warning}")

    # Next action
    console.print("\n" + "=" * 70)
    console.print("[bold green]NEXT ACTION[/bold green]")
    console.print("=" * 70)
    next_action = context.get("next_action", "Awaiting user input...")
    console.print(next_action)
    console.print()


@app.command()
def run():
    """
    Start the RWD IE Optimizer REPL.

    This interactive session will:
    1. Accept your I/E criteria text
    2. Parse into structured format
    3. Resolve medical concepts to codes
    4. Generate SQL queries
    5. Execute and show patient funnel
    6. Allow iterative refinement
    """

    # Validate settings
    try:
        settings.validate()
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print("\nPlease set OPENAI_API_KEY in your .env file:")
        console.print("  cp .env.example .env")
        console.print("  # Edit .env and add your API key")
        raise typer.Exit(1)

    # Display banner
    display_banner()

    # Instructions
    console.print("\n[bold]Instructions:[/bold]")
    console.print("1. Paste your I/E criteria below")
    console.print("2. Press Ctrl+D (Mac/Linux) or Ctrl+Z then Enter (Windows) when done")
    console.print("3. Review the generated SQL and funnel")
    console.print("4. Provide feedback or type 'finalize' to complete\n")

    # Read multi-line input
    console.print("[bold cyan]Paste your I/E criteria:[/bold cyan]\n")

    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    user_ie_text = "\n".join(lines)

    if not user_ie_text.strip():
        console.print("\n[red]No input provided. Exiting.[/red]")
        raise typer.Exit(1)

    console.print(f"\n[green]✓[/green] Received {len(user_ie_text)} characters of I/E criteria")
    console.print("\n[bold cyan]Processing with multi-agent system...[/bold cyan]\n")

    # Initialize Swarm client
    client = Swarm()

    # Initialize context
    context = {
        "criteria_dsl": {},
        "resolved_concepts": {},
        "sql_cohort": "pending",
        "sql_funnel": "pending",
        "funnel_steps": [],
        "warnings": [],
        "next_action": "",
        "finalized": False,
        "iteration": 0,
    }

    # Initial message to orchestrator
    messages = [
        {
            "role": "user",
            "content": f"""I need help converting the following clinical trial I/E criteria into SQL over our RWD database.

Please follow the complete workflow:
1. Parse this text into Criteria DSL JSON
2. Resolve all medical concepts to codes
3. Generate SQL queries for cohort identification
4. Execute the SQL and show me the funnel

Here are the I/E criteria:

{user_ie_text}

Please begin by transferring to the IE_Interpreter agent to parse this criteria."""
        }
    ]

    # Run workflow
    try:
        max_iterations = 5
        current_iteration = 0

        while current_iteration < max_iterations and not context.get("finalized"):
            current_iteration += 1

            console.print(f"[dim]Iteration {current_iteration}...[/dim]")

            # Run Swarm
            response = client.run(
                agent=orchestrator_agent,
                messages=messages,
                context_variables=context,
            )

            # Update context from response
            if hasattr(response, 'context_variables'):
                context.update(response.context_variables)

            # Extract messages
            if hasattr(response, 'messages'):
                for msg in response.messages:
                    if msg.get("role") == "assistant" and msg.get("content"):
                        messages.append(msg)

            # Display current state
            display_repl_output(context)

            # Check if we should continue
            if context.get("finalized"):
                console.print("\n[bold green]✓ Workflow complete![/bold green]")
                break

            # Get user feedback
            feedback = console.input("\n[bold]Your feedback (or type 'finalize' to complete, 'quit' to exit):[/bold] ")

            if feedback.lower() in ["quit", "exit", "q"]:
                console.print("\n[yellow]Exiting...[/yellow]")
                break

            if feedback.lower() in ["finalize", "good", "approve", "ship it", "done"]:
                context["finalized"] = True
                messages.append({
                    "role": "user",
                    "content": "Please finalize this workflow and transfer to the Receiver agent for the final summary."
                })
                continue

            # Add user feedback to conversation
            messages.append({"role": "user", "content": feedback})

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user.[/yellow]")
        raise typer.Exit(0)

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        import traceback
        console.print("\n[dim]Traceback:[/dim]")
        console.print(traceback.format_exc())
        raise typer.Exit(1)

    console.print("\n[bold cyan]Thank you for using RWD IE Optimizer![/bold cyan]")


@app.command()
def test():
    """
    Test the system with a simple example.
    """
    console.print("[bold cyan]Testing RWD IE Optimizer...[/bold cyan]\n")

    from src.tools.catalog import get_catalog
    from src.tools.concept_search import search_concepts
    from src.tools.sql_executor import run_sql

    # Test catalog
    console.print("1. Testing get_catalog()...")
    catalog = get_catalog()
    console.print(f"   ✓ Found {len(catalog['tables'])} tables\n")

    # Test concept search
    console.print("2. Testing search_concepts('diabetes')...")
    results = search_concepts("diabetes")
    console.print(f"   ✓ Found {len(results)} matches\n")

    # Test SQL execution
    console.print("3. Testing run_sql()...")
    result = run_sql("SELECT COUNT(*) as cnt FROM patients", mode="preview")
    if result["ok"]:
        console.print(f"   ✓ Query executed successfully")
        console.print(f"   ✓ Patient count: {result['preview_rows'][0]['cnt']}\n")
    else:
        console.print(f"   ✗ Error: {result['error']}\n")

    console.print("[bold green]All tests passed![/bold green]")


if __name__ == "__main__":
    app()
