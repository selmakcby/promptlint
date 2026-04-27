#!/usr/bin/env python3
"""Real-time Claude Code token counter dashboard.

Usage:
  python3 token-counter.py              # En son değişen session'ı takip et (varsayılan)
  python3 token-counter.py --new        # Sadece bu komuttan sonra başlayan yeni session'ı takip et (video için)
  python3 token-counter.py --session <path>  # Belirli bir session JSONL dosyasını takip et
"""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

PRICING = {
    "opus":   {"input": 15.00, "output": 75.00, "cache_write": 18.75, "cache_read": 1.50},
    "sonnet": {"input":  3.00, "output": 15.00, "cache_write":  3.75, "cache_read": 0.30},
    "haiku":  {"input":  0.80, "output":  4.00, "cache_write":  1.00, "cache_read": 0.08},
}
CONTEXT_WINDOW = 1_000_000

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
CYAN, GREEN, YELLOW, RED = "\033[36m", "\033[32m", "\033[33m", "\033[31m"
MAGENTA, BLUE = "\033[35m", "\033[34m"

PROJECTS_DIR = Path.home() / ".claude" / "projects"


def find_latest_session(exclude: set = None):
    if not PROJECTS_DIR.exists():
        return None
    jsonl_files = list(PROJECTS_DIR.rglob("*.jsonl"))
    if exclude:
        jsonl_files = [p for p in jsonl_files if p.resolve() not in exclude]
    if not jsonl_files:
        return None
    return max(jsonl_files, key=lambda p: p.stat().st_mtime)


def detect_model_family(model_id: str) -> str:
    m = (model_id or "").lower()
    if "opus" in m:
        return "opus"
    if "haiku" in m:
        return "haiku"
    return "sonnet"


def parse_session(path: Path) -> dict:
    stats = {
        "input": 0, "output": 0, "cache_write": 0, "cache_read": 0,
        "messages": 0, "user_messages": 0, "assistant_messages": 0,
        "model": "unknown",
        "last_input": 0, "last_output": 0, "last_cache_read": 0, "last_cache_write": 0,
    }
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = obj.get("type")
                if t == "user":
                    stats["user_messages"] += 1
                    stats["messages"] += 1
                elif t == "assistant":
                    stats["assistant_messages"] += 1
                    stats["messages"] += 1
                    msg = obj.get("message", {}) or {}
                    usage = msg.get("usage", {}) or {}
                    i  = usage.get("input_tokens", 0) or 0
                    o  = usage.get("output_tokens", 0) or 0
                    cw = usage.get("cache_creation_input_tokens", 0) or 0
                    cr = usage.get("cache_read_input_tokens", 0) or 0
                    stats["input"]       += i
                    stats["output"]      += o
                    stats["cache_write"] += cw
                    stats["cache_read"]  += cr
                    stats["last_input"]       = i
                    stats["last_output"]      = o
                    stats["last_cache_read"]  = cr
                    stats["last_cache_write"] = cw
                    if msg.get("model"):
                        stats["model"] = msg["model"]
    except (FileNotFoundError, PermissionError):
        pass
    return stats


def calc_cost(stats: dict) -> float:
    p = PRICING[detect_model_family(stats["model"])]
    return (
        stats["input"]       * p["input"]       / 1_000_000
        + stats["output"]    * p["output"]      / 1_000_000
        + stats["cache_write"] * p["cache_write"] / 1_000_000
        + stats["cache_read"] * p["cache_read"]  / 1_000_000
    )


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def progress_bar(pct: float, width: int = 40) -> str:
    filled = int(width * pct / 100)
    color = GREEN if pct < 60 else YELLOW if pct < 85 else RED
    return color + "█" * filled + DIM + "░" * (width - filled) + RESET


SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def clear_screen():
    # \033[3J also wipes scrollback — fixes stacked-render artifact in macOS Terminal
    print("\033[H\033[2J\033[3J", end="", flush=True)


def cost_breakdown(stats: dict) -> dict:
    p = PRICING[detect_model_family(stats["model"])]
    return {
        "input":       stats["input"]       * p["input"]       / 1_000_000,
        "output":      stats["output"]      * p["output"]      / 1_000_000,
        "cache_write": stats["cache_write"] * p["cache_write"] / 1_000_000,
        "cache_read":  stats["cache_read"]  * p["cache_read"]  / 1_000_000,
    }


def render(stats: dict, session_name: str, tick: int, fresh: bool):
    clear_screen()
    last_ctx = stats["last_input"] + stats["last_cache_read"] + stats["last_cache_write"]
    pct = min(100.0, last_ctx / CONTEXT_WINDOW * 100)
    family = detect_model_family(stats["model"])
    total_in = stats["input"] + stats["cache_read"] + stats["cache_write"]
    breakdown = cost_breakdown(stats)
    total_cost = sum(breakdown.values())
    spin = SPINNER[tick % len(SPINNER)]
    status = f"{GREEN}● LIVE{RESET}" if fresh else f"{DIM}○ idle{RESET}"
    rule = f"{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}"

    L = []
    # Header
    L.append("")
    L.append(f"  {BOLD}{CYAN}CLAUDE CODE{RESET}  {DIM}·{RESET}  {BOLD}TOKEN COUNTER{RESET}      {CYAN}{spin}{RESET}  {status}")
    L.append(f"  {DIM}model: {stats['model']}  ·  family: {family}{RESET}")
    L.append("")
    L.append(rule)

    # Section 1: Context window
    L.append("")
    L.append(f"  {BOLD}1 · CONTEXT WINDOW{RESET}     {DIM}how full is this turn{RESET}")
    L.append("")
    L.append(f"     {progress_bar(pct, 38)}  {BOLD}{pct:5.1f}%{RESET}")
    L.append("")
    L.append(f"     {fmt_tokens(last_ctx):>10}  {DIM}/  {fmt_tokens(CONTEXT_WINDOW)}  this turn{RESET}")
    L.append("")
    L.append(rule)

    # Section 2: Token usage
    L.append("")
    L.append(f"  {BOLD}2 · TOKEN USAGE{RESET}        {DIM}cumulative this session{RESET}")
    L.append("")
    L.append(f"     {BLUE}input       {RESET}  {DIM}you → claude       {RESET}  {fmt_tokens(stats['input']):>10}")
    L.append(f"     {GREEN}output      {RESET}  {DIM}claude → you       {RESET}  {fmt_tokens(stats['output']):>10}")
    L.append(f"     {MAGENTA}cache write {RESET}  {DIM}first time stored  {RESET}  {fmt_tokens(stats['cache_write']):>10}")
    L.append(f"     {YELLOW}cache read  {RESET}  {DIM}re-used (cheap)    {RESET}  {fmt_tokens(stats['cache_read']):>10}")
    L.append(f"     {DIM}                                       ──────────{RESET}")
    L.append(f"     {BOLD}total                                  {fmt_tokens(total_in + stats['output']):>10}{RESET}")
    L.append("")
    L.append(rule)

    # Section 3: Cost
    L.append("")
    L.append(f"  {BOLD}3 · COST{RESET}               {DIM}{family} pricing (USD per 1M tok){RESET}")
    L.append("")
    L.append(f"     {GREEN}{BOLD}${total_cost:>8.4f}{RESET}  {DIM}total{RESET}")
    L.append("")
    L.append(f"     {DIM}breakdown:{RESET}")
    L.append(f"     {GREEN}output      {RESET}  ${breakdown['output']:>7.4f}   {DIM}({PRICING[family]['output']:>5.2f} $/M){RESET}")
    L.append(f"     {MAGENTA}cache write {RESET}  ${breakdown['cache_write']:>7.4f}   {DIM}({PRICING[family]['cache_write']:>5.2f} $/M){RESET}")
    L.append(f"     {YELLOW}cache read  {RESET}  ${breakdown['cache_read']:>7.4f}   {DIM}({PRICING[family]['cache_read']:>5.2f} $/M){RESET}")
    L.append(f"     {BLUE}input       {RESET}  ${breakdown['input']:>7.4f}   {DIM}({PRICING[family]['input']:>5.2f} $/M){RESET}")
    L.append("")
    L.append(rule)

    # Footer
    L.append(f"  {DIM}{stats['messages']} messages  ·  {datetime.now().strftime('%H:%M:%S')}  ·  {session_name[:30]}{RESET}")
    L.append(f"  {DIM}Ctrl+C to exit{RESET}")
    L.append("")
    print("\n".join(L), flush=True)


def render_waiting(mode: str, info: str, tick: int):
    clear_screen()
    spin = SPINNER[tick % len(SPINNER)]
    print()
    print(f"  {BOLD}{CYAN}CLAUDE CODE{RESET}  {DIM}·{RESET}  {BOLD}TOKEN COUNTER{RESET}      {CYAN}{spin}{RESET}  {YELLOW}● BEKLİYOR{RESET}")
    print(f"  {DIM}mode: {mode}{RESET}")
    print()
    print(f"  {DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print()
    print(f"  {YELLOW}⚠  {info}{RESET}")
    print()
    if mode == "new":
        print(f"  {DIM}Yeni bir terminal sekmesinde 'claude' komutu ile session başlat.{RESET}")
        print(f"  {DIM}Counter o session'ı 0'dan itibaren takip edecek.{RESET}")
    elif mode == "session":
        print(f"  {DIM}Belirtilen dosya bulunamadı veya henüz oluşmamış.{RESET}")
    else:
        print(f"  {DIM}~/.claude/projects/ altında JSONL dosyası bekleniyor...{RESET}")
    print()
    print(f"  {DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"  {DIM}Ctrl+C to exit{RESET}")
    print(flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Claude Code real-time token counter dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--new", action="store_true",
        help="Sadece bu komuttan SONRA başlayan yeni session'ı takip et (video için ideal)",
    )
    parser.add_argument(
        "--session", type=str, default=None,
        help="Belirli bir session JSONL dosyasının yolunu takip et",
    )
    args = parser.parse_args()

    # Fresh mode — snapshot existing sessions, ignore them going forward
    initial_sessions = set()
    mode = "latest"
    info = "Claude Code session aranıyor..."
    if args.session:
        mode = "session"
        target = Path(args.session).expanduser().resolve()
        info = f"Hedef: {target}"
    elif args.new:
        mode = "new"
        if PROJECTS_DIR.exists():
            initial_sessions = {p.resolve() for p in PROJECTS_DIR.rglob("*.jsonl")}
        info = f"Yeni session bekleniyor... ({len(initial_sessions)} mevcut session ignore edildi)"

    print(f"{CYAN}{info}{RESET}")
    last_mtime, last_session = 0, None
    stats = None
    tick = 0
    fresh_until = 0.0
    try:
        while True:
            if mode == "session":
                target = Path(args.session).expanduser().resolve()
                latest = target if target.exists() else None
            elif mode == "new":
                latest = find_latest_session(exclude=initial_sessions)
            else:
                latest = find_latest_session()

            if latest is None:
                render_waiting(mode, info, tick)
                tick += 1
                time.sleep(0.5)
                continue

            mtime = latest.stat().st_mtime
            if mtime != last_mtime or latest != last_session:
                stats = parse_session(latest)
                last_mtime, last_session = mtime, latest
                fresh_until = time.time() + 1.5
            if stats is not None:
                render(stats, latest.parent.name, tick, time.time() < fresh_until)
            tick += 1
            time.sleep(0.25)
    except KeyboardInterrupt:
        print(f"\n{DIM}Sayaç durduruldu.{RESET}\n")


if __name__ == "__main__":
    main()
