# REMOTE-AGENTS

Autonomous multi-agent office runtime.

## Run

1) Ensure `AGENT_GUIDE_LIST.md` and `DESIGNATED_AGENTS_LIST.md` exist in the repo root.
2) Execute:

python run_autonomous_office.py --business-case "Build the core runtime for REMOTE-AGENTS."

Governance events are written to `logs/governance.jsonl`.

## 3D Dashboard

- Frontend: `packages/dashboard-3d/` (Vite + TS + Tailwind + R3F)
- Backend bridge module: `core/mcp_bridge.py` (stdlib-only WebSocket + MCP-style tools/events)
- Integration rig: `tests/test_3d_canvas_integration.py`
