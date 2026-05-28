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
from tools.graphics_sandbox import parse_matrix4, trace_asset_compilation, validate_transform_math
from tools.semantic_memory import append_memory, inject_relevant_memories
from tools.workspace_mounter import resolve_repo_root, resolve_secure_path
from routers.consensus_engine import TwinRejectedError, record_consensus_metrics_update, verify_with_twin_agent
from routers.repo_governance_router import (
    build_governance_system_context,
    constraints_for_engine,
    resolve_repo_governance_route,
)

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
        self._active_target_repository: str | None = None
        self._active_repo_root: Path | None = None
        self._active_execution_constraints: dict[str, object] = {}
        self._active_default_profile: bool = False
        self._active_primary_agent_class: str | None = None
        self._active_twin_agent_class: str | None = None
        self._active_num_thread: int = 4
        self._active_task_twin_rejection_count: int = 0
        self._active_task_refinement_recorded: bool = False
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
                rel = arguments.get("relative_path") or arguments.get("path")
                action = arguments.get("action")
                if not isinstance(rel, str) or not rel.strip():
                    raise ValueError("workspace_file_router requires non-empty relative_path")
                if not isinstance(action, str) or not action.strip():
                    raise ValueError("workspace_file_router requires action")

                if self._active_repo_root is None:
                    raise RuntimeError("No active repo root bound for workspace_file_router")

                if self._active_default_profile and action == "write":
                    raise PermissionError("Default diagnostic profile forbids workspace writes")

                _enforce_repo_path_constraints(rel, self._active_execution_constraints, action=action)
                repo_name = self._active_target_repository or self._active_repo_root.name
                abs_path = resolve_secure_path(repo_name, rel)
                if action == "write":
                    review = verify_with_twin_agent(
                        repo_name=repo_name,
                        proposed_code=arguments.get("content", ""),
                        twin_role=self._active_twin_agent_class or "RuntimeDiagnosticTwinAgent",
                        tool_name=name,
                        relative_path=rel,
                        num_thread=int(self._active_num_thread or 4),
                    )
                    approved = bool(review.get("approved"))
                    feedback = str(review.get("feedback") or "")
                    record_consensus_metrics_update(
                        total_consensus_reviews_delta=1,
                        twin_rejections_delta=0 if approved else 1,
                    )
                    if not approved:
                        self._active_task_twin_rejection_count += 1
                        raise TwinRejectedError(feedback)
                    if (
                        self._active_task_twin_rejection_count > 0
                        and not self._active_task_refinement_recorded
                    ):
                        record_consensus_metrics_update(successful_refinements_delta=1)
                        self._active_task_refinement_recorded = True
                    with open(abs_path, "w", encoding="utf-8") as f:
                        f.write(arguments.get("content", ""))
                    if self._artifacts_created is not None:
                        self._artifacts_created.add(f"{repo_name}:{rel}")
                    return f"Successfully written to {repo_name}:{rel}"
                if action == "read":
                    with open(abs_path, "r", encoding="utf-8") as f:
                        return f.read()
                raise ValueError(f"Unsupported workspace_file_router action: {action}")

            if name == "graphics_validate_transform_math":
                payload = arguments.get("payload")
                result = validate_transform_math(payload)
                return json.dumps(result, ensure_ascii=False)

            if name == "graphics_parse_matrix4":
                matrix = arguments.get("matrix")
                result = parse_matrix4(matrix)
                return json.dumps(result, ensure_ascii=False)

            if name == "trace_asset_compilation":
                if self._active_repo_root is None:
                    raise RuntimeError("No active repo root bound for trace_asset_compilation")

                expected_repo = self._active_target_repository or self._active_repo_root.name
                repo_name = arguments.get("repo_name") or expected_repo
                if repo_name != expected_repo:
                    raise PermissionError("trace_asset_compilation repo_name must match the active target repository")

                asset_path = arguments.get("asset_path")
                compile_command = arguments.get("compile_command")
                if not isinstance(asset_path, str) or not asset_path.strip():
                    raise ValueError("trace_asset_compilation requires asset_path")
                if not isinstance(compile_command, str) or not compile_command.strip():
                    raise ValueError("trace_asset_compilation requires compile_command")

                try:
                    trace = trace_asset_compilation(repo_name=expected_repo, asset_path=asset_path, compile_command=compile_command)
                except subprocess.TimeoutExpired as exc:
                    trace = {
                        "ok": False,
                        "repo_name": expected_repo,
                        "asset_path": asset_path,
                        "compile_command": compile_command,
                        "exit_code": None,
                        "duration_s": None,
                        "error": f"timeout_expired: {exc}",
                    }
                except Exception as exc:
                    trace = {
                        "ok": False,
                        "repo_name": expected_repo,
                        "asset_path": asset_path,
                        "compile_command": compile_command,
                        "exit_code": None,
                        "duration_s": None,
                        "error": f"trace_failed: {exc}",
                    }

                # If the compilation failed, ask the Twin to provide an actionable explanation rather than
                # terminating the main tool loop. This allows the Primary to iterate within max_loops.
                if not bool(trace.get("ok")):
                    try:
                        twin_role = self._active_twin_agent_class or "RuntimeDiagnosticTwinAgent"
                        snippet = json.dumps(trace, ensure_ascii=False)
                        if len(snippet) > 8000:
                            snippet = snippet[-8000:]
                        twin_review = verify_with_twin_agent(
                            repo_name=expected_repo,
                            proposed_code=snippet,
                            twin_role=twin_role,
                            tool_name=name,
                            relative_path=str(asset_path),
                            num_thread=int(self._active_num_thread or 4),
                            max_prompt_code_chars=8000,
                        )
                        trace["twin_feedback"] = str(twin_review.get("feedback") or "")
                    except Exception:
                        pass

                return json.dumps(trace, ensure_ascii=False)

            if name == "execute_isolated_task":
                code = arguments.get("script_content")
                if not isinstance(code, str):
                    raise ValueError("execute_isolated_task requires script_content")
                if self._active_repo_root is None:
                    raise RuntimeError("No active repo root bound for execute_isolated_task")

                readonly = bool(self._active_default_profile) or bool(
                    (self._active_execution_constraints or {}).get("execute_isolated_task_readonly")
                )
                no_network = bool(self._active_default_profile) or bool(
                    (self._active_execution_constraints or {}).get("execute_isolated_task_no_network")
                )
                repo_name = self._active_target_repository or self._active_repo_root.name
                review = verify_with_twin_agent(
                    repo_name=repo_name,
                    proposed_code=code,
                    twin_role=self._active_twin_agent_class or "RuntimeDiagnosticTwinAgent",
                    tool_name=name,
                    relative_path=None,
                    num_thread=int(self._active_num_thread or 4),
                )
                approved = bool(review.get("approved"))
                feedback = str(review.get("feedback") or "")
                record_consensus_metrics_update(
                    total_consensus_reviews_delta=1,
                    twin_rejections_delta=0 if approved else 1,
                )
                if not approved:
                    self._active_task_twin_rejection_count += 1
                    raise TwinRejectedError(feedback)
                if self._active_task_twin_rejection_count > 0 and not self._active_task_refinement_recorded:
                    record_consensus_metrics_update(successful_refinements_delta=1)
                    self._active_task_refinement_recorded = True
                wrapped = _wrap_script_for_sandbox(code, readonly=readonly, no_network=no_network)
                result = subprocess.run(
                    ["python", "-c", wrapped],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                    cwd=os.fspath(self._active_repo_root),
                )
                return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"

            if name == "network_data_fetch":
                if self._active_default_profile:
                    raise PermissionError("Default diagnostic profile forbids network access")
                url = arguments.get("url")
                method = arguments.get("method")
                res = requests.request(method, url, timeout=15)
                res.raise_for_status()
                return res.text

            raise ValueError(f"Unknown tool: {name}")
        except Exception as e:
            raise RuntimeError(f"Tool {name} crashed: {e}") from e

    def query_local_llm(self, prompt_content, *, num_thread: int = 4):
        # Enforce exact 4 thread runtime to stay on hardware P-cores
        payload = {
            "model": MODEL_NAME,
            "prompt": f"System Tools available:\n{json.dumps(self.tools_schema)}\n\nUser Task: {prompt_content}\n\nRespond with a JSON object containing 'tool_to_call' and 'arguments' if needed, or 'final_response'.",
            "stream": False,
            "format": "json",
            "options": {"num_thread": int(num_thread)} 
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("Ollama response was not a JSON object")
        return body.get("response", "{}")

    def _compress_intermediate_tool_logs(self, logs: str, *, num_thread: int = 4) -> str:
        logs = str(logs or "").strip()
        if not logs:
            return ""
        if len(logs) > 30_000:
            logs = logs[-30_000:]

        prompt = (
            "INTERNAL COMPRESSOR:\n"
            "Compress the following intermediate tool logs into a single snapshot <= 500 characters.\n"
            "Keep file paths, error messages, and key outcomes. No markdown. Output ONLY the snapshot.\n\n"
            f"LOGS:\n{logs}\n"
        )
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"num_thread": int(num_thread)},
        }
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=45)
            response.raise_for_status()
            body = response.json()
            snapshot = str(body.get("response") or "").strip()
        except Exception:
            snapshot = ""

        if not snapshot:
            snapshot = logs[-500:].strip()
        if len(snapshot) > 500:
            snapshot = snapshot[:500].rstrip() + "…"
        return snapshot

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

    def _try_acquire_processing_lock(self, *, task_id: str, details: dict[str, object] | None = None) -> bool:
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
                payload: dict[str, object] = {
                    "task_id": task_id,
                    "pid": os.getpid(),
                    "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                if isinstance(details, dict):
                    for k, v in details.items():
                        if v is None:
                            continue
                        payload[str(k)] = v
                json.dump(payload, f, ensure_ascii=False, indent=2)
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
                    last_approved_code_snippet: str = ""

                    route = resolve_repo_governance_route(task_data)
                    system_context = build_governance_system_context(route)
                    prompt_history = [{"system_context": system_context}, {"instruction": instruction}]

                    # Bind the repository context for tool routing inside this task execution.
                    self._active_default_profile = bool(route.used_default_profile)
                    self._active_execution_constraints = dict(route.execution_constraints or {})
                    self._active_target_repository = route.resolved_repository or route.target_repository
                    self._active_primary_agent_class = str(route.primary_agent_class or "")
                    self._active_twin_agent_class = str(route.twin_agent_class or "")
                    try:
                        if self._active_default_profile:
                            self._active_repo_root = resolve_repo_root(None)
                            # Prefer local, read-only diagnostics when routing falls back.
                            self._active_target_repository = self._active_repo_root.name
                        else:
                            self._active_repo_root = resolve_repo_root(self._active_target_repository)
                    except Exception as exc:
                        # Fail closed: if we cannot resolve the repo root, do not allow tool execution.
                        self._active_repo_root = None
                        self._active_default_profile = True
                        self._active_execution_constraints = {}
                        self._active_target_repository = None
                        raise RuntimeError(f"Failed to resolve repository workspace root: {exc}") from exc

                    lock_details = {
                        "target_repository": self._active_target_repository,
                        "primary_agent_class": self._active_primary_agent_class,
                        "twin_agent_class": self._active_twin_agent_class,
                        "num_thread": int((route.execution_constraints or {}).get("num_thread") or 4),
                    }
                    if not self._try_acquire_processing_lock(task_id=task_id, details=lock_details):
                        # Another engine instance has compute priority, or lock is stale.
                        time.sleep(2)
                        continue
                    lock_acquired = True
                    task_start_monotonic = time.monotonic()
                    self._artifacts_created = set()

                    num_thread, max_context_chars = constraints_for_engine(route)
                    self._active_num_thread = int(num_thread)
                    self._active_task_twin_rejection_count = 0
                    self._active_task_refinement_recorded = False
                    repo_name_for_memory = self._active_target_repository or (
                        self._active_repo_root.name if self._active_repo_root is not None else ""
                    )
                    memory_context = ""
                    try:
                        memory_context = inject_relevant_memories(repo_name_for_memory, instruction)
                    except Exception:
                        memory_context = ""

                    base_chunks: list[str] = [system_context]
                    if memory_context:
                        base_chunks.append(memory_context)
                    base_chunks.append(instruction)
                    log_chunks: deque[str] = deque()
                    current_context_size = sum(len(chunk) + 1 for chunk in base_chunks) - 1

                    def append_context(chunk: str) -> None:
                        nonlocal current_context_size
                        chunk = chunk or ""
                        log_chunks.append(chunk)
                        current_context_size += len(chunk) + 1
                        while current_context_size > max_context_chars and log_chunks:
                            removed = log_chunks.popleft()
                            current_context_size -= len(removed) + 1

                    while current_loop < max_loops and not completed:
                        current_loop += 1
                        if current_loop in (3, 4) and log_chunks:
                            near_limit = current_context_size >= int(float(max_context_chars) * 0.85)
                            if near_limit:
                                snapshot = self._compress_intermediate_tool_logs(
                                    "\n".join(log_chunks),
                                    num_thread=num_thread,
                                )
                                log_chunks.clear()
                                log_chunks.append(f"Intermediate logs snapshot: {snapshot}")
                                current_context_size = (
                                    (sum(len(chunk) + 1 for chunk in base_chunks) - 1)
                                    + sum(len(chunk) + 1 for chunk in log_chunks)
                                )
                        try:
                            rendered = "\n".join(base_chunks + list(log_chunks))
                            raw_decision = self.query_local_llm(rendered, num_thread=num_thread)
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
                                tool_name = decision["tool_to_call"]
                                tool_args = decision.get("arguments", {}) or {}
                                if isinstance(tool_args, dict):
                                    if tool_name == "workspace_file_router" and tool_args.get("action") == "write":
                                        last_approved_code_snippet = str(tool_args.get("content") or "")
                                    elif tool_name == "execute_isolated_task":
                                        last_approved_code_snippet = str(tool_args.get("script_content") or "")
                                tool_output = self.execute_tool(tool_name, tool_args)
                            except TwinRejectedError as e:
                                prompt_history.append({"twin_rejection": e.feedback})
                                append_context(f"Twin Rejection: {e.feedback}")
                                continue
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
                        if self._active_task_twin_rejection_count > 0:
                            failure_summary = (
                                "DUAL_AGENT_CONSENSUS_TIMEOUT: "
                                "max loops reached without twin approval for code execution/write."
                            )
                        else:
                            failure_summary = "Loop breaker triggered: max loops reached"
                        self._handle_failure(
                            task_file=task_file,
                            task_id=task_id,
                            prompt_history=prompt_history,
                            error_message=failure_summary,
                            loop_count=current_loop,
                        )
                    elif completed and not failed and os.path.exists(task_file):
                        try:
                            consensus_snippet = last_approved_code_snippet.strip() or final_summary.strip()
                            if consensus_snippet:
                                append_memory(
                                    repo_name=repo_name_for_memory,
                                    task_summary=instruction,
                                    consensus_code_snippet=consensus_snippet,
                                )
                        except Exception:
                            pass
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
                    self._active_target_repository = None
                    self._active_repo_root = None
                    self._active_execution_constraints = {}
                    self._active_default_profile = False
                    self._active_primary_agent_class = None
                    self._active_twin_agent_class = None
                    self._active_num_thread = 4
                    self._active_task_twin_rejection_count = 0
                    self._active_task_refinement_recorded = False
                    if lock_acquired:
                        self._release_processing_lock()
                
            time.sleep(10) # Cooling sleep cycle to prevent CPU throttling


def _wrap_script_for_sandbox(script: str, *, readonly: bool, no_network: bool) -> str:
    """Best-effort safety prelude for scripts executed via execute_isolated_task."""

    prelude = f"""
READONLY = {bool(readonly)!r}
NO_NETWORK = {bool(no_network)!r}

def _deny(msg: str):
    raise PermissionError(msg)

def _mode_is_write(mode: str) -> bool:
    return any(flag in mode for flag in ("w", "a", "x", "+"))

if READONLY:
    import builtins as _builtins
    import os as _os
    import pathlib as _pathlib
    import shutil as _shutil
    import subprocess as _subprocess

    _orig_open = _builtins.open
    def _open(file, mode="r", *args, **kwargs):  # noqa: ANN001
        if _mode_is_write(str(mode)):
            _deny("read-only sandbox: writes are forbidden")
        return _orig_open(file, mode, *args, **kwargs)
    _builtins.open = _open

    _orig_path_open = _pathlib.Path.open
    def _path_open(self, mode="r", *args, **kwargs):  # noqa: ANN001
        if _mode_is_write(str(mode)):
            _deny("read-only sandbox: writes are forbidden")
        return _orig_path_open(self, mode, *args, **kwargs)
    _pathlib.Path.open = _path_open

    def _blocked(*args, **kwargs):  # noqa: ANN001
        _deny("read-only sandbox: filesystem mutation forbidden")

    _os.remove = _blocked
    _os.unlink = _blocked
    _os.rmdir = _blocked
    _os.mkdir = _blocked
    _os.makedirs = _blocked
    _os.rename = _blocked
    _os.replace = _blocked
    _os.chmod = _blocked
    _os.chown = _blocked
    _os.utime = _blocked
    _os.system = _blocked

    _pathlib.Path.unlink = _blocked
    _pathlib.Path.mkdir = _blocked
    _pathlib.Path.rmdir = _blocked
    _pathlib.Path.rename = _blocked
    _pathlib.Path.replace = _blocked

    _shutil.rmtree = _blocked
    _shutil.move = _blocked
    _shutil.copy = _blocked
    _shutil.copy2 = _blocked
    _shutil.copytree = _blocked

    _subprocess.Popen = _blocked
    _subprocess.call = _blocked
    _subprocess.check_call = _blocked
    _subprocess.check_output = _blocked
    _subprocess.run = _blocked

if NO_NETWORK:
    import socket as _socket
    import urllib.request as _urllib_request

    def _blocked_net(*args, **kwargs):  # noqa: ANN001
        _deny("network disabled by diagnostic sandbox")

    _socket.socket = _blocked_net
    _socket.create_connection = _blocked_net
    try:
        _urllib_request.urlopen = _blocked_net
    except Exception:
        pass
"""
    return prelude.lstrip() + "\n" + (script or "")


def _enforce_repo_path_constraints(rel: str, constraints: dict[str, object], *, action: str | None = None) -> None:
    """Optionally restrict workspace file access to per-repo allowed prefixes.

    Supports:
      - allowed_path_prefixes / deny_path_prefixes (applies to reads+writes)
      - allowed_write_path_prefixes / deny_write_path_prefixes (applies only when action == "write")
    """

    if not isinstance(rel, str):
        return
    normalized = Path(rel).as_posix().lstrip("/")
    while normalized.startswith("./"):
        normalized = normalized[2:]

    allow = constraints.get("allowed_path_prefixes")
    if isinstance(allow, list) and allow:
        allowed_prefixes = [str(x).strip().strip("/") for x in allow if isinstance(x, str) and str(x).strip()]
        if allowed_prefixes:
            ok = any(normalized == p or normalized.startswith(p + "/") for p in allowed_prefixes)
            if not ok:
                raise PermissionError("Path blocked by repository constraints (allowed_path_prefixes)")

    deny = constraints.get("deny_path_prefixes")
    if isinstance(deny, list) and deny:
        denied_prefixes = [str(x).strip().strip("/") for x in deny if isinstance(x, str) and str(x).strip()]
        if any(normalized == p or normalized.startswith(p + "/") for p in denied_prefixes):
            raise PermissionError("Path blocked by repository constraints (deny_path_prefixes)")

    if action != "write":
        return

    allow_write = constraints.get("allowed_write_path_prefixes")
    if isinstance(allow_write, list) and allow_write:
        allowed_prefixes = [str(x).strip().strip("/") for x in allow_write if isinstance(x, str) and str(x).strip()]
        if allowed_prefixes:
            ok = any(normalized == p or normalized.startswith(p + "/") for p in allowed_prefixes)
            if not ok:
                raise PermissionError("Path blocked by repository constraints (allowed_write_path_prefixes)")

    deny_write = constraints.get("deny_write_path_prefixes")
    if isinstance(deny_write, list) and deny_write:
        denied_prefixes = [str(x).strip().strip("/") for x in deny_write if isinstance(x, str) and str(x).strip()]
        if any(normalized == p or normalized.startswith(p + "/") for p in denied_prefixes):
            raise PermissionError("Path blocked by repository constraints (deny_write_path_prefixes)")

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
