from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from confirmation_guard import ConfirmationGuard
from providers.base import Provider, ToolCall
from tools import TOOL_FUNCTIONS


@dataclass
class AgentRun:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)


class HelpdeskAgent:
    def __init__(
        self,
        provider: Provider,
        *,
        system_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        guard: ConfirmationGuard | None = None,
    ) -> None:
        self.provider = provider
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.model = model
        # A single eval turn has no real clarify(yes_no) before it, so every
        # create_ticket(confirmed=true) is blocked here instead of writing a ticket.
        self.guard = guard or ConfirmationGuard()

    def run(self, user_messages: list[dict[str, str]], *, tool_choice: Any | None = None) -> AgentRun:
        messages = [{"role": "system", "content": self.system_prompt}, *user_messages]
        response = self.provider.complete(
            messages,
            self.tools,
            model=self.model,
            temperature=0.0,
            tool_choice=tool_choice,
        )
        results: list[dict[str, Any]] = []
        for call in response.tool_calls:
            func = TOOL_FUNCTIONS.get(call.name)
            if not func:
                results.append({"tool": call.name, "error": "unknown_tool"})
                continue
            blocked = self.guard.check(call.name, call.args)
            if blocked is not None:
                results.append({"tool": call.name, "args": call.args, "result": blocked})
                continue
            try:
                result = func(**call.args)
            except Exception as exc:  # keep eval robust; failures are evidence
                result = {"error": type(exc).__name__, "message": str(exc)}
            self.guard.record(call.name, call.args, result)
            results.append({"tool": call.name, "args": call.args, "result": result})
        return AgentRun(text=response.text, tool_calls=response.tool_calls, tool_results=results)
