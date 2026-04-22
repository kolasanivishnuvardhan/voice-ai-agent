"""Groq Llama tool-calling agent with reasoning trace logging."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from groq import Groq
import structlog

from agent.tools.tool_definitions import TOOL_DEFINITIONS
from agent.tools.tool_executor import ToolExecutor

logger = structlog.get_logger(__name__)


class LLMAgent:
    """Orchestrates Groq chat completions and iterative tool usage."""

    def __init__(self, tool_executor: ToolExecutor) -> None:
        api_key: str | None = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required")
        self.client: Groq = Groq(api_key=api_key)
        self.model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.tool_executor: ToolExecutor = tool_executor

    async def _completion(self, messages: list[dict[str, Any]]) -> Any:
        """Call Groq completion endpoint asynchronously."""
        return await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=1024,
        )

    async def run(
        self,
        system_prompt: str,
        conversation_history: list[dict[str, Any]],
        user_text: str,
    ) -> dict[str, Any]:
        """Run a multi-turn agent loop with optional tool execution."""
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-12:])
        messages.append({"role": "user", "content": user_text})

        reasoning_trace: list[dict[str, Any]] = [*messages]
        tool_called: str | None = None
        tool_executions: list[dict[str, Any]] = []

        first_response = await self._completion(messages)
        first_message = first_response.choices[0].message
        assistant_entry: dict[str, Any] = {
            "role": "assistant",
            "content": first_message.content or "",
        }

        if first_message.tool_calls:
            assistant_entry["tool_calls"] = [tc.model_dump() for tc in first_message.tool_calls]
        messages.append(assistant_entry)
        reasoning_trace.append(assistant_entry)

        if first_message.tool_calls:
            for tool_call in first_message.tool_calls:
                tool_called = tool_call.function.name
                args: dict[str, Any] = json.loads(tool_call.function.arguments or "{}")
                result = await self.tool_executor.execute(tool_called, args)
                tool_executions.append({"name": tool_called, "arguments": args, "result": result})
                tool_result_text = json.dumps(result, ensure_ascii=False)
                tool_msg: dict[str, Any] = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_called,
                    "content": tool_result_text,
                }
                messages.append(tool_msg)
                reasoning_trace.append(tool_msg)

            second_response = await self._completion(messages)
            final_text: str = second_response.choices[0].message.content or ""
            final_msg: dict[str, Any] = {"role": "assistant", "content": final_text}
            reasoning_trace.append(final_msg)
        else:
            final_text = first_message.content or ""

        if not final_text.strip():
            final_text = (
                "Please share doctor specialization and preferred date. "
                "You can say today or tomorrow, and I will show available slots for you to choose."
            )

        logger.info(
            "agent_reasoning_trace",
            trace=reasoning_trace,
            tool_called=tool_called,
            model=self.model,
        )

        return {
            "response_text": final_text,
            "tool_called": tool_called,
            "tool_executions": tool_executions,
            "reasoning_trace": reasoning_trace,
            "intent": "appointment_management",
        }
