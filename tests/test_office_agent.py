from __future__ import annotations

import os
import tempfile
import unittest
import uuid
from pathlib import Path

TEST_ROOT = Path(tempfile.mkdtemp(prefix="officepilot-test-"))
os.environ["AGENT_DATA_DIR"] = str(TEST_ROOT / "data")
os.environ["AGENT_WORKSPACE_DIR"] = str(TEST_ROOT / "workspace")
os.environ["AGENT_DB_PATH"] = str(TEST_ROOT / "data" / "agent.db")
os.environ.pop("LLM_API_URL", None)
os.environ.pop("LLM_API_KEY", None)
os.environ.pop("LLM_MODEL", None)

from agent.runtime import OfficeAgent  # noqa: E402
from mcp_server.tools import call_tool, list_tools  # noqa: E402


class OfficePilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = OfficeAgent()
        cls.session = f"test-{uuid.uuid4()}"

    @classmethod
    def tearDownClass(cls):
        cls.agent.close()

    def test_tool_registry(self):
        names = {tool["name"] for tool in list_tools()}
        self.assertEqual(
            names,
            {"todo_add", "todo_list", "todo_complete", "calculator", "file_write", "file_read", "weather_query"},
        )

    def test_calculator(self):
        result = call_tool("calculator", {"expression": "(12 + 8) * 3"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], 60)

    def test_file_sandbox_and_round_trip(self):
        result = call_tool(
            "file_write",
            {"path": "notes/test.txt", "content": "第一行\n第二行", "mode": "overwrite"},
        )
        self.assertTrue(result["ok"])
        read = call_tool("file_read", {"path": "notes/test.txt"})
        self.assertTrue(read["ok"])
        self.assertIn("第二行", read["content"])
        blocked = call_tool("file_read", {"path": "../secret.txt"})
        self.assertFalse(blocked["ok"])

    def test_multi_turn_task_completion(self):
        added = self.agent.chat(self.session, "添加待办：完成 MCP 智能体实验报告")
        self.assertTrue(added["tool_calls"])
        self.assertEqual(added["tool_calls"][0]["name"], "todo_add")
        task_id = added["state"]["last_task_id"]
        completed = self.agent.chat(self.session, "完成它")
        self.assertEqual(completed["tool_calls"][0]["name"], "todo_complete")
        self.assertEqual(completed["tool_calls"][0]["arguments"]["task_id"], task_id)

    def test_file_follow_up_memory(self):
        write = self.agent.chat(self.session, "把“今天完成了多轮记忆测试”写入 memory-demo.txt")
        self.assertEqual(write["tool_calls"][0]["name"], "file_write")
        read = self.agent.chat(self.session, "再读取刚才的文件")
        self.assertEqual(read["tool_calls"][0]["name"], "file_read")
        self.assertIn("多轮记忆测试", read["reply"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
