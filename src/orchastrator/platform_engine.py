import os
import json
import time
import subprocess
import requests
import sys
from collections import deque
from pathlib import Path
import traceback

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from tools.logger import archive_failed_payload, ensure_runtime_directories, log_agent_failure

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:3b" # Optimized for Meteor Lake P-Cores
TOOLS_CONFIG_PATH = "config/platform_mcp_tools.json"

class PlatformAgentEngine:
    def __init__(self):
        ensure_runtime_directories()
        self.load_mcp_tools()
        print("⚡ Platform Agent Infrastructure Initialized.")
        print(f"🔒 Guardrails active: 4 P-Core enforcement, OLLAMA Keep-Alive ready.")

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

    def run_loop(self):
        print("🚀 24/7 Autonomous Node Listening to Platform Events...")
        while True:
            # Placeholder for platform queue monitoring (e.g. database change, webhook, folder drop)
            task_file = ".platform_queue/next_task.json"
            
            if os.path.exists(task_file):
                print("📬 Task discovered in platform loop.")
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
                task_id = task_data.get("task_id") or task_data.get("id") or os.path.basename(task_file)
                instruction = task_data.get("instruction") or ""
                prompt_history = [{"instruction": instruction}]

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
                        self._handle_failure(
                            task_file=task_file,
                            task_id=task_id,
                            prompt_history=prompt_history,
                            error_message=f"Ollama disconnected: {e}",
                            loop_count=current_loop,
                        )
                        completed = True
                        break

                    prompt_history.append({"raw_decision": raw_decision})
                    try:
                        decision = json.loads(raw_decision)
                    except Exception as e:
                        self._handle_failure(
                            task_file=task_file,
                            task_id=task_id,
                            prompt_history=prompt_history,
                            error_message=f"Model formatting failure (invalid JSON): {e}",
                            loop_count=current_loop,
                        )
                        completed = True
                        break
                    
                    if "tool_to_call" in decision:
                        try:
                            tool_output = self.execute_tool(decision["tool_to_call"], decision.get("arguments", {}))
                        except Exception as e:
                            self._handle_failure(
                                task_file=task_file,
                                task_id=task_id,
                                prompt_history=prompt_history,
                                error_message=str(e),
                                loop_count=current_loop,
                            )
                            completed = True
                            break
                        prompt_history.append({"tool_output": tool_output})
                        append_context(f"Tool Observation: {tool_output}")
                    else:
                        print(f"🎉 Task Finished: {decision.get('final_response')}")
                        completed = True
                
                if not completed and current_loop >= max_loops:
                    self._handle_failure(
                        task_file=task_file,
                        task_id=task_id,
                        prompt_history=prompt_history,
                        error_message="Loop breaker triggered: max loops reached",
                        loop_count=current_loop,
                    )
                elif os.path.exists(task_file):
                    os.remove(task_file) # Clear task from platform processing queue
                
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
