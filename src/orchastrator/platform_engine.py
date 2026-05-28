import os
import json
import time
import subprocess
import requests
import sys
from collections import deque
from pathlib import Path
import traceback
import errno

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from orchestrator.dispatcher import DispatcherConfig, OutboundCallbackDispatcher, build_delivery_envelope
from tools.logger import archive_failed_payload, ensure_runtime_directories, log_agent_failure, log_engine_interruption

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:3b" # Optimized for Meteor Lake P-Cores
TOOLS_CONFIG_PATH = "config/platform_mcp_tools.json"
PROCESSING_LOCK_FILE = ".platform_queue/processing.lock"
LOCK_STALE_S = 15 * 60  # surface as Error-Locked via /health if stuck

class PlatformAgentEngine:
    def __init__(self):
        ensure_runtime_directories()
        self._artifacts_created: set[str] | None = None
        self._dispatcher: OutboundCallbackDispatcher | None = None
        self._init_outbound_dispatcher()
        self._prune_stale_processing_lock(on_boot=True)
        self.load_mcp_tools()
        print("⚡ Platform Agent Infrastructure Initialized.")
        print(f"🔒 Guardrails active: 4 P-Core enforcement, OLLAMA Keep-Alive ready.")

    def _init_outbound_dispatcher(self) -> None:
        callback_url = os.environ.get("PLATFORM_CALLBACK_URL", "").strip()
        if not callback_url:
            return
        token = os.environ.get("PLATFORM_CALLBACK_BEARER_TOKEN", "").strip() or None
        cfg = DispatcherConfig(callback_url=callback_url, bearer_token=token)
        self._dispatcher = OutboundCallbackDispatcher(cfg)
        self._dispatcher.start()

    def load_mcp_tools(self):
        try:
            with open(TOOLS_CONFIG_PATH, "r", encoding="utf-8") as f:
                self.tools_schema = json.load(f)["tools"]
        except FileNotFoundError:
            self.tools_schema = []
            print(f"⚠️ Tools config not found at {TOOLS_CONFIG_PATH}; continuing with no tools.")

    def execute_tool(self, name, arguments):
        """Standard routing layout for autonomous system tool execution"""
        print(f"⚙️ Executing system tool: {name}")
        try:
            if name == "workspace_file_router":
                path = arguments.get("relative_path")
                action = arguments.get("action")
                if action == "write":
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(arguments.get("content", ""))
                    if self._artifacts_created is not None and isinstance(path, str) and path:
                        self._artifacts_created.add(path)
                    return f"Successfully written to {path}"
                if action == "read":
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
                raise ValueError(f"Unsupported workspace_file_router action: {action}")

            if name == "execute_isolated_task":
                code = arguments.get("script_content")
                result = subprocess.run(
                    ["python", "-c", code],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"

            if name == "network_data_fetch":
                url = arguments.get("url")
                method = arguments.get("method")
                res = requests.request(method, url, timeout=15)
                res.raise_for_status()
                return res.text

            raise ValueError(f"Unknown tool: {name}")
        except Exception as e:
            raise RuntimeError(f"Tool {name} crashed: {e}") from e

    def query_local_llm(self, prompt_content):
        # Enforce exact 4 thread runtime to stay on hardware P-cores
        payload = {
            "model": MODEL_NAME,
            "prompt": f"System Tools available:\n{json.dumps(self.tools_schema)}\n\nUser Task: {prompt_content}\n\nRespond with a JSON object containing 'tool_to_call' and 'arguments' if needed, or 'final_response'.",
            "stream": False,
            "format": "json",
            "options": {"num_thread": 4} 
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("Ollama response was not a JSON object")
        return body.get("response", "{}")

    def _handle_failure(self, task_file: str, task_id: str, prompt_history: list, error_message: str, loop_count: int):
        log_agent_failure(
            task_id=task_id,
            prompt_history=prompt_history,
            error_message=error_message,
            loop_count=loop_count,
        )
        try:
            archived_path = archive_failed_payload(task_file_path=task_file, task_id=task_id)
            print(f"📦 Task archived for review: {archived_path}")
        except Exception as e:
            print(f"⚠️ Failed to archive payload {task_file}: {e}")

    def _processing_lock_age_s(self) -> float | None:
        try:
            st = os.stat(PROCESSING_LOCK_FILE)
        except OSError:
            return None
        return time.time() - float(st.st_mtime)

    def _prune_stale_processing_lock(self, *, on_boot: bool) -> bool:
        age = self._processing_lock_age_s()
        if age is None or age <= LOCK_STALE_S:
            return False

        details: dict[str, object] = {"lock_age_s": round(float(age), 3), "lock_path": PROCESSING_LOCK_FILE}
        try:
            with open(PROCESSING_LOCK_FILE, "r", encoding="utf-8") as f:
                lock_body = json.load(f)
            if isinstance(lock_body, dict):
                details["lock_details"] = lock_body
        except Exception:
            pass

        try:
            os.remove(PROCESSING_LOCK_FILE)
        except FileNotFoundError:
            return True
        except Exception as exc:
            log_engine_interruption(
                event_type="STALE_LOCK_PRUNE_FAILED",
                message=f"Failed to delete stale processing lock (age_s={age:.1f}): {exc}",
                details=details,
            )
            return False

        log_engine_interruption(
            event_type="STALE_LOCK_PRUNED",
            message=f"Deleted stale processing lock (age_s={age:.1f}){' on boot' if on_boot else ''}.",
            details=details,
        )
        return True

    def _try_acquire_processing_lock(self, *, task_id: str) -> bool:
        ensure_runtime_directories()
        age = self._processing_lock_age_s()
        if age is not None and age > LOCK_STALE_S:
            if not self._prune_stale_processing_lock(on_boot=False):
                print(f"🧯 Error-Locked: stale processing lock detected (age_s={age:.1f}).")
                return False

        try:
            fd = os.open(PROCESSING_LOCK_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except OSError as e:
            if e.errno in (errno.EEXIST,):
                return False
            raise

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "task_id": task_id,
                        "pid": os.getpid(),
                        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                os.remove(PROCESSING_LOCK_FILE)
            except Exception:
                pass
            raise

        return True

    def _release_processing_lock(self) -> None:
        try:
            os.remove(PROCESSING_LOCK_FILE)
        except FileNotFoundError:
            pass

    def run_loop(self):
        print("🚀 24/7 Autonomous Node Listening to Platform Events...")
        while True:
            # Placeholder for platform queue monitoring (e.g. database change, webhook, folder drop)
            task_file = ".platform_queue/next_task.json"
            
            if os.path.exists(task_file):
                print("📬 Task discovered in platform loop.")
                lock_acquired = False
                task_start_monotonic: float | None = None
                artifacts_created: list[str] = []
                final_summary: str = ""
                failure_summary: str = ""
                try:
                    try:
                        with open(task_file, "r", encoding="utf-8") as f:
                            task_data = json.load(f)
                    except Exception as e:
                        self._handle_failure(
                            task_file=task_file,
                            task_id=os.path.basename(task_file),
                            prompt_history=[],
                            error_message=f"Failed to read/parse task payload: {e}",
                            loop_count=0,
                        )
                        time.sleep(10)
                        continue

                    # Enforce loop breaker guardrail
                    max_loops = 5
                    current_loop = 0
                    completed = False
                    failed = False
                    task_id = task_data.get("task_id") or task_data.get("id") or os.path.basename(task_file)
                    instruction = task_data.get("instruction") or ""
                    prompt_history = [{"instruction": instruction}]

                    if not self._try_acquire_processing_lock(task_id=task_id):
                        # Another engine instance has compute priority, or lock is stale.
                        time.sleep(2)
                        continue
                    lock_acquired = True
                    task_start_monotonic = time.monotonic()
                    self._artifacts_created = set()

                    max_context_chars = 20_000
                    context_chunks = deque([instruction])
                    current_context_size = len(instruction)

                    def append_context(chunk: str) -> None:
                        nonlocal current_context_size
                        chunk = chunk or ""
                        context_chunks.append(chunk)
                        current_context_size += len(chunk) + 1
                        while current_context_size > max_context_chars and len(context_chunks) > 1:
                            removed = context_chunks.popleft()
                            current_context_size -= len(removed) + 1

                    while current_loop < max_loops and not completed:
                        current_loop += 1
                        try:
                            raw_decision = self.query_local_llm("\n".join(context_chunks))
                        except Exception as e:
                            failed = True
                            failure_summary = f"Ollama disconnected: {e}"
                            self._handle_failure(
                                task_file=task_file,
                                task_id=task_id,
                                prompt_history=prompt_history,
                                error_message=failure_summary,
                                loop_count=current_loop,
                            )
                            completed = True
                            break

                        prompt_history.append({"raw_decision": raw_decision})
                        try:
                            decision = json.loads(raw_decision)
                        except Exception as e:
                            failed = True
                            failure_summary = f"Model formatting failure (invalid JSON): {e}"
                            self._handle_failure(
                                task_file=task_file,
                                task_id=task_id,
                                prompt_history=prompt_history,
                                error_message=failure_summary,
                                loop_count=current_loop,
                            )
                            completed = True
                            break
                        
                        if "tool_to_call" in decision:
                            try:
                                tool_output = self.execute_tool(decision["tool_to_call"], decision.get("arguments", {}))
                            except Exception as e:
                                failed = True
                                failure_summary = str(e)
                                self._handle_failure(
                                    task_file=task_file,
                                    task_id=task_id,
                                    prompt_history=prompt_history,
                                    error_message=failure_summary,
                                    loop_count=current_loop,
                                )
                                completed = True
                                break
                            prompt_history.append({"tool_output": tool_output})
                            append_context(f"Tool Observation: {tool_output}")
                        else:
                            final_summary = str(decision.get("final_response") or "")
                            print(f"🎉 Task Finished: {final_summary}")
                            completed = True
                    
                    if not completed and current_loop >= max_loops:
                        failed = True
                        failure_summary = "Loop breaker triggered: max loops reached"
                        self._handle_failure(
                            task_file=task_file,
                            task_id=task_id,
                            prompt_history=prompt_history,
                            error_message=failure_summary,
                            loop_count=current_loop,
                        )
                    elif completed and not failed and os.path.exists(task_file):
                        os.remove(task_file) # Clear task from platform processing queue

                    if self._artifacts_created:
                        artifacts_created = sorted(self._artifacts_created)
                    duration_s = 0.0
                    if task_start_monotonic is not None:
                        duration_s = max(0.0, float(time.monotonic() - task_start_monotonic))
                    status = "FAILED" if failed else "COMPLETED"
                    execution_summary = failure_summary if failed else final_summary
                    if execution_summary is None:
                        execution_summary = ""
                    if self._dispatcher is not None:
                        envelope = build_delivery_envelope(
                            task_id=str(task_id),
                            status=status,
                            duration_seconds=duration_s,
                            execution_summary=str(execution_summary),
                            artifacts_created=artifacts_created,
                        )
                        try:
                            self._dispatcher.enqueue(envelope)
                        except Exception as exc:
                            log_engine_interruption(
                                event_type="DISPATCH_ENQUEUE_FAILED",
                                message=f"Failed to enqueue outbound delivery envelope for task_id={task_id}: {exc}",
                                details={"task_id": str(task_id), "status": status},
                            )
                finally:
                    self._artifacts_created = None
                    if lock_acquired:
                        self._release_processing_lock()
                
            time.sleep(10) # Cooling sleep cycle to prevent CPU throttling

if __name__ == "__main__":
    try:
        engine = PlatformAgentEngine()
        engine.run_loop()
    except Exception:
        log_agent_failure(
            task_id="platform_engine_boot",
            prompt_history=[],
            error_message=traceback.format_exc(),
            loop_count=0,
        )
        raise
