"""
Lightweight agent runtime using the OpenAI Python SDK.

Replaces the deprecated Swarm dependency while keeping a similar run() API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Union
import types
import json
import os
import inspect
from typing import get_args, get_origin

from openai import OpenAI


JsonDict = Dict[str, Any]
ToolCallable = Callable[..., Any]


class Agent:
    """Simple agent definition compatible with Swarm-style usage."""

    def __init__(
        self,
        name: str,
        model: str,
        instructions: str,
        tools: Optional[List[ToolCallable]] = None,
        functions: Optional[List[ToolCallable]] = None,
    ) -> None:
        if tools is not None and functions is not None:
            raise ValueError("Provide either tools or functions, not both")

        self.name = name
        self.model = model
        self.instructions = instructions
        self.tools = tools if tools is not None else (functions or [])


@dataclass
class AgentResponse:
    messages: List[JsonDict]
    context_variables: JsonDict


class AgentRunner:
    """Runs agents with tool-calling using the OpenAI Chat Completions API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        max_turns: int = 8,
    ) -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.default_model = default_model or os.getenv("MODEL_DEFAULT", "gpt-4o")
        self.max_turns = max_turns

    def run(
        self,
        agent: Agent,
        messages: List[JsonDict],
        context_variables: Optional[JsonDict] = None,
    ) -> AgentResponse:
        conversation: List[JsonDict] = []

        if agent.instructions:
            conversation.append({"role": "system", "content": agent.instructions})

        if context_variables:
            conversation.append(
                {
                    "role": "system",
                    "content": (
                        "Context variables (JSON, read-only): "
                        + json.dumps(context_variables, ensure_ascii=True)
                    ),
                }
            )

        conversation.extend(messages)

        tool_specs = self._build_tool_specs(agent.tools)
        tool_map = {tool.__name__: tool for tool in agent.tools}

        response_messages: List[JsonDict] = []
        ctx = dict(context_variables or {})

        current_agent = agent

        for _ in range(self.max_turns):
            request_kwargs: JsonDict = {
                "model": current_agent.model or self.default_model,
                "messages": conversation,
            }

            if tool_specs:
                request_kwargs["tools"] = tool_specs
                request_kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**request_kwargs)

            message = response.choices[0].message

            assistant_entry: JsonDict = {
                "role": "assistant",
                "content": message.content or "",
            }

            if getattr(message, "tool_calls", None):
                assistant_entry["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": call.type,
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in message.tool_calls
                ]

            conversation.append(assistant_entry)

            if message.content:
                response_messages.append({"role": "assistant", "content": message.content})

            tool_calls = getattr(message, "tool_calls", None) or []
            if not tool_calls:
                if not response_messages:
                    response_messages.append({"role": "assistant", "content": message.content or ""})
                return AgentResponse(messages=response_messages, context_variables=ctx)

            for call in tool_calls:
                tool_name = call.function.name
                tool = tool_map.get(tool_name)

                if tool is None:
                    result: Any = {"error": f"Unknown tool '{tool_name}'"}
                else:
                    args = self._parse_tool_args(call.function.arguments)
                    try:
                        result = tool(**args)
                    except Exception as exc:  # pragma: no cover - defensive
                        result = {"error": str(exc)}

                # Handoff to another agent if the tool returns an Agent
                if isinstance(result, Agent):
                    current_agent = result
                    tool_specs = self._build_tool_specs(current_agent.tools)
                    tool_map = {tool.__name__: tool for tool in current_agent.tools}
                    conversation.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(
                                {"handoff": current_agent.name},
                                ensure_ascii=True,
                            ),
                        }
                    )
                    conversation.append(
                        {"role": "system", "content": current_agent.instructions}
                    )
                    continue

                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, ensure_ascii=True, default=str),
                    }
                )

        return AgentResponse(messages=response_messages, context_variables=ctx)

    @staticmethod
    def _parse_tool_args(arguments: str) -> Dict[str, Any]:
        if not arguments:
            return {}

        try:
            parsed = json.loads(arguments)
            if isinstance(parsed, dict):
                return parsed
            return {"value": parsed}
        except json.JSONDecodeError:
            return {"__raw_arguments": arguments}

    def _build_tool_specs(self, tools: Iterable[ToolCallable]) -> List[JsonDict]:
        specs = []
        for tool in tools:
            specs.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.__name__,
                        "description": self._tool_description(tool),
                        "parameters": self._tool_parameters(tool),
                    },
                }
            )
        return specs

    @staticmethod
    def _tool_description(tool: ToolCallable) -> str:
        doc = (tool.__doc__ or "").strip().splitlines()
        return doc[0] if doc else ""

    def _tool_parameters(self, tool: ToolCallable) -> JsonDict:
        signature = inspect.signature(tool)
        properties: Dict[str, JsonDict] = {}
        required: List[str] = []

        for name, param in signature.parameters.items():
            annotation = param.annotation
            is_optional = False

            if annotation is inspect._empty:
                annotation = type(param.default) if param.default is not inspect._empty else str
            else:
                annotation, is_optional = self._unwrap_optional(annotation)

            properties[name] = self._json_schema_for(annotation)

            if param.default is inspect._empty and not is_optional:
                required.append(name)

        schema: JsonDict = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required

        return schema

    @staticmethod
    def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
        origin = get_origin(annotation)
        if origin is None:
            return annotation, False

        if origin in (Union, types.UnionType):
            args = [a for a in get_args(annotation) if a is not type(None)]
            if len(args) != len(get_args(annotation)):
                return (args[0] if args else str), True

        return annotation, False

    @staticmethod
    def _json_schema_for(annotation: Any) -> JsonDict:
        origin = get_origin(annotation)

        if origin is list or origin is List:
            return {"type": "array"}
        if origin is dict or origin is Dict:
            return {"type": "object"}

        if annotation in (str,):
            return {"type": "string"}
        if annotation in (int,):
            return {"type": "integer"}
        if annotation in (float,):
            return {"type": "number"}
        if annotation in (bool,):
            return {"type": "boolean"}

        return {"type": "string"}


__all__ = ["Agent", "AgentRunner", "AgentResponse"]
