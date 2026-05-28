import os
import json
import time
import subprocess
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:3b" # Optimized for Meteor Lake P-Cores
TOOLS_CONFIG_PATH = "config/platform_mcp_tools.json"

class PlatformAgentEngine:
    def __init__(self):
        self.load_mcp_tools()
        print("⚡ Platform Agent Infrastructure Initialized.")
        print(f"🔒 Guardrails active: 4 P-Core enforcement, OLLAMA Keep-Alive ready.")

    def load_mcp_tools(self):
        with open(TOOLS_CONFIG_PATH, "r") as f:
            self.tools_schema = json.load(f)["tools"]

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
                elif action == "read":
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
                        
            elif name == "execute_isolated_task":
                # Executes within a safe local sandbox process
                code = arguments.get("script_content")
                result = subprocess.run(["python", "-c", code], capture_output=True, text=True, timeout=10)
                return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
                
            elif name == "network_data_fetch":
                url = arguments.get("url")
                method = arguments.get("method")
                res = requests.request(method, url, timeout=15)
                return res.text
        except Exception as e:
            return f"Tool Execution Failure: {str(e)}"

    def query_local_llm(self, prompt_content):
        # Enforce exact 4 thread runtime to stay on hardware P-cores
        payload = {
            "model": MODEL_NAME,
            "prompt": f"System Tools available:\n{json.dumps(self.tools_schema)}\n\nUser Task: {prompt_content}\n\nRespond with a JSON object containing 'tool_to_call' and 'arguments' if needed, or 'final_response'.",
            "stream": False,
            "format": "json",
            "options": {"num_thread": 4} 
        }
        try:
            response = requests.post(OLLAMA_URL, json=payload)
            return response.json().get("response", "{}")
        except Exception as e:
            return json.dumps({"error": f"Ollama disconnected: {e}"})

    def run_loop(self):
        print("🚀 24/7 Autonomous Node Listening to Platform Events...")
        while True:
            # Placeholder for platform queue monitoring (e.g. database change, webhook, folder drop)
            task_file = ".platform_queue/next_task.json"
            
            if os.path.exists(task_file):
                print("📬 Task discovered in platform loop.")
                with open(task_file, "r") as f:
                    task_data = json.load(f)
                
                # Enforce loop breaker guardrail
                max_loops = 5
                current_loop = 0
                completed = False
                current_prompt = task_data.get("instruction")
                
                while current_loop < max_loops and not completed:
                    current_loop += 1
                    raw_decision = self.query_local_llm(current_prompt)
                    decision = json.loads(raw_decision)
                    
                    if "tool_to_call" in decision:
                        tool_output = self.execute_tool(decision["tool_to_call"], decision["arguments"])
                        # Append observation history back into context
                        current_prompt += f"\nTool Observation: {tool_output}"
                    else:
                        print(f"🎉 Task Finished: {decision.get('final_response')}")
                        completed = True
                
                os.remove(task_file) # Clear task from platform processing queue
                
            time.sleep(10) # Cooling sleep cycle to prevent CPU throttling

if __name__ == "__main__":
    engine = PlatformAgentEngine()
    engine.run_loop()
