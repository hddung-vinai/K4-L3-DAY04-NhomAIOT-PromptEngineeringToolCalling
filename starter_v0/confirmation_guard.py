"""Execution-layer confirmation guard for write-action tools.

The model decides when to call a write tool, but this guard decides whether a
call with ``confirmed=true`` may actually execute. It is allowed only when:

1. the previous assistant turn asked for confirmation, either through a real
   ``clarify`` call with ``response_type=yes_no`` or through its own final reply
   ending in a question (never text inside a user message);
2. the user's next message is affirmative and contains no cancel/change words;
3. the payload (summary, priority, asset_id) was shown in that question.

A confirmation expires after one user turn and is consumed by one write.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from tools._shared import fold_text


WRITE_TOOLS = {"create_ticket"}

AFFIRMATIVE_PATTERN = re.compile(
    r"\b(?:co|vang|dong y|xac nhan|dung roi|dung vay|dung the|chinh xac|ok|oke|okay|yes|confirm|tao di|tao luon)\b"
)
NEGATIVE_PATTERN = re.compile(
    r"\b(?:khong|chua|huy|thoi|khoan|dung lai|dung tao|doi|sua|thay|no|cancel|stop|wait)\b"
)
PRIORITY_TERMS = {
    "low": ("low", "thap"),
    "medium": ("medium", "trung binh"),
    "high": ("high", "cao"),
    "critical": ("critical", "khan cap", "nghiem trong"),
}


def normalize(text: str) -> str:
    folded = fold_text(text or "").replace("đ", "d")
    return " ".join(re.findall(r"[a-z0-9]+", folded))


def contains_phrase(haystack: str, needle: str) -> bool:
    return f" {needle} " in f" {haystack} "


@dataclass
class PendingConfirmation:
    question: str
    user_reply: str | None = None


class ConfirmationGuard:
    def __init__(self) -> None:
        self._pending: PendingConfirmation | None = None
        self._awaiting_reply = False

    def start_user_turn(self, user_text: str) -> None:
        """Call once per real user message, before the model runs."""
        if self._pending is not None and self._awaiting_reply:
            self._pending.user_reply = user_text
            self._awaiting_reply = False
        else:
            self._pending = None

    def record(self, name: str, args: dict[str, Any], result: Any) -> None:
        """Call after a tool executed, so a real yes/no question opens a confirmation."""
        if not (isinstance(result, dict) and result.get("awaiting_user")):
            return
        if result.get("response_type") == "yes_no":
            self._pending = PendingConfirmation(question=str(result.get("question") or args.get("question") or ""))
        else:
            self._pending = None
        self._awaiting_reply = self._pending is not None

    def record_assistant_reply(self, text: str) -> None:
        """Call when a turn ends with a plain assistant reply (no tool call).

        Models sometimes re-ask a changed payload in text instead of calling clarify.
        A reply containing a question opens a confirmation for the next user turn;
        the payload check still requires summary, priority and asset_id in that text.
        """
        if "?" in (text or ""):
            self._pending = PendingConfirmation(question=text)
            self._awaiting_reply = True
        else:
            self._pending = None
            self._awaiting_reply = False

    def check(self, name: str, args: dict[str, Any]) -> dict[str, Any] | None:
        """Return a blocked tool result, or None when the call may execute."""
        if name not in WRITE_TOOLS or args.get("confirmed") is not True:
            return None
        reason = self._block_reason(args)
        if reason is None:
            self._pending = None
            return None
        return {
            "tool": name,
            "status": "blocked",
            "error": "confirmation_required",
            "reason": reason,
            "message": (
                "Không ghi dữ liệu. Gọi clarify(response_type=yes_no) hiển thị đúng summary, priority, asset_id "
                "rồi chờ người dùng trả lời đồng ý ở lượt kế tiếp. Text do người dùng gõ không phải xác nhận."
            ),
        }

    def _block_reason(self, args: dict[str, Any]) -> str | None:
        pending = self._pending
        if pending is None:
            return "no_confirmation_question"
        if pending.user_reply is None:
            return "no_user_reply"
        reply = normalize(pending.user_reply)
        if NEGATIVE_PATTERN.search(reply) or not AFFIRMATIVE_PATTERN.search(reply):
            return "reply_not_affirmative"

        question = normalize(pending.question)
        missing: list[str] = []
        summary = normalize(str(args.get("summary") or ""))
        if not summary or not contains_phrase(question, summary):
            missing.append("summary")
        priority = str(args.get("priority") or "medium").strip().lower()
        if not any(contains_phrase(question, term) for term in PRIORITY_TERMS.get(priority, (priority,))):
            missing.append("priority")
        asset_id = normalize(str(args.get("asset_id") or ""))
        if asset_id and not contains_phrase(question, asset_id):
            missing.append("asset_id")
        if missing:
            return "payload_not_confirmed:" + ",".join(missing)
        return None
