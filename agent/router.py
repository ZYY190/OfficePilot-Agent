from __future__ import annotations

import re
from typing import Any

from agent.llm_planner import LlmPlanner
from agent.plan import Plan


class IntentRouter:
    """Optional LLM planner with a deterministic offline fallback."""

    def __init__(self) -> None:
        self.llm = LlmPlanner.from_environment()

    def plan(
        self,
        message: str,
        history: list[dict[str, str]],
        tools: list[dict[str, Any]],
        state: dict[str, Any],
    ) -> Plan:
        if self.llm is not None:
            try:
                llm_plan = self.llm.plan(message, history, tools)
                if llm_plan is not None:
                    return llm_plan
            except Exception:
                pass
        return self._fallback(message, state)

    def _fallback(self, message: str, state: dict[str, Any]) -> Plan:
        text = message.strip()

        if any(word in text for word in ["查看", "列出", "显示", "有哪些"]) and any(
            word in text for word in ["待办", "任务"]
        ):
            return Plan("tool", "todo_list", {"status": "all"})

        complete = re.search(r"完成.{0,8}?(?:第\s*)?(\d+)\s*(?:个|项)?\s*(?:待办|任务)?", text)
        if complete:
            return Plan("tool", "todo_complete", {"task_id": int(complete.group(1))})
        if any(phrase in text for phrase in ["完成它", "完成这项", "标记为完成"]):
            task_id = state.get("last_task_id")
            if task_id:
                return Plan("tool", "todo_complete", {"task_id": int(task_id)})

        add = re.search(r"(?:添加|新增|创建|记下|提醒我).*?(?:待办|任务)[：:，,\s]*(.+)", text)
        if add:
            return Plan("tool", "todo_add", {"title": add.group(1).strip(), "priority": "normal"})
        reminder = re.search(r"提醒我(.+)", text)
        if reminder:
            return Plan("tool", "todo_add", {"title": reminder.group(1).strip(), "priority": "high"})

        calc = re.search(r"(?:计算|算一下|帮我算)\s*[:：]?\s*(.+)", text)
        if calc:
            return Plan("tool", "calculator", {"expression": calc.group(1).strip()})
        if re.fullmatch(r"[\d\s+\-*/().%]+", text):
            return Plan("tool", "calculator", {"expression": text})

        write = re.search(r"(?:把|将)?\s*[“\"']?(.+?)[”\"']?\s*(?:写入|保存到|写到)\s*([^\s，,。]+)", text)
        if write:
            return Plan("tool", "file_write", {"path": write.group(2), "content": write.group(1)})
        create = re.search(r"创建文件\s*([^\s，,。]+)\s*(?:内容|写入)[：:，,\s]*(.+)", text)
        if create:
            return Plan("tool", "file_write", {"path": create.group(1), "content": create.group(2)})

        if "刚才的文件" in text or "这个文件" in text:
            path = state.get("last_file_path")
            if path:
                return Plan("tool", "file_read", {"path": path})
        read = re.search(r"(?:读取|打开|查看文件)\s*[:：]?\s*([^\s，,。]+)", text)
        if read:
            return Plan("tool", "file_read", {"path": read.group(1)})

        weather = re.search(r"(.+?)(?:今天|现在)?天气(?:怎么样|如何)?", text)
        if weather:
            city = weather.group(1).strip(" ，,。")
            if city:
                return Plan("tool", "weather_query", {"city": city})

        if any(word in text for word in ["你好", "嗨", "hello", "hi"]):
            return Plan("chat", reply="你好，我是 OfficePilot。你可以让我管理待办、计算表达式、读写文件或查询天气。")
        return Plan(
            "chat",
            reply="我理解你的输入，但暂时没有匹配到可执行工具。你可以试试：“添加待办：明天交作业”“计算 (12+8)*3”“读取 note.txt”或“北京天气怎么样”。",
        )

