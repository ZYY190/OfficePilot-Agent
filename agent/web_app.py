from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from agent.config import ROOT, WEB_HOST, WEB_PORT
from agent.runtime import OfficeAgent

WEB_ROOT = ROOT / "web"
ASSETS = {"/": "index.html", "/index.html": "index.html", "/styles.css": "styles.css", "/app.js": "app.js"}


class Handler(BaseHTTPRequestHandler):
    server_version = "OfficePilot/1.0"
    agent: OfficeAgent

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json({"ok": True, "tools": len(self.agent.mcp.tools)})
            return
        if parsed.path == "/api/tools":
            self._json({"tools": self.agent.mcp.tools})
            return
        if parsed.path == "/api/history":
            session_id = parse_qs(parsed.query).get("session_id", [""])[0]
            self._json({"messages": self.agent.history(session_id)})
            return
        filename = ASSETS.get(parsed.path)
        if filename is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        path = WEB_ROOT / filename
        content = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/chat":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            response = self.agent.chat(
                str(payload.get("session_id", "web-demo")),
                str(payload.get("message", "")),
            )
            self._json(response)
        except Exception as exception:
            self._json({"error": str(exception)}, 400)

    def log_message(self, format: str, *args) -> None:
        print(f"[web] {self.address_string()} - {format % args}")


def main() -> None:
    agent = OfficeAgent()
    Handler.agent = agent
    server = ThreadingHTTPServer((WEB_HOST, WEB_PORT), Handler)
    print(f"OfficePilot running at http://{WEB_HOST}:{WEB_PORT}")
    print(f"MCP tools loaded: {', '.join(tool['name'] for tool in agent.mcp.tools)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        agent.close()


if __name__ == "__main__":
    main()
