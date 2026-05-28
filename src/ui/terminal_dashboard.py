"""Interactive terminal dashboard for the local platform gateway (stdlib-only).

Polls `GET /health` every 2 seconds and renders:
- A repository matrix (18 repos) with agent pair + status + semantic memory counts.
- A small performance panel (scheduler buffer + system memory + thread target).
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ANSI_CLEAR = "\x1b[2J\x1b[H"
ANSI_RESET = "\x1b[0m"
ANSI_BOLD = "\x1b[1m"
ANSI_DIM = "\x1b[2m"

FG_RED = "\x1b[31m"
FG_GREEN = "\x1b[32m"
FG_YELLOW = "\x1b[33m"
FG_CYAN = "\x1b[36m"
FG_GRAY = "\x1b[90m"


def _enable_windows_vt() -> None:
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        new_mode = ctypes.c_uint32(mode.value | 0x0004)
        kernel32.SetConsoleMode(handle, new_mode)
    except Exception:
        return


def _http_get_json(url: str, *, timeout_s: float = 3.0) -> dict[str, Any]:
    req = urllib.request.Request(
        url=str(url),
        headers={"Accept": "application/json", "User-Agent": "REMOTE-AGENTS/terminal-dashboard"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=float(timeout_s)) as resp:
        raw = resp.read()
    try:
        obj = json.loads(raw.decode("utf-8", errors="replace"))
    except Exception:
        obj = {}
    return obj if isinstance(obj, dict) else {}


def _format_bytes(n: int | None) -> str:
    if n is None:
        return "n/a"
    try:
        v = float(n)
    except Exception:
        return "n/a"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    idx = 0
    while v >= 1024.0 and idx < len(units) - 1:
        v /= 1024.0
        idx += 1
    if idx <= 1:
        return f"{int(v)} {units[idx]}"
    return f"{v:.2f} {units[idx]}"


def _style_status(status: str) -> str:
    s = str(status or "Idle")
    if s == "Idle":
        return f"{FG_GREEN}{s}{ANSI_RESET}"
    if s == "Processing":
        return f"{FG_YELLOW}{s}{ANSI_RESET}"
    if s == "Error-Locked":
        return f"{FG_RED}{s}{ANSI_RESET}"
    return s


def _pad(text: str, width: int) -> str:
    text = str(text)
    if len(text) >= width:
        return text[: max(0, width - 1)] + "…" if width > 1 else ""
    return text + (" " * (width - len(text)))


def _render_box_table(headers: list[str], rows: list[list[str]]) -> str:
    cols = len(headers)
    widths = [len(h) for h in headers]
    for r in rows:
        for i in range(cols):
            widths[i] = max(widths[i], len(str(r[i]) if i < len(r) else ""))

    def line(left: str, mid: str, right: str, fill: str = "─") -> str:
        parts = [left]
        for i, w in enumerate(widths):
            parts.append(fill * (w + 2))
            parts.append(mid if i < cols - 1 else right)
        return "".join(parts)

    out: list[str] = []
    out.append(line("┌", "┬", "┐"))
    out.append("│ " + " │ ".join(_pad(h, widths[i]) for i, h in enumerate(headers)) + " │")
    out.append(line("├", "┼", "┤"))
    for r in rows:
        out.append("│ " + " │ ".join(_pad(r[i], widths[i]) for i in range(cols)) + " │")
    out.append(line("└", "┴", "┘"))
    return "\n".join(out)


def _load_agent_registry(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    try:
        obj = json.loads(raw)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


@dataclass(frozen=True, slots=True)
class RepoRow:
    name: str
    primary: str
    twin: str


def _repos_from_registry(registry: dict[str, Any]) -> list[RepoRow]:
    repos = registry.get("repositories")
    if not isinstance(repos, dict):
        return []
    rows: list[RepoRow] = []
    for repo_name, profile in repos.items():
        if not isinstance(repo_name, str) or not repo_name.strip():
            continue
        prof = profile if isinstance(profile, dict) else {}
        primary = str(prof.get("primary_agent_class") or "RuntimeDiagnosticAgent")
        twin = str(prof.get("twin_agent_class") or "RuntimeDiagnosticTwinAgent")
        rows.append(RepoRow(name=repo_name, primary=primary, twin=twin))
    rows.sort(key=lambda r: r.name.lower())
    return rows


def _compute_repo_statuses(
    *,
    repos: list[RepoRow],
    health: dict[str, Any],
) -> dict[str, str]:
    global_state = str(health.get("state") or "Idle")
    lock_details = health.get("processing_lock_details")
    lock = lock_details if isinstance(lock_details, dict) else {}
    active_repo = lock.get("target_repository")
    if not isinstance(active_repo, str) or not active_repo.strip():
        active_repo = None
    else:
        active_repo = active_repo.strip()

    statuses: dict[str, str] = {r.name: "Idle" for r in repos}
    if global_state == "Error-Locked":
        for r in repos:
            statuses[r.name] = "Error-Locked"
        return statuses

    if global_state == "Processing" and active_repo and active_repo in statuses:
        statuses[active_repo] = "Processing"
    return statuses


def _render_dashboard(
    *,
    base_url: str,
    repos: list[RepoRow],
    health: dict[str, Any] | None,
    last_error: str | None,
) -> str:
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    term_width = int(getattr(shutil.get_terminal_size(fallback=(120, 30)), "columns", 120))

    lines: list[str] = []
    title = f"{ANSI_BOLD}REMOTE-AGENTS Terminal Command Center{ANSI_RESET}"
    lines.append(f"{title}  {ANSI_DIM}{now}{ANSI_RESET}")
    lines.append(f"{ANSI_DIM}Gateway:{ANSI_RESET} {base_url.rstrip('/')}/health")

    if health is None:
        err = last_error or "no data"
        lines.append(f"{FG_RED}Health unavailable:{ANSI_RESET} {err}")
        return "\n".join(lines) + "\n"

    state = str(health.get("state") or "Idle")
    buffered = int(health.get("buffered") or 0)
    disk_task = bool(health.get("disk_task_present"))
    lock_age = health.get("processing_lock_age_s")
    resources = health.get("resources") if isinstance(health.get("resources"), dict) else {}
    sem = health.get("semantic_memory") if isinstance(health.get("semantic_memory"), dict) else {}
    mem_by_repo = sem.get("by_repository") if isinstance(sem.get("by_repository"), dict) else {}
    total_records = int(sem.get("total_records") or 0)

    lock_details = health.get("processing_lock_details")
    lock = lock_details if isinstance(lock_details, dict) else {}
    active_repo = lock.get("target_repository")
    if not isinstance(active_repo, str) or not active_repo.strip():
        active_repo = None
    else:
        active_repo = active_repo.strip()

    active_primary = lock.get("primary_agent_class") if isinstance(lock.get("primary_agent_class"), str) else None
    active_twin = lock.get("twin_agent_class") if isinstance(lock.get("twin_agent_class"), str) else None
    active_threads = lock.get("num_thread")
    try:
        active_threads_i = int(active_threads) if active_threads is not None else 4
    except Exception:
        active_threads_i = 4

    used_pct = resources.get("system_used_percent")
    used_pct_s = f"{used_pct:.2f}%" if isinstance(used_pct, (int, float)) else "n/a"
    used_s = _format_bytes(resources.get("system_used_bytes"))
    total_s = _format_bytes(resources.get("system_total_bytes"))

    mem_line = f"{ANSI_DIM}Memory:{ANSI_RESET} {used_s} / {total_s} ({used_pct_s})"
    queue_line = (
        f"{ANSI_DIM}Queue:{ANSI_RESET} buffered={buffered} disk_task={'yes' if disk_task else 'no'} "
        f"lock_age_s={lock_age if lock_age is not None else 'n/a'}"
    )
    exec_line = (
        f"{ANSI_DIM}Execution:{ANSI_RESET} state={_style_status(state)} "
        f"threads={active_threads_i}/4 "
        f"active_repo={active_repo or 'n/a'}"
    )
    if active_primary or active_twin:
        exec_line += f" agents={active_primary or 'n/a'}+{active_twin or 'n/a'}"

    lines.extend([mem_line, queue_line, exec_line])
    if last_error:
        lines.append(f"{FG_RED}Last error:{ANSI_RESET} {last_error}")

    statuses = _compute_repo_statuses(repos=repos, health=health)
    headers = ["Repository", "Primary", "Twin", "Status", "Mem"]
    rows: list[list[str]] = []
    for r in repos:
        mem_count = mem_by_repo.get(r.name)
        try:
            mem_i = int(mem_count) if mem_count is not None else 0
        except Exception:
            mem_i = 0
        status = statuses.get(r.name, "Idle")
        rows.append([r.name, r.primary, r.twin, _style_status(status), str(mem_i)])

    table = _render_box_table(headers, rows)
    if term_width < 80:
        lines.append(f"{FG_YELLOW}Warning:{ANSI_RESET} terminal is narrow; table may truncate.")
    lines.append(f"{ANSI_DIM}Semantic memory total:{ANSI_RESET} {total_records}")
    lines.append(table)
    lines.append(f"{ANSI_DIM}Press Ctrl+C to exit.{ANSI_RESET}")
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Interactive local platform dashboard (polls GET /health).")
    p.add_argument(
        "--url",
        default=os.environ.get("GATEWAY_URL", "").strip() or "http://127.0.0.1:8080",
        help="Gateway base URL (default: http://127.0.0.1:8080).",
    )
    p.add_argument("--interval", type=float, default=2.0, help="Polling interval seconds (default: 2).")
    p.add_argument(
        "--registry",
        default="config/agent_registry.json",
        help="Path to agent registry JSON (default: config/agent_registry.json).",
    )
    p.add_argument("--once", action="store_true", help="Render once and exit.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    _enable_windows_vt()

    registry_path = Path(str(args.registry))
    registry = _load_agent_registry(registry_path)
    repos = _repos_from_registry(registry)
    if not repos:
        print(f"ERROR: no repositories found in registry: {registry_path}", file=sys.stderr)
        return 2

    base_url = str(args.url).rstrip("/")
    health_url = f"{base_url}/health"
    interval_s = max(0.5, float(args.interval))

    last_error: str | None = None
    last_health: dict[str, Any] | None = None

    while True:
        try:
            last_health = _http_get_json(health_url, timeout_s=3.0)
            last_error = None
        except urllib.error.URLError as exc:
            last_error = str(exc)
        except Exception as exc:
            last_error = str(exc)

        sys.stdout.write(ANSI_CLEAR)
        sys.stdout.write(
            _render_dashboard(base_url=base_url, repos=repos, health=last_health, last_error=last_error)
        )
        sys.stdout.flush()

        if bool(args.once):
            return 0
        time.sleep(interval_s)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

