from __future__ import annotations

import json
import math
import os
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable

from tools.workspace_mounter import resolve_repo_root, resolve_secure_path


_WARN_RE = re.compile(r"\bwarn(ing)?\b", re.IGNORECASE)
_ERR_RE = re.compile(r"\berror\b|\bfail(ed|ure)?\b|\bexception\b", re.IGNORECASE)


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("bool is not a valid float")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            raise ValueError("empty string is not a valid float")
        return float(s)
    raise ValueError(f"unsupported numeric type: {type(value).__name__}")


def _is_finite_number(value: Any) -> tuple[bool, str | None, float | None]:
    try:
        f = _as_float(value)
    except Exception as exc:
        return False, str(exc), None
    if not math.isfinite(f):
        return False, "non-finite float", f
    return True, None, f


def _flatten_matrix(value: Any) -> list[Any]:
    if isinstance(value, list) and len(value) == 16:
        return list(value)
    if isinstance(value, tuple) and len(value) == 16:
        return list(value)
    if isinstance(value, list) and len(value) == 4 and all(isinstance(row, (list, tuple)) and len(row) == 4 for row in value):
        out: list[Any] = []
        for row in value:
            out.extend(list(row))
        return out
    raise ValueError("matrix must be length-16 list/tuple or 4x4 nested list")


def parse_matrix4(value: Any) -> dict[str, Any]:
    """Parse a 4x4 matrix into 16 finite floats.

    Accepts:
      - 16-length list/tuple
      - 4x4 nested list
      - JSON string encoding either shape
    """

    if isinstance(value, str):
        s = value.strip()
        if not s:
            raise ValueError("matrix string is empty")
        try:
            value = json.loads(s)
        except Exception as exc:
            raise ValueError(f"matrix string is not valid JSON: {exc}") from exc

    raw = _flatten_matrix(value)
    parsed: list[float] = []
    for idx, item in enumerate(raw):
        ok, err, f = _is_finite_number(item)
        if not ok or f is None:
            raise ValueError(f"matrix element {idx} invalid: {err}")
        parsed.append(float(f))
    return {"matrix": parsed}


def validate_transform_math(payload: Any) -> dict[str, Any]:
    """Validate transforms/matrices/bounding boxes for 3D automation tasks.

    Payload can be a dict with any of:
      - matrix: 16-length array or 4x4 nested array (or JSON string)
      - translation: [x,y,z]
      - rotation_quat: [x,y,z,w]
      - rotation_euler: [x,y,z] (radians or degrees; only finite check)
      - scale: [x,y,z]
      - bounding_box: {"min":[x,y,z], "max":[x,y,z]} or [[min...],[max...]]
    """

    issues: list[dict[str, str]] = []

    if isinstance(payload, str):
        s = payload.strip()
        if s:
            try:
                payload = json.loads(s)
            except Exception as exc:
                return {"ok": False, "issues": [{"path": "$", "message": f"payload is not valid JSON: {exc}"}]}

    if not isinstance(payload, dict):
        return {"ok": False, "issues": [{"path": "$", "message": "payload must be an object"}]}

    def check_vec3(path: str, value: Any, *, allow_zero: bool = True) -> list[float] | None:
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            issues.append({"path": path, "message": "expected [x,y,z]"})
            return None
        out: list[float] = []
        for i, item in enumerate(value):
            ok, err, f = _is_finite_number(item)
            if not ok or f is None:
                issues.append({"path": f"{path}[{i}]", "message": f"invalid number: {err}"})
                return None
            out.append(float(f))
        if not allow_zero and all(abs(x) < 1e-12 for x in out):
            issues.append({"path": path, "message": "vector is near-zero; may cause divide-by-zero in normalization"})
        return out

    def check_quat(path: str, value: Any) -> list[float] | None:
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            issues.append({"path": path, "message": "expected [x,y,z,w] quaternion"})
            return None
        out: list[float] = []
        for i, item in enumerate(value):
            ok, err, f = _is_finite_number(item)
            if not ok or f is None:
                issues.append({"path": f"{path}[{i}]", "message": f"invalid number: {err}"})
                return None
            out.append(float(f))
        n2 = sum(x * x for x in out)
        if n2 < 1e-24:
            issues.append({"path": path, "message": "quaternion norm is near-zero; may cause divide-by-zero in normalization"})
        return out

    if "translation" in payload:
        check_vec3("$.translation", payload.get("translation"), allow_zero=True)
    if "rotation_euler" in payload:
        check_vec3("$.rotation_euler", payload.get("rotation_euler"), allow_zero=True)
    if "rotation_quat" in payload:
        check_quat("$.rotation_quat", payload.get("rotation_quat"))
    if "scale" in payload:
        scale = check_vec3("$.scale", payload.get("scale"), allow_zero=True)
        if scale is not None and any(abs(s) < 1e-12 for s in scale):
            issues.append({"path": "$.scale", "message": "scale contains near-zero component; may cause divide-by-zero in inverses"})

    if "matrix" in payload:
        try:
            m = parse_matrix4(payload.get("matrix")).get("matrix", [])
        except Exception as exc:
            issues.append({"path": "$.matrix", "message": str(exc)})
        else:
            if len(m) == 16:
                # Flag a clearly non-invertible matrix (very weak heuristic).
                # If the last row is all zeros, many pipelines will divide by w.
                if all(abs(float(x)) < 1e-12 for x in m[12:16]):
                    issues.append({"path": "$.matrix", "message": "last row is near-zero; may cause divide-by-zero in homogeneous divide"})

    if "bounding_box" in payload:
        bb = payload.get("bounding_box")
        bb_min: Any = None
        bb_max: Any = None
        if isinstance(bb, dict):
            bb_min = bb.get("min")
            bb_max = bb.get("max")
        elif isinstance(bb, (list, tuple)) and len(bb) == 2:
            bb_min, bb_max = bb[0], bb[1]
        else:
            issues.append({"path": "$.bounding_box", "message": "expected {min,max} or [min,max]"})
            bb = None

        if bb is not None:
            mn = check_vec3("$.bounding_box.min", bb_min, allow_zero=True)
            mx = check_vec3("$.bounding_box.max", bb_max, allow_zero=True)
            if mn is not None and mx is not None:
                if any(mn[i] > mx[i] for i in range(3)):
                    issues.append({"path": "$.bounding_box", "message": "min must be <= max on all axes"})

    return {"ok": len(issues) == 0, "issues": issues}


def _truncate_lines(text: str, *, max_chars: int, max_lines: int) -> str:
    text = str(text or "")
    if not text:
        return ""
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    out = "\n".join(lines)
    if len(out) > max_chars:
        out = out[-max_chars:]
    return out


def _extract_flagged_lines(lines: Iterable[str], pattern: re.Pattern[str], *, max_items: int) -> list[str]:
    out: list[str] = []
    for ln in lines:
        if pattern.search(ln):
            out.append(ln)
            if len(out) >= max_items:
                break
    return out


def _validate_compile_command(command: str) -> list[str]:
    """Return argv for safe non-shell execution; raise on unsafe constructs."""

    if not isinstance(command, str) or not command.strip():
        raise ValueError("compile_command must be a non-empty string")
    if len(command) > 4000:
        raise ValueError("compile_command too long")

    argv = shlex.split(command, posix=True)
    if not argv:
        raise ValueError("compile_command produced empty argv")

    forbidden_tokens = {"&&", "||", ";", "|", "&", ">", "<", ">>", "2>", "1>", "0>"}
    for tok in argv:
        if tok in forbidden_tokens:
            raise PermissionError(f"compile_command contains forbidden shell token: {tok!r}")
        if "`" in tok or "$(" in tok:
            raise PermissionError("compile_command contains forbidden command substitution")

    # Very small allowlist; can be extended later without changing callers.
    allowed_binaries = {
        "npm",
        "npx",
        "node",
        "pnpm",
        "yarn",
        "python",
        "python3",
    }
    first = argv[0]
    if first in allowed_binaries:
        return argv

    # Allow executing a repo-local script by path (e.g. ./scripts/build-assets.py).
    if first.startswith("./") or "/" in first or first.endswith((".py", ".js", ".mjs", ".cjs", ".sh")):
        return argv

    raise PermissionError(f"compile_command binary not allowed: {first!r}")


def trace_asset_compilation(repo_name: str, asset_path: str, compile_command: str) -> dict[str, Any]:
    """Execute a local compilation command and return a structured trace.

    The command is executed without a shell, pinned to the repo root as resolved by
    workspace_mounter. The asset path is verified to be inside the repo boundary.
    """

    repo_root = resolve_repo_root(repo_name)
    abs_asset = resolve_secure_path(repo_name, asset_path)
    asset_exists = False
    try:
        asset_exists = Path(abs_asset).exists()
    except OSError:
        asset_exists = False

    argv = _validate_compile_command(compile_command)

    # If argv[0] is a path, ensure it is repo-contained.
    if argv[0].startswith("./") or "/" in argv[0]:
        script_rel = argv[0].lstrip("./")
        script_abs = resolve_secure_path(repo_name, script_rel)
        argv = [script_abs, *argv[1:]]

    started = time.monotonic()
    env = dict(os.environ)
    env.setdefault("CI", "1")
    result = subprocess.run(
        argv,
        cwd=os.fspath(repo_root),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )
    duration_s = float(time.monotonic() - started)

    stdout = str(result.stdout or "")
    stderr = str(result.stderr or "")
    stdout_lines = stdout.splitlines()
    stderr_lines = stderr.splitlines()
    warnings = _extract_flagged_lines([*stderr_lines, *stdout_lines], _WARN_RE, max_items=80)
    errors = _extract_flagged_lines([*stderr_lines, *stdout_lines], _ERR_RE, max_items=80)

    return {
        "ok": int(result.returncode) == 0,
        "repo_name": repo_name,
        "repo_root": os.fspath(repo_root),
        "asset_path": asset_path,
        "asset_abs_path": abs_asset,
        "asset_exists": asset_exists,
        "compile_command": compile_command,
        "argv": argv,
        "exit_code": int(result.returncode),
        "duration_s": round(duration_s, 3),
        "warnings": warnings,
        "error_lines": errors,
        "stdout_tail": _truncate_lines(stdout, max_chars=8000, max_lines=200),
        "stderr_tail": _truncate_lines(stderr, max_chars=8000, max_lines=200),
    }

