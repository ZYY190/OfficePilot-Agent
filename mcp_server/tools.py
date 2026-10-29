from __future__ import annotations

import ast
import json
import operator
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from agent.config import DB_PATH, WORKSPACE_DIR
from agent.memory import MemoryStore

STORE = MemoryStore(DB_PATH)
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "todo_add": {
        "description": "添加一条待办任务",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "title": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]},
            },
            "required": ["session_id", "title"],
        },
    },
    "todo_list": {
        "description": "查看某个会话的待办任务",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "done", "all"]},
            },
            "required": ["session_id"],
        },
    },
    "todo_complete": {
        "description": "将指定编号的待办标记为完成",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "task_id": {"type": "integer"},
            },
            "required": ["session_id", "task_id"],
        },
    },
    "calculator": {
        "description": "安全计算四则运算表达式",
        "inputSchema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
    "file_write": {
        "description": "在智能体沙箱工作区创建或追加文本文件",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "mode": {"type": "string", "enum": ["overwrite", "append"]},
            },
            "required": ["path", "content"],
        },
    },
    "file_read": {
        "description": "读取智能体沙箱工作区中的文本文件",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    "weather_query": {
        "description": "调用外部天气接口查询城市当前天气",
        "inputSchema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}


def _ok(**payload: Any) -> dict[str, Any]:
    return {"ok": True, **payload}


def _error(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message}


def _safe_path(raw_path: str) -> Path:
    candidate = (WORKSPACE_DIR / raw_path).resolve()
    if candidate != WORKSPACE_DIR and WORKSPACE_DIR not in candidate.parents:
        raise ValueError("只允许访问智能体工作区内的文件")
    return candidate


_OPS: dict[type[ast.AST], Callable[..., Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_evaluate(node.operand))
    raise ValueError("表达式只支持数字、括号和四则运算")


def tool_todo_add(args: dict[str, Any]) -> dict[str, Any]:
    title = str(args.get("title", "")).strip()
    if not title:
        return _error("待办内容不能为空")
    session_id = str(args["session_id"])
    priority = str(args.get("priority", "normal"))
    return _ok(task=STORE.add_task(session_id, title, priority))


def tool_todo_list(args: dict[str, Any]) -> dict[str, Any]:
    session_id = str(args["session_id"])
    status = str(args.get("status", "pending"))
    return _ok(tasks=STORE.list_tasks(session_id, status))


def tool_todo_complete(args: dict[str, Any]) -> dict[str, Any]:
    session_id = str(args["session_id"])
    task_id = int(args["task_id"])
    task = STORE.complete_task(session_id, task_id)
    return _ok(task=task) if task else _error(f"未找到待办 #{task_id}")


def tool_calculator(args: dict[str, Any]) -> dict[str, Any]:
    expression = str(args.get("expression", "")).strip()
    if not expression:
        return _error("计算表达式不能为空")
    try:
        value = _evaluate(ast.parse(expression, mode="eval"))
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return _ok(expression=expression, result=value)
    except Exception as exception:
        return _error(f"计算失败：{exception}")


def tool_file_write(args: dict[str, Any]) -> dict[str, Any]:
    try:
        path = _safe_path(str(args["path"]))
        mode = str(args.get("mode", "overwrite"))
        content = str(args.get("content", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a" if mode == "append" else "w", encoding="utf-8") as handle:
            handle.write(content)
        return _ok(path=path.relative_to(WORKSPACE_DIR).as_posix(), mode=mode, chars=len(content))
    except Exception as exception:
        return _error(f"写入失败：{exception}")


def tool_file_read(args: dict[str, Any]) -> dict[str, Any]:
    try:
        path = _safe_path(str(args["path"]))
        if not path.exists():
            return _error(f"文件不存在：{args['path']}")
        content = path.read_text(encoding="utf-8")
        return _ok(path=path.relative_to(WORKSPACE_DIR).as_posix(), content=content)
    except Exception as exception:
        return _error(f"读取失败：{exception}")


def tool_weather_query(args: dict[str, Any]) -> dict[str, Any]:
    city = str(args.get("city", "")).strip()
    if not city:
        return _error("城市不能为空")
    url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1&lang=zh"
    request = urllib.request.Request(url, headers={"User-Agent": "OfficePilot-Agent/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
        current = payload["current_condition"][0]
        return _ok(
            city=city,
            temperature_c=current["temp_C"],
            feels_like_c=current["FeelsLikeC"],
            humidity=current["humidity"],
            weather=current["weatherDesc"][0]["value"],
            source="wttr.in",
        )
    except Exception as exception:
        return _error(f"天气接口暂时不可用：{exception}")


TOOL_FUNCTIONS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "todo_add": tool_todo_add,
    "todo_list": tool_todo_list,
    "todo_complete": tool_todo_complete,
    "calculator": tool_calculator,
    "file_write": tool_file_write,
    "file_read": tool_file_read,
    "weather_query": tool_weather_query,
}


def list_tools() -> list[dict[str, Any]]:
    return [{"name": name, **schema} for name, schema in TOOL_SCHEMAS.items()]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return _error(f"未知工具：{name}")
    return function(arguments)
