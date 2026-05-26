import type {
  JsonRpcId,
  JsonRpcResponse,
  TelemetryEvent,
  TelemetryNotification,
  ToolsCallParams,
  ToolsCallResult,
  ToolsListResult,
} from './protocol'

type ConnectionState = 'closed' | 'connecting' | 'open'

type Listener = (ev: TelemetryEvent) => void
type StateListener = (state: ConnectionState) => void

function isRecord(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === 'object' && !Array.isArray(v)
}

function isTelemetryNotification(msg: unknown): msg is TelemetryNotification {
  if (!isRecord(msg)) return false
  const jsonrpc = msg.jsonrpc
  const method = msg.method
  const params = msg.params
  return jsonrpc === '2.0' && method === 'telemetry/event' && isRecord(params)
}

export class McpClient {
  readonly url: string
  private ws: WebSocket | null = null
  private state: ConnectionState = 'closed'
  private listeners = new Set<Listener>()
  private stateListeners = new Set<StateListener>()
  private pending = new Map<string, (msg: JsonRpcResponse<unknown>) => void>()
  private reconnectTimer: number | null = null

  constructor(url: string) {
    this.url = url
  }

  onEvent(cb: Listener): () => void {
    this.listeners.add(cb)
    return () => this.listeners.delete(cb)
  }

  onState(cb: StateListener): () => void {
    this.stateListeners.add(cb)
    cb(this.state)
    return () => this.stateListeners.delete(cb)
  }

  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return
    this.setState('connecting')
    const ws = new WebSocket(this.url)
    this.ws = ws

    ws.onopen = () => {
      this.setState('open')
    }
    ws.onclose = () => {
      this.setState('closed')
      this.scheduleReconnect()
    }
    ws.onerror = () => {
      this.setState('closed')
      try {
        ws.close()
      } catch {
        // ignore
      }
      this.scheduleReconnect()
    }
    ws.onmessage = (evt) => {
      let msg: unknown
      try {
        msg = JSON.parse(String(evt.data))
      } catch {
        return
      }
      if (isTelemetryNotification(msg)) {
        for (const cb of this.listeners) cb(msg.params)
        return
      }
      if (!isRecord(msg)) return
      const id = msg.id
      if (id === undefined || id === null) return
      const key = String(id as JsonRpcId)
      const resolver = this.pending.get(key)
      if (!resolver) return
      this.pending.delete(key)
      resolver(msg as JsonRpcResponse<unknown>)
    }
  }

  disconnect(): void {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (!this.ws) return
    try {
      this.ws.close()
    } catch {
      // ignore
    }
    this.ws = null
    this.setState('closed')
  }

  async listTools(): Promise<ToolsListResult> {
    const res = await this.request<'tools/list', Record<string, never>, ToolsListResult>('tools/list', {})
    return res
  }

  async callTool(params: ToolsCallParams): Promise<ToolsCallResult> {
    const res = await this.request<'tools/call', ToolsCallParams, ToolsCallResult>('tools/call', params)
    return res
  }

  private request<TMethod extends string, TParams, TResult>(method: TMethod, params: TParams): Promise<TResult> {
    this.connect()
    const ws = this.ws
    if (!ws) return Promise.reject(new Error('socket not available'))
    const id: JsonRpcId = `${Date.now()}-${Math.random().toString(16).slice(2)}`
    const payload = { jsonrpc: '2.0', id, method, params }
    return new Promise<TResult>((resolve, reject) => {
      this.pending.set(String(id), (resp) => {
        if (resp.error) reject(new Error(resp.error.message))
        else resolve(resp.result as TResult)
      })
      try {
        ws.send(JSON.stringify(payload))
      } catch (e) {
        this.pending.delete(String(id))
        reject(e)
      }
    })
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null) return
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, 600)
  }

  private setState(next: ConnectionState): void {
    if (this.state === next) return
    this.state = next
    for (const cb of this.stateListeners) cb(next)
  }
}
