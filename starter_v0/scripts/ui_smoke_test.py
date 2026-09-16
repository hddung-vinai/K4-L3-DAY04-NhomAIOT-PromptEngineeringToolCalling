"""
ui_smoke_test.py — Smoke test for the Web UI agent pipeline (starter_v0)

Tests that the full agent stack (provider → run_model_tool_loop → tool execution)
works correctly end-to-end for three representative cases used in the Web UI:

  Case 1 — routing     : "Kiểm tra VPN production" must call check_service_status
  Case 2 — clarify     : "Kiểm tra laptop của mình" must call clarify (missing asset_id)
  Case 3 — out-of-scope: "Gợi ý công thức nấu phở" must return no tool calls

Usage:
    python scripts/ui_smoke_test.py --provider openrouter
    python scripts/ui_smoke_test.py --provider openrouter --model openai/gpt-4o-mini
    python scripts/ui_smoke_test.py --provider openrouter --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — same pattern as scripts/preflight_provider.py
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ARTIFACTS_DIR = ROOT / "artifacts"

from chat import run_model_tool_loop  # noqa: E402
from env_loader import load_lab_env  # noqa: E402
from providers import make_provider  # noqa: E402
from tools import load_tool_declarations, to_openai_tools  # noqa: E402

load_lab_env(ROOT)

# ---------------------------------------------------------------------------
# Test case definitions
# ---------------------------------------------------------------------------
SMOKE_CASES: list[dict[str, Any]] = [
    {
        "id": "UI_S01_routing",
        "description": "Service status query phải gọi check_service_status",
        "user": "Kiểm tra trạng thái dịch vụ VPN production giúp mình.",
        "expect_tool": "check_service_status",
        "expect_no_tool": False,
    },
    {
        "id": "UI_S02_clarify_missing_asset",
        "description": "Thiếu asset ID phải gọi clarify để hỏi lại",
        "user": "Kiểm tra Wi-Fi trên laptop của mình giúp nhé.",
        "expect_tool": "clarify",
        "expect_no_tool": False,
    },
    {
        "id": "UI_S03_out_of_scope",
        "description": "Yêu cầu ngoài IT helpdesk không được gọi tool nào",
        "user": "Gợi ý cho mình công thức nấu phở bò.",
        "expect_tool": None,
        "expect_no_tool": True,
    },
]

# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------
PASS = "PASS"
FAIL = "FAIL"

def _check(case: dict[str, Any], result: dict[str, Any], verbose: bool) -> tuple[str, str]:
    """
    Returns (status, reason).
    status is PASS or FAIL.
    reason is empty string on PASS, descriptive on FAIL.
    """
    tool_events: list[dict[str, Any]] = result.get("tool_events", [])
    called_tools = [e["tool"] for e in tool_events]

    if case["expect_no_tool"]:
        if called_tools:
            return FAIL, f"Expected no tool calls, got: {called_tools}"
        return PASS, ""

    expected = case["expect_tool"]
    if expected not in called_tools:
        return FAIL, f"Expected tool '{expected}', got: {called_tools or '(none)'}"

    return PASS, ""


def _print_result(
    case: dict[str, Any],
    status: str,
    reason: str,
    result: dict[str, Any],
    verbose: bool,
) -> None:
    icon = "✓" if status == PASS else "✗"
    print(f"  {icon} [{status}] {case['id']} — {case['description']}")
    if status == FAIL:
        print(f"        → {reason}")
    if verbose:
        tool_events = result.get("tool_events", [])
        if tool_events:
            for ev in tool_events:
                args_str = json.dumps(ev.get("args", {}), ensure_ascii=False)
                print(f"        tool: {ev['tool']}  args: {args_str}")
        else:
            print(f"        tool_calls: (none)  status: {result.get('status')}")
        if result.get("assistant_text"):
            snippet = result["assistant_text"][:120].replace("\n", " ")
            print(f"        reply: {snippet}…")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test for Web UI agent pipeline.")
    parser.add_argument(
        "--provider",
        choices=["openrouter", "openai", "anthropic", "gemini"],
        required=True,
    )
    parser.add_argument("--model", default=None, help="Optional model override.")
    parser.add_argument(
        "--tools",
        type=Path,
        default=ARTIFACTS_DIR / "tools.yaml",
    )
    parser.add_argument(
        "--system-prompt",
        type=Path,
        default=ARTIFACTS_DIR / "system_prompt.md",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print tool calls and reply snippet for every case.",
    )
    args = parser.parse_args()

    # ---- Load agent resources ----
    system_prompt = args.system_prompt.read_text(encoding="utf-8")
    openai_tools = to_openai_tools(load_tool_declarations(args.tools))
    provider = make_provider(args.provider)
    selected_model = args.model or getattr(provider, "default_model", None)

    print(f"\nUI Smoke Test — provider={args.provider}  model={selected_model}")
    print(f"system_prompt : {args.system_prompt}")
    print(f"tools         : {args.tools}")
    print("-" * 60)

    passed = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    for case in SMOKE_CASES:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": case["user"]},
        ]
        try:
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=openai_tools,
                model=args.model,
                max_tool_rounds=4,
            )
        except Exception as exc:
            result = {
                "status": "provider_error",
                "assistant_text": f"{type(exc).__name__}: {exc}",
                "tool_events": [],
                "rounds": [],
            }

        status, reason = _check(case, result, args.verbose)
        _print_result(case, status, reason, result, args.verbose)

        if status == PASS:
            passed += 1
        else:
            failed += 1
            failures.append((case["id"], reason))

    # ---- Summary ----
    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed  (total {len(SMOKE_CASES)})")

    if failures:
        print("\nFailed cases:")
        for case_id, reason in failures:
            print(f"  • {case_id}: {reason}")
        raise SystemExit(f"\nSmoke test FAILED ({failed} case(s)). Fix agent pipeline before running Web UI.")

    print("\nAll smoke tests passed. Web UI pipeline is healthy.")


if __name__ == "__main__":
    main()
