from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from typing import Any

from agent.config import ROOT


class McpClient:
    """Small MCP stdio client used by the agent runtime."""

    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self._request_id = 0
        self._lock = threading.Lock()
        self.tools: list[dict[str, Any]] = []

    def start(self) -> None:
        if self.process is not None:
            return
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        self.process = subprocess.Popen(
            [sys.executable, "-m", "mcp_server.server"],
            cwd=ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "officepilot-agent", "version": "1.0.0"},
        })
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.process.stdin.flush()
        self.tools = self.list_tools()

    def _request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("MCP server is not running")
        with self._lock:
            self._request_id += 1
            request_id = self._request_id
            payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
            if params is not None:
                payload["params"] = params
            self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
            while True:
                line = self.process.stdout.readline()
                if not line:
                    error = self.process.stderr.read() if self.process.stderr else ""
                    raise RuntimeError(f"MCP server stopped unexpectedly: {error}")
                response = json.loads(line)
                if response.get("id") == request_id:
                    if "error" in response:
                        raise RuntimeError(response["error"].get("message", "MCP request failed"))
                    return response.get("result")

    def list_tools(self) -> list[dict[str, Any]]:
        return self._request("tools/list", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        content = result.get("content", [])
        if not content:
            return {"ok": False, "error": "MCP tool returned no content"}
        return json.loads(content[0].get("text", "{}"))

    def close(self) -> None:
        if self.process is None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None:
                stream.close()
        self.process = None


