# OfficePilot MCP 办公智能体

GitHub: <https://github.com/ZYY190/OfficePilot-Agent>

OfficePilot 是一个“能说会做”的智能办公助理。它接收自然语言任务，自动选择并调用 MCP 工具，完成待办管理、表达式计算、文件读写和天气查询，同时使用 SQLite 保存多轮会话记忆。

## 功能

- 自然语言聊天与意图识别
- MCP 风格工具服务器：`initialize`、`tools/list`、`tools/call`
- 待办添加、查看、完成
- 安全表达式计算
- 沙箱文件写入与读取
- 外部天气 API 查询
- SQLite 多轮对话记忆和最近任务上下文
- 无依赖 Web 前端
- 可选 OpenAI-compatible LLM 工具选择；未配置时使用离线规则回退
- 标准库实现，不需要安装第三方 Python 包

## 快速运行

要求 Python 3.10 或更高版本。

```powershell
.\start_web.ps1
```

浏览器访问 <http://127.0.0.1:8765>。

也可以使用 CLI：

```powershell
python -m agent.cli "添加待办：明天提交实验报告"
python -m agent.cli "北京天气怎么样"
```

## 演示示例

```text
你：添加待办：完成 MCP 智能体实验报告
Agent：已添加待办 #1：完成 MCP 智能体实验报告（优先级：normal）。

你：完成它
Agent：已将待办 #1「完成 MCP 智能体实验报告」标记为完成。

你：计算 (128 + 72) / 4
Agent：(128 + 72) / 4 = 50

你：把“会议纪要：完成需求评审”写入 meeting.txt
Agent：已写入文件 `meeting.txt`，共 11 个字符。

你：再读取刚才的文件
Agent：文件 `meeting.txt` 的内容：会议纪要：完成需求评审
```

## MCP 工具

| 工具 | 作用 |
| --- | --- |
| `todo_add` | 添加待办 |
| `todo_list` | 查看待办 |
| `todo_complete` | 完成待办 |
| `calculator` | 安全计算四则表达式 |
| `file_write` | 写入沙箱文件 |
| `file_read` | 读取沙箱文件 |
| `weather_query` | 调用 wttr.in 查询天气 |

## 可选 LLM 配置

不配置时，系统使用确定性的自然语言规则完成演示。配置以下环境变量后，会优先使用兼容 Chat Completions 的模型进行工具选择：

```powershell
$env:LLM_API_URL="https://your-endpoint/v1"
$env:LLM_API_KEY="your-key"
$env:LLM_MODEL="your-model"
```

## 测试

```powershell
.\run_tests.ps1
```

测试覆盖工具注册、计算器、文件沙箱、多轮任务完成和文件上下文记忆。

## 项目结构

```text
agent/          Agent Runtime、意图规划、MCP 客户端、SQLite 记忆
mcp_server/     MCP 工具定义与 JSON-RPC stdio 服务器
web/            单页聊天前端
tests/          自动化测试
docs/           架构图、业务流程图与博客草稿
workspace/      Agent 可读写的沙箱目录
data/           SQLite 数据库
```

## 安全说明

- 文件工具只能访问 `workspace/` 目录，阻止 `../` 路径穿越。
- 计算器只允许数字和四则运算，避免执行任意代码。
- 对外天气查询失败时会返回错误信息，不影响其他工具。
- 不要把 API Key 写入源码或提交到仓库。


