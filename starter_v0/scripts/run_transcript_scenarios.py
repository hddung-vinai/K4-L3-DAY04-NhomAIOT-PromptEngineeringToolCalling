from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay scripted conversations through chat.py and save real transcripts.")
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "gemini"], required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--scenarios", type=Path, default=Path(__file__).with_name("transcript_scenarios.json"))
    parser.add_argument("--transcripts-dir", type=Path, default=ROOT / "transcripts")
    parser.add_argument("--only", nargs="*", default=None, help="Scenario ids to run; default runs all.")
    args = parser.parse_args()

    scenarios = json.loads(args.scenarios.read_text(encoding="utf-8"))["scenarios"]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for scenario in scenarios:
        if args.only and scenario["id"] not in args.only:
            continue
        print(f"===== {scenario['id']}: {scenario['goal']}", flush=True)
        stdin_text = "\n".join([*scenario["turns"], "/exit"]) + "\n"
        proc = subprocess.run(
            [
                sys.executable, "chat.py",
                "--provider", args.provider,
                "--version", args.version,
                "--transcripts-dir", str(args.transcripts_dir / scenario["id"]),
            ],
            input=stdin_text,
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=ROOT,
            env=env,
        )
        print(proc.stdout, flush=True)
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
