from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


DEFAULT_OLLAMA_URL = os.environ.get("PLATFORM_OLLAMA_URL", "").strip() or "http://localhost:11434/api/generate"
DEFAULT_MODEL_NAME = os.environ.get("PLATFORM_OLLAMA_MODEL", "").strip() or "qwen2.5-coder:3b"

_METRICS_PATH = Path(".logs/consensus_metrics.json")


class TwinRejectedError(RuntimeError):
    def __init__(self, feedback: str):
        super().__init__(feedback)
        self.feedback = feedback


@dataclass(frozen=True, slots=True)
class TwinVerification:
    approved: bool
    feedback: str
    raw: str | None = None


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{int(time.time() * 1000)}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load_json_obj(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    try:
        obj = json.loads(raw)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def load_consensus_metrics() -> dict[str, int]:
    obj = _load_json_obj(_METRICS_PATH)
    return {
        "total_consensus_reviews": int(obj.get("total_consensus_reviews") or 0),
        "twin_rejections": int(obj.get("twin_rejections") or 0),
        "successful_refinements": int(obj.get("successful_refinements") or 0),
    }


def record_consensus_metrics_update(
    *,
    total_consensus_reviews_delta: int = 0,
    twin_rejections_delta: int = 0,
    successful_refinements_delta: int = 0,
) -> dict[str, int]:
    metrics = load_consensus_metrics()
    metrics["total_consensus_reviews"] = max(0, int(metrics["total_consensus_reviews"]) + int(total_consensus_reviews_delta))
    metrics["twin_rejections"] = max(0, int(metrics["twin_rejections"]) + int(twin_rejections_delta))
    metrics["successful_refinements"] = max(
        0, int(metrics["successful_refinements"]) + int(successful_refinements_delta)
    )
    _atomic_write_json(_METRICS_PATH, metrics)
    return metrics


def _truncate_code_for_prompt(code: str, *, max_chars: int) -> tuple[str, bool]:
    code = code or ""
    if max_chars <= 0 or len(code) <= max_chars:
        return code, False
    head = max(0, max_chars // 2)
    tail = max(0, max_chars - head)
    return code[:head] + "\n\n[...truncated...]\n\n" + code[-tail:], True


def _python_syntax_check(source: str, *, label: str) -> str | None:
    try:
        compile(source or "", label, "exec")
    except SyntaxError as exc:
        ln = getattr(exc, "lineno", None)
        col = getattr(exc, "offset", None)
        msg = getattr(exc, "msg", "SyntaxError")
        loc = ""
        if ln is not None:
            loc = f" (line {ln}" + (f", col {col})" if col is not None else ")")
        return f"Python syntax error{loc}: {msg}"
    except Exception as exc:
        return f"Python compile check failed: {exc}"
    return None


def _build_twin_audit_prompt(
    *,
    repo_name: str,
    twin_role: str,
    tool_name: str | None,
    relative_path: str | None,
    proposed_code: str,
    truncated: bool,
) -> str:
    meta: list[str] = [
        "[TWIN_AUDIT]",
        f"repo_name={repo_name}",
        f"twin_role={twin_role}",
    ]
    if tool_name:
        meta.append(f"tool_name={tool_name}")
    if relative_path:
        meta.append(f"relative_path={relative_path}")
    if truncated:
        meta.append("note=proposed_code_truncated_for_prompt")
    meta.append("")
    meta.append(
        "Audit the proposed code/action. Reject if you see: syntax errors, unsafe filesystem/network behavior, secrets, "
        "destructive commands, path traversal, or obvious anti-patterns. Provide actionable feedback."
    )
    meta.append("")
    meta.append('Respond with STRICT JSON: {"approved": true|false, "feedback": "..."}.')
    meta.append("")
    meta.append("[PROPOSED_CODE]")
    meta.append(proposed_code or "")
    return "\n".join(meta)


def _ollama_generate_json(
    *,
    prompt: str,
    num_thread: int,
    ollama_url: str,
    model_name: str,
    timeout_s: int = 60,
) -> str:
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"num_thread": int(num_thread)},
    }
    response = requests.post(ollama_url, json=payload, timeout=int(timeout_s))
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("Ollama response was not a JSON object")
    raw = body.get("response", "")
    if not isinstance(raw, str):
        raise ValueError("Ollama 'response' field was not a string")
    return raw


def verify_with_twin_agent(
    repo_name: str,
    proposed_code: str,
    twin_role: str,
    *,
    tool_name: str | None = None,
    relative_path: str | None = None,
    num_thread: int = 4,
    max_prompt_code_chars: int = 8000,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    model_name: str = DEFAULT_MODEL_NAME,
) -> dict[str, object]:
    """Run a Twin audit pass over proposed code before it is executed or written.

    Returns {"approved": bool, "feedback": str}.
    """

    if not isinstance(repo_name, str) or not repo_name.strip():
        repo_name = "unknown"
    if not isinstance(twin_role, str) or not twin_role.strip():
        twin_role = "RuntimeDiagnosticTwinAgent"
    if not isinstance(proposed_code, str):
        proposed_code = str(proposed_code)

    # Fail closed on obvious syntax errors for python execution / python file writes.
    if tool_name == "execute_isolated_task" or (isinstance(relative_path, str) and relative_path.endswith(".py")):
        syntax_err = _python_syntax_check(proposed_code, label=relative_path or "<isolated_task>")
        if syntax_err:
            return {"approved": False, "feedback": syntax_err}

    rendered_code, truncated = _truncate_code_for_prompt(proposed_code, max_chars=int(max_prompt_code_chars))
    prompt = _build_twin_audit_prompt(
        repo_name=repo_name,
        twin_role=twin_role,
        tool_name=tool_name,
        relative_path=relative_path,
        proposed_code=rendered_code,
        truncated=truncated,
    )

    raw = _ollama_generate_json(
        prompt=prompt,
        num_thread=int(num_thread),
        ollama_url=str(ollama_url),
        model_name=str(model_name),
    )

    try:
        decision = json.loads(raw)
    except Exception:
        return {"approved": False, "feedback": "Twin audit returned invalid JSON; retry with strict JSON output."}

    if not isinstance(decision, dict):
        return {"approved": False, "feedback": "Twin audit returned non-object JSON; retry with strict JSON output."}

    approved = bool(decision.get("approved"))
    feedback = decision.get("feedback")
    if not isinstance(feedback, str):
        feedback = ""
    feedback = feedback.strip()
    if not feedback and not approved:
        feedback = "Rejected by twin audit; provide specific remediation feedback and retry."

    return {"approved": approved, "feedback": feedback}

