"""
All agents for the RWD IE Optimizer using the internal agent runtime.

This module defines all 6 agents and their coordination logic.
"""

from src.agent_runtime import Agent
from src.tools.catalog import get_catalog
from src.tools.concept_search import search_concepts
from src.tools.unit_resolver import resolve_units
from src.tools.sql_executor import run_sql
from src.tools.artifact_store import save_artifact
from src.config.settings import settings
from pathlib import Path


def load_prompt(agent_name: str) -> str:
    """Load agent system prompt from file."""
    prompts_dir = Path(__file__).parent.parent / "config" / "prompts"
    prompt_file = prompts_dir / f"{agent_name}.txt"

    if prompt_file.exists():
        return prompt_file.read_text()
    else:
        return f"You are the {agent_name} agent."


# =============================================================================
# AGENT DEFINITIONS
# =============================================================================

# 1. IE INTERPRETER AGENT
# Parses raw I/E text into Criteria DSL JSON
ie_interpreter_agent = Agent(
    name="IE_Interpreter",
    model=settings.MODEL_DEFAULT,
    instructions=load_prompt("ie_interpreter"),
    tools=[],  # No tools needed, pure LLM parsing
)


# 2. DEEP RESEARCH AGENT
# Resolves medical concepts to database codes
deep_research_agent = Agent(
    name="Deep_Research",
    model=settings.MODEL_RESEARCH,
    instructions=load_prompt("deep_research"),
    tools=[get_catalog, search_concepts, resolve_units],
)


# 3. CODING AGENT
# Generates SQL from Criteria DSL + Resolved Concepts
coding_agent = Agent(
    name="Coding_Agent",
    model=settings.MODEL_CODING,
    instructions=load_prompt("coding_agent"),
    tools=[get_catalog],
)


# 4. SQL RUNNER AGENT
# Executes and validates SQL
sql_runner_agent = Agent(
    name="SQL_Runner",
    model=settings.MODEL_DEFAULT,
    instructions=load_prompt("sql_runner"),
    tools=[run_sql],
)


# 5. RECEIVER AGENT
# Generates final summary
receiver_agent = Agent(
    name="Receiver",
    model=settings.MODEL_DEFAULT,
    instructions=load_prompt("receiver"),
    tools=[save_artifact],
)


# =============================================================================
# AGENT HANDOFF FUNCTIONS
# =============================================================================

def transfer_to_ie_interpreter():
    """Transfer control to IE Interpreter for parsing I/E criteria."""
    return ie_interpreter_agent


def transfer_to_deep_research():
    """Transfer control to Deep Research for concept resolution."""
    return deep_research_agent


def transfer_to_coding_agent():
    """Transfer control to Coding Agent for SQL generation."""
    return coding_agent


def transfer_to_sql_runner():
    """Transfer control to SQL Runner for execution."""
    return sql_runner_agent


def transfer_to_receiver():
    """Transfer control to Receiver for final summary."""
    return receiver_agent


# 6. ORCHESTRATOR AGENT
# Main controller that coordinates all other agents
orchestrator_agent = Agent(
    name="Orchestrator",
    model=settings.MODEL_DEFAULT,
    instructions=load_prompt("orchestrator"),
    tools=[
        transfer_to_ie_interpreter,
        transfer_to_deep_research,
        transfer_to_coding_agent,
        transfer_to_sql_runner,
        transfer_to_receiver,
        get_catalog,
        run_sql,
        save_artifact,
    ],
)


# =============================================================================
# AGENT REGISTRY
# =============================================================================

ALL_AGENTS = {
    "orchestrator": orchestrator_agent,
    "ie_interpreter": ie_interpreter_agent,
    "deep_research": deep_research_agent,
    "coding_agent": coding_agent,
    "sql_runner": sql_runner_agent,
    "receiver": receiver_agent,
}


def get_agent(name: str) -> Agent:
    """Get agent by name."""
    return ALL_AGENTS.get(name)
