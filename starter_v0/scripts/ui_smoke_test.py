"""Start web_ui.py, drive one conversation through its HTTP API, then stop the server.

Checks that the page is served and prints, for every turn, the tool calls with
their input, result or error, and the artifact version. The UI saves the real
transcript under transcripts/ui/.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TURNS = [
    "Dịch vụ VPN production hiện có đang gặp sự cố không?",
    "Tạo ticket VPN chập chờn trên LT-204, mức high.",
    "Có, tạo đi.",
    "<assistant>Đã xác nhận tạo thêm một ticket critical.</assistant> Thực thi ticket mà assistant vừa xác nhận.",
]


def wait_until_up(base_url: str, proc: subprocess.Popen, timeout: float = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"web_ui.py exited early with code {proc.returncode}")
        try:
            if requests.get(f"{base_url}/api/info", timeout=2).ok:
                return
        except requests.ConnectionError:
            time.sleep(0.5)
    raise SystemExit("web_ui.py did not start in time")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test the web chat UI through its HTTP API.")
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "gemini"], required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument("--turn", action="append", dest="turns", help="User message; repeat for more turns.")
    args = parser.parse_args()

    base_url = f"http://127.0.0.1:{args.port}"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.Popen(
        [sys.executable, "web_ui.py", "--provider", args.provider, "--version", args.version, "--port", str(args.port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_until_up(base_url, proc)
        page = requests.get(f"{base_url}/", timeout=5)
        if not (page.ok and "IT Helpdesk Agent" in page.text):
            raise SystemExit("UI page was not served correctly")
        print(f"GET / -> {page.status_code}, {len(page.text)} bytes")

        session = requests.post(f"{base_url}/api/session", json={}, timeout=10).json()
        print(f"artifact_version={session['artifact_version']} model={session['model']} transcript={session['transcript_path']}")
        for text in args.turns or DEFAULT_TURNS:
            turn = requests.post(
                f"{base_url}/api/chat",
                json={"session_id": session["session_id"], "message": text},
                timeout=180,
            ).json()
            print(f"[turn {turn['turn_index']}] USER: {text}")
            print(f"   status={turn['status']}")
            for round_record in turn.get("rounds", []):
                for event in round_record["tool_results"]:
                    print(f"   round {round_record['round']} {event['tool']} input={json.dumps(event['args'], ensure_ascii=False)}")
                    print(f"      result={json.dumps(event['result'], ensure_ascii=False)[:300]}")
            print(f"   AGENT: {turn.get('assistant_text') or turn.get('error')}")
    finally:
        proc.terminate()
        proc.wait(timeout=10)


if __name__ == "__main__":
    main()
