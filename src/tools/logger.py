import json
import os
import time
from typing import Any


LOG_DIR = ".logs"
ERRORS_FILE = os.path.join(LOG_DIR, "errors.json")

PLATFORM_QUEUE_DIR = ".platform_queue"
PLATFORM_QUEUE_FAILED_DIR = os.path.join(PLATFORM_QUEUE_DIR, "failed")


def ensure_runtime_directories() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(PLATFORM_QUEUE_DIR, exist_ok=True)
    os.makedirs(PLATFORM_QUEUE_FAILED_DIR, exist_ok=True)

    if not os.path.exists(ERRORS_FILE):
        _atomic_write_json(ERRORS_FILE, [])


def log_agent_failure(
    task_id: str,
    prompt_history: list,
    error_message: str,
    loop_count: int,
) -> None:
    ensure_runtime_directories()

    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "task_id": task_id,
        "loop_count_reached": loop_count,
        "error_type": _infer_error_type(error_message=error_message, loop_count=loop_count),
        "last_known_error": error_message,
        "context_snapshot": _snapshot_prompt_history(prompt_history),
    }

    try:
        existing = _read_json_list(ERRORS_FILE)
    except Exception as e:
        existing = []
        record["last_known_error"] = (
            f"{error_message}\n\n[logger] Failed to read existing {ERRORS_FILE}: {e}"
        )

    existing.append(record)
    _atomic_write_json(ERRORS_FILE, existing)


def archive_failed_payload(task_file_path: str, task_id: str) -> str:
    ensure_runtime_directories()

    base_name = os.path.basename(task_file_path)
    safe_task_id = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in task_id)[:64]
    timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    archived_name = f"{timestamp}__{safe_task_id}__{base_name}"
    archived_path = os.path.join(PLATFORM_QUEUE_FAILED_DIR, archived_name)

    os.replace(task_file_path, archived_path)
    return archived_path


def _infer_error_type(error_message: str, loop_count: int) -> str:
    lowered = (error_message or "").lower()
    if loop_count >= 5 and ("max_iterations" in lowered or "max loops" in lowered or "loop breaker" in lowered):
        return "MAX_ITERATIONS_EXCEEDED"
    if "ollama" in lowered or "11434" in lowered or "disconnected" in lowered:
        return "OLLAMA_DISCONNECT"
    if loop_count >= 5:
        return "MAX_ITERATIONS_EXCEEDED"
    return "TOOL_CRASH"


def _snapshot_prompt_history(prompt_history: list, max_chars: int = 20_000) -> str:
    try:
        rendered = json.dumps(prompt_history, ensure_ascii=False)
    except Exception:
        rendered = "\n".join(str(item) for item in prompt_history)

    if len(rendered) <= max_chars:
        return rendered
    return f"[truncated] ...{rendered[-max_chars:]}"


def _read_json_list(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def _atomic_write_json(path: str, data: Any) -> None:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    tmp_path = f"{path}.tmp.{os.getpid()}.{int(time.time() * 1000)}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)

