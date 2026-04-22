"""Tool executor maps tool names to injected scheduler callables."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

ToolHandler = Callable[..., Awaitable[Any]]


class ToolExecutor:
    """Execute agent tool calls via dependency-injected handlers."""

    def __init__(self, handlers: dict[str, ToolHandler]) -> None:
        self.handlers: dict[str, ToolHandler] = handlers

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
        """Execute tool and normalize known scheduler exceptions."""
        if tool_name not in self.handlers:
            return {"error": "UnknownTool", "message": f"Unknown tool: {tool_name}"}

        try:
            return await self.handlers[tool_name](**arguments)
        except Exception as exc:  # noqa: BLE001
            name: str = exc.__class__.__name__
            if name == "SlotConflictError":
                return {"error": "SlotConflict", "message": str(exc)}
            if name == "PastDateError":
                return {"error": "PastDate", "message": str(exc)}
            if name == "DoctorNotFoundError":
                return {"error": "DoctorNotFound", "message": str(exc)}
            if name == "SlotNotAvailableError":
                return {"error": "SlotNotAvailable", "message": str(exc)}
            if isinstance(exc, ValueError):
                return {"error": "NotFound", "message": str(exc)}
            return {"error": "ToolExecutionError", "message": str(exc)}
