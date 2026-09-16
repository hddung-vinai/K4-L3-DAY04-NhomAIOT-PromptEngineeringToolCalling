from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from chat import ARTIFACTS_DIR, ROOT, now_iso, run_model_tool_loop, safe_slug, trim_history, write_transcript
from confirmation_guard import ConfirmationGuard
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


class AppConfig:
    def __init__(self, args: argparse.Namespace) -> None:
        self.provider_name = args.provider
        self.model = args.model
        self.system_prompt_path = args.system_prompt
        self.tools_path = args.tools
        self.system_prompt = args.system_prompt.read_text(encoding="utf-8")
        self.openai_tools = to_openai_tools(load_tool_declarations(args.tools))
        self.provider = make_provider(args.provider)
        self.selected_model = args.model or getattr(self.provider, "default_model", None)
        self.artifact_version = build_artifact_version(args.version, args.system_prompt, args.tools)
        self.transcripts_dir = args.transcripts_dir
        self.history_window = args.history_window
        self.max_tool_rounds = args.max_tool_rounds

    def info(self) -> dict[str, Any]:
        return {
            **artifact_version_dict(self.artifact_version),
            "provider": self.provider_name,
            "model": self.selected_model,
            "system_prompt": str(self.system_prompt_path),
            "tools": str(self.tools_path),
        }


class ChatSession:
    """One browser conversation: history, confirmation guard and transcript, same shape as chat.py."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.session_id = uuid.uuid4().hex
        self.history: list[dict[str, str]] = []
        self.guard = ConfirmationGuard()
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        transcript_id = "_".join([
            safe_slug(config.artifact_version.version),
            safe_slug(config.provider_name),
            "ui",
            timestamp,
        ])
        self.transcript_path = config.transcripts_dir / f"{transcript_id}.transcript.json"
        self.transcript: dict[str, Any] = {
            "transcript_id": transcript_id,
            **artifact_version_dict(config.artifact_version),
            "provider": config.provider_name,
            "model": config.selected_model,
            "system_prompt": str(config.system_prompt_path),
            "tools": str(config.tools_path),
            "history_window": config.history_window,
            "max_tool_rounds": config.max_tool_rounds,
            "interface": "web_ui",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "turns": [],
        }

    def send(self, user_text: str) -> dict[str, Any]:
        self.guard.start_user_turn(user_text)
        turn_record: dict[str, Any] = {
            "turn_index": len(self.transcript["turns"]) + 1,
            "started_at": now_iso(),
            "user": user_text,
            "status": "started",
            "assistant_text": None,
            "rounds": [],
            "tool_events": [],
        }
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            *trim_history(self.history, self.config.history_window),
            {"role": "user", "content": user_text},
        ]
        try:
            result = run_model_tool_loop(
                provider=self.config.provider,
                messages=messages,
                tools=self.config.openai_tools,
                model=self.config.model,
                max_tool_rounds=self.config.max_tool_rounds,
                guard=self.guard,
            )
            turn_record.update(result)
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": result["assistant_text"]})
        except Exception as exc:
            turn_record.update({"status": "provider_error", "error": f"{type(exc).__name__}: {str(exc)}"})
        turn_record["ended_at"] = now_iso()
        self.transcript["turns"].append(turn_record)
        write_transcript(self.transcript_path, self.transcript)
        return turn_record


PAGE = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IT Helpdesk Agent</title>
<style>
  :root { --bg:#f6f7f9; --panel:#fff; --text:#1d2330; --muted:#667085; --line:#d9dee7;
          --user:#e8f0fe; --ok:#1f7a45; --okbg:#e7f6ec; --err:#b42318; --errbg:#fdecea; --wait:#9a6700; --waitbg:#fff4d6; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#14171c; --panel:#1c2027; --text:#e6e9ef; --muted:#98a2b3; --line:#2f3642;
            --user:#23324d; --ok:#6fcf97; --okbg:#1c3326; --err:#ff8a80; --errbg:#3a2020; --wait:#f2c94c; --waitbg:#3a321c; }
  }
  * { box-sizing:border-box; }
  body { margin:0; font:14px/1.5 system-ui, sans-serif; background:var(--bg); color:var(--text); }
  header { position:sticky; top:0; background:var(--panel); border-bottom:1px solid var(--line); padding:10px 16px; display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
  header h1 { font-size:16px; margin:0 12px 0 0; }
  .badge { font:12px ui-monospace, monospace; background:var(--bg); border:1px solid var(--line); border-radius:6px; padding:2px 8px; overflow-wrap:anywhere; }
  header button { margin-left:auto; }
  main { max-width:960px; margin:0 auto; padding:16px; padding-bottom:120px; }
  .turn { margin-bottom:18px; }
  .user { background:var(--user); border-radius:10px; padding:8px 12px; margin-left:15%; white-space:pre-wrap; }
  .meta { color:var(--muted); font-size:12px; margin:6px 0; }
  .status { font-weight:600; border-radius:6px; padding:1px 6px; }
  .status.answered { color:var(--ok); background:var(--okbg); }
  .status.waiting_for_user { color:var(--wait); background:var(--waitbg); }
  .status.provider_error, .status.max_tool_rounds { color:var(--err); background:var(--errbg); }
  .tool { border:1px solid var(--line); border-left:4px solid var(--muted); background:var(--panel); border-radius:8px; padding:8px 10px; margin:6px 0; }
  .tool.ok { border-left-color:var(--ok); }
  .tool.error { border-left-color:var(--err); background:var(--errbg); }
  .tool.wait { border-left-color:var(--wait); }
  .tool h3 { font-size:13px; margin:0 0 4px; font-family:ui-monospace, monospace; }
  .label { color:var(--muted); font-size:12px; margin-top:4px; }
  pre { margin:2px 0 0; padding:6px 8px; background:var(--bg); border-radius:6px; overflow-x:auto; font-size:12px; white-space:pre-wrap; overflow-wrap:anywhere; }
  .agent { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:8px 12px; margin-right:15%; white-space:pre-wrap; }
  .agent.error { color:var(--err); }
  form { position:fixed; bottom:0; left:0; right:0; background:var(--panel); border-top:1px solid var(--line); padding:10px 16px; }
  .row { max-width:960px; margin:0 auto; display:flex; gap:8px; }
  textarea { flex:1; resize:vertical; min-height:44px; font:inherit; padding:8px; border:1px solid var(--line); border-radius:8px; background:var(--bg); color:var(--text); }
  button { font:inherit; padding:8px 14px; border-radius:8px; border:1px solid var(--line); background:var(--text); color:var(--bg); cursor:pointer; }
  button:disabled { opacity:.5; cursor:wait; }
</style>
</head>
<body>
<header>
  <h1>IT Helpdesk Agent</h1>
  <span class="badge" id="version">…</span>
  <span class="badge" id="model">…</span>
  <span class="badge" id="transcript">transcript: …</span>
  <button type="button" id="reset">Phiên mới</button>
</header>
<main id="log"></main>
<form id="form">
  <div class="row">
    <textarea id="input" placeholder="Nhập yêu cầu hỗ trợ IT (Enter để gửi, Shift+Enter xuống dòng)"></textarea>
    <button id="send">Gửi</button>
  </div>
</form>
<script>
const log = document.getElementById("log");
const input = document.getElementById("input");
const send = document.getElementById("send");
let sessionId = null;

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

function toolClass(result) {
  if (result && typeof result === "object") {
    if (result.error || result.status === "blocked") return "tool error";
    if (result.awaiting_user) return "tool wait";
    return "tool ok";
  }
  return "tool";
}

async function api(path, body) {
  const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

async function newSession() {
  const data = await api("/api/session");
  sessionId = data.session_id;
  document.getElementById("version").textContent = "version: " + data.artifact_version;
  document.getElementById("model").textContent = data.provider + " / " + data.model;
  document.getElementById("transcript").textContent = "transcript: " + data.transcript_path;
  log.replaceChildren();
}

function renderTurn(turn) {
  const box = log.lastElementChild;
  const meta = el("div", "meta");
  meta.append("Lượt " + turn.turn_index + " · ");
  meta.append(el("span", "status " + turn.status, turn.status));
  box.append(meta);
  for (const round of turn.rounds || []) {
    for (const event of round.tool_results || []) {
      const card = el("div", toolClass(event.result));
      card.append(el("h3", "", "round " + round.round + " · " + event.tool));
      card.append(el("div", "label", "input"));
      card.append(el("pre", "", JSON.stringify(event.args, null, 2)));
      card.append(el("div", "label", "kết quả / lỗi"));
      card.append(el("pre", "", JSON.stringify(event.result, null, 2)));
      box.append(card);
    }
  }
  if (turn.status === "provider_error") {
    box.append(el("div", "agent error", turn.error));
  } else {
    box.append(el("div", "agent", turn.assistant_text || ""));
  }
}

async function submit(event) {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || send.disabled) return;
  const box = el("div", "turn");
  box.append(el("div", "user", text));
  log.append(box);
  input.value = "";
  send.disabled = true;
  try {
    renderTurn(await api("/api/chat", { session_id: sessionId, message: text }));
  } catch (err) {
    box.append(el("div", "agent error", "Lỗi UI/server: " + err.message));
  } finally {
    send.disabled = false;
    input.focus();
    window.scrollTo(0, document.body.scrollHeight);
  }
}

document.getElementById("form").addEventListener("submit", submit);
input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) submit(e); });
document.getElementById("reset").addEventListener("click", newSession);
newSession();
</script>
</body>
</html>
"""


def make_handler(config: AppConfig, sessions: dict[str, ChatSession]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(length).decode("utf-8") or "{}")

        def do_GET(self) -> None:
            if self.path == "/":
                body = PAGE.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/api/info":
                self._send_json(HTTPStatus.OK, config.info())
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self) -> None:
            try:
                body = self._read_json()
            except json.JSONDecodeError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
                return
            if self.path == "/api/session":
                session = ChatSession(config)
                sessions[session.session_id] = session
                self._send_json(HTTPStatus.OK, {
                    "session_id": session.session_id,
                    **config.info(),
                    "transcript_path": str(session.transcript_path.relative_to(ROOT)),
                })
            elif self.path == "/api/chat":
                session = sessions.get(str(body.get("session_id")))
                message = str(body.get("message") or "").strip()
                if session is None:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "unknown_session"})
                elif not message:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "empty_message"})
                else:
                    self._send_json(HTTPStatus.OK, session.send(message))
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Local web chat UI for the IT Helpdesk Agent with transcript logging.")
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "gemini"], required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--version", required=True, help="Artifact version label shown in the UI, e.g. v4.")
    parser.add_argument("--system-prompt", type=Path, default=ARTIFACTS_DIR / "system_prompt.md")
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    parser.add_argument("--transcripts-dir", type=Path, default=ROOT / "transcripts" / "ui")
    parser.add_argument("--history-window", type=int, default=5)
    parser.add_argument("--max-tool-rounds", type=int, default=4)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    config = AppConfig(args)
    server = HTTPServer((args.host, args.port), make_handler(config, {}))
    print(f"IT Helpdesk web UI: http://{args.host}:{args.port}  artifact_version={config.artifact_version.artifact_version}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
