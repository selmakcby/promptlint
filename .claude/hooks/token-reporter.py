#!/usr/bin/env python3
"""promptlint — Stop hook that prints a token usage box after each Claude response.

Reads the session JSONL transcript (path provided via stdin payload) and
prints a 3-line summary to stderr:
  - Last turn: input/output/cache breakdown + cost
  - Session totals + cumulative cost
  - Model family auto-detected for pricing

Pop-up is silenced when ~/.claude/promptlint.disabled exists.
"""
import json
import os
import sys
from pathlib import Path

PRICING = {
    "opus":   {"input": 15.00, "output": 75.00, "cache_write": 18.75, "cache_read": 1.50},
    "sonnet": {"input":  3.00, "output": 15.00, "cache_write":  3.75, "cache_read": 0.30},
    "haiku":  {"input":  0.80, "output":  4.00, "cache_write":  1.00, "cache_read": 0.08},
}

# Token reporter has its OWN state file, independent of the prompt filter.
# This way you can see token costs even with prompt filter off.
# Default: ON (token visibility is harmless and useful).
TOKEN_OFF_FILE = Path.home() / ".claude" / "promptlint.tokens.disabled"


def fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def detect_family(model: str) -> str:
    m = (model or "").lower()
    if "opus" in m:
        return "opus"
    if "haiku" in m:
        return "haiku"
    return "sonnet"


def calc_cost(usage: dict, family: str) -> float:
    p = PRICING[family]
    return (
        usage.get("input", 0) * p["input"]
        + usage.get("output", 0) * p["output"]
        + usage.get("cache_write", 0) * p["cache_write"]
        + usage.get("cache_read", 0) * p["cache_read"]
    ) / 1_000_000


def main() -> int:
    # Silenced only if user explicitly disabled token reporter
    if TOKEN_OFF_FILE.exists():
        return 0

    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    transcript = payload.get("transcript_path")
    if not transcript or not Path(transcript).exists():
        return 0

    session_total = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    last_turn = None
    last_model = "unknown"

    try:
        with open(transcript, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") != "assistant":
                    continue
                msg = obj.get("message", {}) or {}
                usage = msg.get("usage", {}) or {}
                if not usage:
                    continue
                turn = {
                    "input":       usage.get("input_tokens", 0) or 0,
                    "output":      usage.get("output_tokens", 0) or 0,
                    "cache_write": usage.get("cache_creation_input_tokens", 0) or 0,
                    "cache_read":  usage.get("cache_read_input_tokens", 0) or 0,
                }
                for k, v in turn.items():
                    session_total[k] += v
                last_turn = turn
                if msg.get("model"):
                    last_model = msg["model"]
    except (FileNotFoundError, PermissionError):
        return 0

    if not last_turn:
        return 0

    family = detect_family(last_model)
    last_cost = calc_cost(last_turn, family)
    session_cost = calc_cost(session_total, family)
    last_total = sum(last_turn.values())
    session_total_tok = sum(session_total.values())

    # Pretty box
    box = [
        "",
        "┌─ 📊 PROMPTLINT · TOKEN ───────────────────────────────────────┐",
        f"│ son turn  · in {fmt(last_turn['input']):>6}  out {fmt(last_turn['output']):>6}  cw {fmt(last_turn['cache_write']):>6}  cr {fmt(last_turn['cache_read']):>6}  ${last_cost:>7.4f}",
        f"│ oturum    · top {fmt(session_total_tok):>5}  ({family})                       ${session_cost:>7.4f}",
        "└───────────────────────────────────────────────────────────────┘",
    ]
    print("\n".join(box), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
