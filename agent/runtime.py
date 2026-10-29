from __future__ import annotations

from typing import Any

from agent.config import DB_PATH, MAX_HISTORY
from agent.mcp_client import McpClient
from agent.memory import MemoryStore
from agent.plan import Plan
from agent.router import IntentRouter


class OfficeAgent:
    """Task-planning and MCP-tool-executing office assistant."""

    def __init__(self) -> None:
        self.memory = MemoryStore(DB_PATH)
        self.mcp = McpClient()
        self.mcp.start()
        self.router = IntentRouter()

    def chat(self, session_id: str, message: str) -> dict[str, Any]:
        if not session_id.strip():
            raise ValueError("session_id 不能为空")
        message = message.strip()
        if not message:
            raise ValueError("消息不能为空")
        history = self.memory.history(session_id, MAX_HISTORY)
        state = self.memory.get_state(session_id)
        self.memory.add_message(session_id, "user", message)
        plan = self.router.plan(message, history, self.mcp.tools, state)
        tool_calls: list[dict[str, Any]] = []
        if plan.kind == "tool":
            arguments = dict(plan.arguments)
            if plan.tool.startswith("todo_"):
                arguments["session_id"] = session_id
            result = self.mcp.call_tool(plan.tool, arguments)
            tool_calls.append({"name": plan.tool, "arguments": arguments, "result": result})
            reply = self._summarize(plan, result)
            self._remember_state(session_id, state, plan, result)
        else:
            reply = plan.reply or "我暂时没有生成有效回复。"
        self.memory.add_message(session_id, "assistant", reply)
        return {"session_id": session_id, "reply": reply, "tool_calls": tool_calls, "state": state}

    def _remember_state(self, session_id: str, state: dict[str, Any], plan: Plan, result: dict[str, Any]) -> None:
        if not result.get("ok"):
            return
        if plan.tool == "todo_add":
            state["last_task_id"] = result["task"]["task_id"]
        elif plan.tool in {"file_write", "file_read"}:
            state["last_file_path"] = result["path"]
        self.memory.set_state(session_id, state)

    def _summarize(self, plan: Plan, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return f"执行工具 `{plan.tool}` 失败：{result.get('error', '未知错误')}"
        if plan.tool == "todo_add":
            task = result["task"]
            return f"已添加待办 #{task['task_id']}：{task['title']}（优先级：{task['priority']}）。"
        if plan.tool == "todo_list":
            tasks = result.get("tasks", [])
            if not tasks:
                return "当前没有待办任务。"
            lines = ["当前任务列表："]
            for task in tasks:
                marker = "✓" if task["status"] == "done" else "○"
                lines.append(f"{marker} #{task['id']} {task['title']}（{task['priority']}）")
            return "\n".join(lines)
        if plan.tool == "todo_complete":
            task = result["task"]
            return f"已将待办 #{task['task_id']}「{task['title']}」标记为完成。"
        if plan.tool == "calculator":
            return f"{result['expression']} = {result['result']}"
        if plan.tool == "file_write":
            return f"已写入文件 `{result['path']}`，共 {result['chars']} 个字符。"
        if plan.tool == "file_read":
            content = result.get("content", "")
            shown = content if len(content) <= 1200 else content[:1200] + "\n...(内容已截断)"
            return f"文件 `{result['path']}` 的内容：\n\n{shown}"
        if plan.tool == "weather_query":
            return (
                f"{result['city']}当前天气：{result['weather']}，气温 {result['temperature_c']}°C，"
                f"体感 {result['feels_like_c']}°C，湿度 {result['humidity']}%。"
            )
        return str(result)

    def history(self, session_id: str) -> list[dict[str, str]]:
        return self.memory.history(session_id, 50)

    def close(self) -> None:
        self.mcp.close()
