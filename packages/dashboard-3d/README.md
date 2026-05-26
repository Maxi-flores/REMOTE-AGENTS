# `dashboard-3d`

Hyper-minimal Three.js / React Three Fiber (R3F) canvas for visualizing rollup + consensus health via an MCP WebSocket bridge (`core/mcp_bridge.py`).

## Run

From the repo root:

- Install: `npm install`
- Dev server: `npm --workspace packages/dashboard-3d run dev`
- Point the client at the bridge: `VITE_MCP_URL=ws://127.0.0.1:8765 npm --workspace packages/dashboard-3d run dev`

## MCP Messages

- Subscribes to JSON-RPC notifications: `method="telemetry/event"`
- Switches use MCP-style tool calls: `method="tools/call"` with tool names:
  - `batch_ceiling` (`{ batch_size: number }`)
  - `quarantine_flush` (`{}` or `{ node_id: string }`)
  - `cache_evict` (`{}`)
