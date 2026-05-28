# Local Autonomous Platform Agent Workspace

This package runs a 24/7 background worker utilizing local system hardware via the Model Context Protocol (MCP).

### ⚙️ Prerequisites
1. Windows 11 on Intel Core Ultra 5 (Meteor Lake)
2. 32GB RAM available
3. <a href="https://ollama.com">Ollama Desktop installed</a> with `qwen2.5-coder:3b` pulled
4. Set the host environment configuration to prevent swapping: `OLLAMA_KEEP_ALIVE=-1`

### 🚀 Launching the Production Workspace Engine
To spin up the continuous platform worker loop, execute via your standard development terminal:

```bash
python src/orchastrator/platform_engine.py
```

> Note: the repository directory is currently named `src/orchastrator/`.

To feed the agent a task, drop a JSON packet containing `{"instruction": "your text command here"}` into `.platform_queue/next_task.json`.
Optionally include `target_repository` (e.g. `{"instruction":"...", "target_repository":"ConceptSHOP"}`) to activate multi-repo governance routing.

Alternatively, use the manual dispatcher CLI (atomic single-flight writer):

```bash
python src/orchestrator/dispatcher.py --repo "ConceptSHOP" --task "Update Vite proxy config to point to new API port" --priority 2
```

Manual stale-lock prune (debugging escape hatch):

```bash
python src/orchestrator/dispatcher.py --flush-locks
```

On boot, the worker initializes `.platform_queue/` and `.logs/`. Failures are appended to `.logs/errors.json`, and failing payloads are archived to `.platform_queue/failed/` for human review.

### 🌐 Live Event Ingestion Gateway (HTTP + WebSocket)
For real-time triggers, run the async ingestion gateway (stdlib-only):

```bash
python src/orchestrator/gateway.py
```

- `POST /api/v1/trigger` with JSON `{"instruction":"..."}` enqueues a task.
- `GET /health` reports `Idle`, `Processing`, or `Error-Locked`.
- `GET /ws/events` upgrades to WebSocket; each text frame must be JSON containing `{"instruction":"..."}`.

### 🖥️ Terminal Command Center Dashboard (TUI)
For a live operator view (repo matrix + semantic memory counts + telemetry), run:

```bash
python src/ui/terminal_dashboard.py
```

## Additional Repository Components

- Office runtime entrypoint: `run_autonomous_office.py`
- 3D dashboard frontend: `packages/dashboard-3d/`
- Backend bridge module: `core/mcp_bridge.py`
- Integration rig: `tests/test_3d_canvas_integration.py`
