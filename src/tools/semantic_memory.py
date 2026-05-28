from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from tools.logger import ensure_runtime_directories


SEMANTIC_MEMORY_FILE = Path(".logs/semantic_memory.json")

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-./]{1,63}")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "our",
    "so",
    "that",
    "the",
    "their",
    "then",
    "there",
    "this",
    "to",
    "use",
    "using",
    "was",
    "we",
    "were",
    "with",
    "you",
    "your",
}


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}.{int(time.time() * 1000)}")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def _load_registry() -> dict[str, list[dict[str, Any]]]:
    ensure_runtime_directories()
    try:
        raw = SEMANTIC_MEMORY_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    try:
        obj = json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}
    if not isinstance(obj, dict):
        return {}

    registry: dict[str, list[dict[str, Any]]] = {}
    for repo_name, records in obj.items():
        if not isinstance(repo_name, str) or not repo_name.strip():
            continue
        if not isinstance(records, list):
            continue
        cleaned: list[dict[str, Any]] = []
        for rec in records:
            if isinstance(rec, dict):
                cleaned.append(rec)
        registry[repo_name] = cleaned
    return registry


def _extract_keywords(text: str, *, max_keywords: int = 12) -> list[str]:
    if not isinstance(text, str):
        return []
    candidates: list[str] = []
    for match in _WORD_RE.findall(text.lower()):
        token = match.strip("._-/")
        if len(token) < 3:
            continue
        if token in _STOPWORDS:
            continue
        candidates.append(token)

    seen: set[str] = set()
    uniq: list[str] = []
    for token in candidates:
        if token in seen:
            continue
        seen.add(token)
        uniq.append(token)
        if len(uniq) >= int(max_keywords):
            break
    return uniq


def append_memory(
    *,
    repo_name: str,
    task_summary: str,
    consensus_code_snippet: str,
    keywords: list[str] | None = None,
    max_records_per_repo: int = 250,
) -> None:
    """Append a new successful consensus outcome to `.logs/semantic_memory.json`."""

    repo_name = str(repo_name or "").strip()
    if not repo_name:
        return

    task_summary = str(task_summary or "").strip()
    consensus_code_snippet = str(consensus_code_snippet or "").strip()
    if keywords is None:
        keywords = _extract_keywords(f"{task_summary}\n{consensus_code_snippet}")
    else:
        keywords = [str(k).strip().lower() for k in keywords if isinstance(k, str) and str(k).strip()]
        keywords = keywords[:12]

    # Avoid unbounded growth on disk.
    task_summary = task_summary[:500]
    consensus_code_snippet = consensus_code_snippet[:4000]

    record = {
        "timestamp": _utc_timestamp(),
        "task_summary": task_summary,
        "consensus_code_snippet": consensus_code_snippet,
        "keywords": keywords,
    }

    registry = _load_registry()
    existing = registry.get(repo_name, [])
    if not isinstance(existing, list):
        existing = []
    existing.append(record)
    if len(existing) > int(max_records_per_repo):
        existing = existing[-int(max_records_per_repo) :]
    registry[repo_name] = existing
    _atomic_write_json(SEMANTIC_MEMORY_FILE, registry)


def inject_relevant_memories(repo_name: str, current_instruction: str) -> str:
    """Return a compact markdown segment with up to 2 relevant prior snippets."""

    repo_name = str(repo_name or "").strip()
    if not repo_name:
        return ""

    instruction_keywords = set(_extract_keywords(current_instruction, max_keywords=16))
    if not instruction_keywords:
        return ""

    registry = _load_registry()
    records = registry.get(repo_name) or []
    if not isinstance(records, list) or not records:
        return ""

    scored: list[tuple[int, int, dict[str, Any]]] = []
    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            continue
        rec_keywords = rec.get("keywords")
        if not isinstance(rec_keywords, list):
            rec_keywords = []
        rec_kw_set = {str(k).strip().lower() for k in rec_keywords if isinstance(k, str) and str(k).strip()}
        score = len(instruction_keywords.intersection(rec_kw_set))
        if score <= 0:
            continue
        scored.append((int(score), int(idx), rec))

    if not scored:
        return ""

    # Prefer higher overlap, then newer entries (higher idx).
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    top = [rec for _score, _idx, rec in scored[:2]]

    lines: list[str] = ["### Semantic Memory (Top Matches)"]
    for rec in top:
        ts = str(rec.get("timestamp") or "").strip()
        summary = str(rec.get("task_summary") or "").strip()
        snippet = str(rec.get("consensus_code_snippet") or "").strip()
        if len(snippet) > 500:
            snippet = snippet[:500].rstrip() + "…"
        if ts and summary:
            lines.append(f"- {ts} — {summary}")
        elif summary:
            lines.append(f"- {summary}")
        elif ts:
            lines.append(f"- {ts}")
        else:
            lines.append("- (memory)")
        if snippet:
            lines.append(snippet)

    return "\n".join(lines).strip() + "\n"


def memory_counts_by_repository() -> dict[str, int]:
    """Return counts per repository for health telemetry."""

    registry = _load_registry()
    counts: dict[str, int] = {}
    for repo_name, records in registry.items():
        if isinstance(repo_name, str) and repo_name.strip() and isinstance(records, list):
            counts[repo_name] = len(records)
    return counts

