"""
web_ui.py — Gradio Chat UI for the IT Helpdesk Agent (starter_v0)

Usage:
    python web_ui.py --provider openrouter --version v1
    python web_ui.py --provider openrouter --version v1 --share   # public link

The UI:
  - Sends each user message through run_model_tool_loop (same path as chat.py)
  - Displays the assistant reply in the chat window
  - Shows a collapsible "Tool trace" panel with tool calls + results
  - Auto-saves every turn to transcripts/<version>_<provider>_<timestamp>.transcript.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — allow running from any cwd
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"

from chat import (  # noqa: E402 — must come after sys.path insert
    run_model_tool_loop,
    trim_history,
    write_transcript,
    now_iso,
    safe_slug,
)
from env_loader import load_lab_env  # noqa: E402
from providers import make_provider  # noqa: E402
from tools import load_tool_declarations, to_openai_tools  # noqa: E402
from versioning import artifact_version_dict, build_artifact_version  # noqa: E402

import gradio as gr  # noqa: E402

load_lab_env(ROOT)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_TOOL_ROUNDS = 4
HISTORY_WINDOW = 6  # keep last N user/assistant pairs in LLM context

# ---------------------------------------------------------------------------
# CLI args — parsed once at module load so Gradio picks them up
# ---------------------------------------------------------------------------
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gradio Web UI for IT Helpdesk Agent.")
    parser.add_argument(
        "--provider",
        choices=["openrouter", "openai", "anthropic", "gemini"],
        default="openrouter",
    )
    parser.add_argument("--model", default=None, help="Optional model override.")
    parser.add_argument("--version", default="v1", help="Artifact version label, e.g. v1, v2.")
    parser.add_argument(
        "--system-prompt",
        type=Path,
        default=ARTIFACTS_DIR / "system_prompt.md",
    )
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public Gradio share link.",
    )
    # Gradio injects its own args when launched; use parse_known_args to avoid conflicts
    args, _ = parser.parse_known_args()
    return args


ARGS = _parse_args()

# ---------------------------------------------------------------------------
# Agent resources — loaded once at startup
# ---------------------------------------------------------------------------
_system_prompt = ARGS.system_prompt.read_text(encoding="utf-8")
_tool_declarations = load_tool_declarations(ARGS.tools)
_openai_tools = to_openai_tools(_tool_declarations)
_provider = make_provider(ARGS.provider)
_selected_model = ARGS.model or getattr(_provider, "default_model", None)
_artifact_version = build_artifact_version(ARGS.version, ARGS.system_prompt, ARGS.tools)

# ---------------------------------------------------------------------------
# Transcript helpers
# ---------------------------------------------------------------------------
def _new_transcript(transcript_id: str) -> dict[str, Any]:
    return {
        "transcript_id": transcript_id,
        **artifact_version_dict(_artifact_version),
        "provider": ARGS.provider,
        "model": _selected_model,
        "system_prompt": str(ARGS.system_prompt),
        "tools": str(ARGS.tools),
        "history_window": HISTORY_WINDOW,
        "max_tool_rounds": MAX_TOOL_ROUNDS,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }


def _transcript_path(transcript_id: str) -> Path:
    return TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"


# ---------------------------------------------------------------------------
# Tool trace formatter — renders calls + results as readable Markdown
# ---------------------------------------------------------------------------
def _format_tool_trace(tool_events: list[dict[str, Any]]) -> str:
    if not tool_events:
        return "_No tool calls in this turn._"
    lines: list[str] = []
    for i, event in enumerate(tool_events, start=1):
        tool_name = event.get("tool", "?")
        args = event.get("args", {})
        result = event.get("result", {})
        lines.append(f"**{i}. `{tool_name}`**")
        lines.append(f"```json\n// args\n{json.dumps(args, ensure_ascii=False, indent=2)}\n```")
        result_text = json.dumps(result, ensure_ascii=False, indent=2)
        # Truncate very long results so the UI stays readable
        if len(result_text) > 1200:
            result_text = result_text[:1200] + "\n… (truncated)"
        lines.append(f"```json\n// result\n{result_text}\n```")
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Core chat handler — called by Gradio on each user message
# ---------------------------------------------------------------------------
def _chat(
    user_text: str,
    chat_history: list[dict[str, str]],
    session_state: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, Any], str]:
    """
    Returns:
        chat_history  — updated list of {"role": ..., "content": ...}
        session_state — updated state dict (transcript, history, etc.)
        tool_trace    — Markdown string shown in the tool trace panel
    """
    user_text = user_text.strip()
    if not user_text:
        return chat_history, session_state, "_No tool calls in this turn._"

    # ---- Initialise session on first turn ----
    if not session_state.get("transcript_id"):
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        tid = "_".join([safe_slug(ARGS.version), safe_slug(ARGS.provider), timestamp])
        session_state["transcript_id"] = tid
        session_state["transcript"] = _new_transcript(tid)
        session_state["lm_history"] = []  # LLM context window (role/content pairs)
        session_state["turn_index"] = 0

    session_state["turn_index"] += 1
    lm_history: list[dict[str, str]] = session_state["lm_history"]

    # ---- Build messages for LLM ----
    messages = [
        {"role": "system", "content": _system_prompt},
        *trim_history(lm_history, HISTORY_WINDOW),
        {"role": "user", "content": user_text},
    ]

    turn_record: dict[str, Any] = {
        "turn_index": session_state["turn_index"],
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    try:
        result = run_model_tool_loop(
            provider=_provider,
            messages=messages,
            tools=_openai_tools,
            model=ARGS.model,
            max_tool_rounds=MAX_TOOL_ROUNDS,
        )
        turn_record.update(result)
        assistant_text = result["assistant_text"]
        tool_events = result.get("tool_events", [])
    except Exception as exc:
        assistant_text = f"⚠️ Error: {type(exc).__name__}: {exc}"
        tool_events = []
        turn_record.update({"status": "provider_error", "error": assistant_text})

    # ---- Update LLM context history ----
    lm_history.append({"role": "user", "content": user_text})
    lm_history.append({"role": "assistant", "content": assistant_text})
    session_state["lm_history"] = lm_history

    # ---- Update Gradio chat history ----
    chat_history = chat_history + [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": assistant_text},
    ]

    # ---- Save transcript ----
    turn_record["ended_at"] = now_iso()
    session_state["transcript"]["turns"].append(turn_record)
    write_transcript(
        _transcript_path(session_state["transcript_id"]),
        session_state["transcript"],
    )

    tool_trace_md = _format_tool_trace(tool_events)
    return chat_history, session_state, tool_trace_md


# ---------------------------------------------------------------------------
# Gradio UI layout
# ---------------------------------------------------------------------------
def _build_ui() -> gr.Blocks:
    with gr.Blocks(title="IT Helpdesk Agent — Northstar Labs", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            f"""
# 🖥️ IT Helpdesk Agent — Northstar Labs
**Provider:** `{ARGS.provider}` &nbsp;|&nbsp;
**Model:** `{_selected_model}` &nbsp;|&nbsp;
**Version:** `{ARGS.version}` &nbsp;|&nbsp;
**Artifact:** `{_artifact_version.artifact_version}`

Trợ lý hỗ trợ IT nội bộ. Hỏi về trạng thái dịch vụ, kiểm tra thiết bị,
tra cứu nhân viên, hướng dẫn kỹ thuật, hoặc tạo ticket hỗ trợ.
"""
        )

        # ---- Session state (persisted per browser tab) ----
        session_state = gr.State({})

        with gr.Row():
            # Left column — chat
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Conversation",
                    height=520,
                    type="messages",
                    show_copy_button=True,
                    bubble_full_width=False,
                )
                with gr.Row():
                    msg_box = gr.Textbox(
                        placeholder="Nhập câu hỏi... (Enter để gửi)",
                        label="",
                        scale=5,
                        lines=1,
                        autofocus=True,
                    )
                    send_btn = gr.Button("Gửi", variant="primary", scale=1)
                clear_btn = gr.Button("🗑️ Xoá hội thoại", variant="secondary", size="sm")

            # Right column — tool trace
            with gr.Column(scale=2):
                gr.Markdown("### 🔧 Tool trace (lượt gần nhất)")
                tool_trace = gr.Markdown(
                    value="_Tool calls sẽ hiện ở đây sau khi bạn gửi tin nhắn._",
                    label="Tool trace",
                )
                with gr.Accordion("ℹ️ Transcript path", open=False):
                    transcript_info = gr.Markdown(
                        f"Transcripts lưu tại: `{TRANSCRIPTS_DIR}`"
                    )

        # ---- Wiring ----
        def _submit(user_text, history, state):
            new_history, new_state, trace = _chat(user_text, history, state)
            return new_history, new_state, trace, ""  # clear textbox

        submit_inputs = [msg_box, chatbot, session_state]
        submit_outputs = [chatbot, session_state, tool_trace, msg_box]

        msg_box.submit(_submit, inputs=submit_inputs, outputs=submit_outputs)
        send_btn.click(_submit, inputs=submit_inputs, outputs=submit_outputs)

        def _clear(state):
            # Reset conversation but keep transcript_id so file is preserved
            state["lm_history"] = []
            state["turn_index"] = state.get("turn_index", 0)
            return [], state, "_Tool calls sẽ hiện ở đây sau khi bạn gửi tin nhắn._"

        clear_btn.click(_clear, inputs=[session_state], outputs=[chatbot, session_state, tool_trace])

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    demo = _build_ui()
    print(f"Starting IT Helpdesk Agent Web UI")
    print(f"  provider : {ARGS.provider}")
    print(f"  model    : {_selected_model}")
    print(f"  version  : {ARGS.version}")
    print(f"  artifact : {_artifact_version.artifact_version}")
    print(f"  transcripts → {TRANSCRIPTS_DIR}")
    demo.launch(share=ARGS.share, inbrowser=True)


if __name__ == "__main__":
    main()
