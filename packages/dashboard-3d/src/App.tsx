import { useMemo, useState } from 'react'
import ControlDeck from './components/ControlDeck'
import TelemetryCanvas from './components/TelemetryCanvas'
import { McpClient } from './mcp/client'

const DEFAULT_MCP_URL = 'ws://127.0.0.1:8765'

function App() {
  const url = import.meta.env.VITE_MCP_URL || DEFAULT_MCP_URL
  const client = useMemo(() => new McpClient(String(url)), [url])
  const [connected, setConnected] = useState(false)

  return (
    <div className="h-full w-full">
      <TelemetryCanvas client={client} onConnectionChange={setConnected} />
      <ControlDeck client={client} connected={connected} />
    </div>
  )
}

export default App
