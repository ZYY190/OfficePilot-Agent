const state = {
  sessionId: localStorage.getItem("officepilot-session") || `web-${crypto.randomUUID()}`,
  busy: false,
};
localStorage.setItem("officepilot-session", state.sessionId);
const messages = document.querySelector("#messages");
const form = document.querySelector("#chat-form");
const input = document.querySelector("#input");
const send = document.querySelector("#send");
const toolList = document.querySelector("#tool-list");

function addMessage(role, text, toolCalls = []) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "我" : "OP";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  if (toolCalls.length) {
    const trace = document.createElement("div");
    trace.className = "tool-trace";
    trace.innerHTML = toolCalls.map(call =>
      `<div>🔧 <strong>${call.name}</strong> · ${JSON.stringify(call.arguments)}</div>`
    ).join("");
    bubble.appendChild(trace);
  }
  article.append(avatar, bubble);
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
}

async function sendMessage(text) {
  if (!text.trim() || state.busy) return;
  state.busy = true;
  send.disabled = true;
  addMessage("user", text.trim());
  input.value = "";
  input.style.height = "auto";
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({session_id: state.sessionId, message: text.trim()}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "请求失败");
    addMessage("assistant", data.reply, data.tool_calls || []);
  } catch (error) {
    addMessage("assistant", `请求失败：${error.message}`);
  } finally {
    state.busy = false;
    send.disabled = false;
    input.focus();
  }
}

async function loadTools() {
  try {
    const response = await fetch("/api/tools");
    const data = await response.json();
    toolList.innerHTML = "";
    for (const tool of data.tools || []) {
      const item = document.createElement("li");
      item.textContent = tool.name;
      item.title = tool.description || "";
      toolList.appendChild(item);
    }
  } catch {
    toolList.innerHTML = "<li>连接失败</li>";
  }
}

async function runDemo(kind) {
  const sequences = {
    tasks: [
      "添加待办：完成 MCP 智能体实验报告",
      "完成它",
      "查看全部待办",
    ],
    files: [
      "计算 (128 + 72) / 4",
      "把“会议纪要：完成需求评审”写入 meeting.txt",
      "再读取刚才的文件",
    ],
    weather: ["北京天气怎么样"],
  };
  state.sessionId = `demo-${kind}-${Date.now()}`;
  localStorage.setItem("officepilot-session", state.sessionId);
  for (const step of sequences[kind] || []) {
    await sendMessage(step);
    await new Promise(resolve => setTimeout(resolve, 350));
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  sendMessage(input.value);
});
input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage(input.value);
  }
});
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
});
document.querySelectorAll(".suggestion").forEach(button => {
  button.addEventListener("click", () => sendMessage(button.textContent));
});
document.querySelector("#new-chat").addEventListener("click", () => {
  state.sessionId = `web-${crypto.randomUUID()}`;
  localStorage.setItem("officepilot-session", state.sessionId);
  messages.innerHTML = "";
  addMessage("assistant", "已开启新会话。之前的记忆仍保存在不同会话中，不会混入当前对话。");
});
loadTools();


const demoKind = new URLSearchParams(location.search).get("demo");
if (demoKind) runDemo(demoKind);
