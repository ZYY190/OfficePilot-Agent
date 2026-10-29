from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from agent.plan import Plan


class LlmPlanner:
    """Optional OpenAI-compatible tool-calling planner."""

    def __init__(self, endpoint: str, api_key: str, model: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model

    @classmethod
    def from_environment(cls) -> "LlmPlanner | None":
        endpoint = os.environ.get("LLM_API_URL", "").strip()
        api_key = os.environ.get("LLM_API_KEY", "").strip()
        model = os.environ.get("LLM_MODEL", "").strip()
        if endpoint and api_key and model:
            return cls(endpoint, api_key, model)
        return None

    def plan(self, message: str, history: list[dict[str, str]], tools: list[dict[str, Any]]) -> Plan | None:
        tool_payload = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {"type": "object"}),
                },
            }
            for tool in tools
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 OfficePilot 的任务规划器。根据用户自然语言选择最合适的工具。"
                    "只调用一个工具；会话 ID 由运行时补充。若无需工具，直接用中文回答。"
                ),
            },
            *history[-8:],
            {"role": "user", "content": message},
        ]
        body = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "tools": tool_payload,
                "tool_choice": "auto",
                "temperature": 0.1,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.endpoint}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assistant = payload["choices"][0]["message"]
        calls = assistant.get("tool_calls") or []
        if calls:
            function = calls[0]["function"]
            return Plan("tool", function["name"], json.loads(function.get("arguments") or "{}"))
        content = (assistant.get("content") or "").strip()
        return Plan("chat", reply=content) if content else None
