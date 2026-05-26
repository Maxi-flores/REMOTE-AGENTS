export type JsonRpcId = string | number | null

export type JsonRpcNotification<TMethod extends string, TParams> = {
  jsonrpc: '2.0'
  method: TMethod
  params: TParams
}

export type JsonRpcRequest<TMethod extends string, TParams> = {
  jsonrpc: '2.0'
  id: JsonRpcId
  method: TMethod
  params: TParams
}

export type JsonRpcResponse<TResult> = {
  jsonrpc: '2.0'
  id: JsonRpcId
  result?: TResult
  error?: { code: number; message: string; data?: unknown }
}

export type RollupTelemetry = {
  batch_id?: string
  seq_start?: number
  seq_end?: number
  tx_count?: number
  merkle_root?: string
  correlation_mask?: string
  execution_token_hash?: string
  target_ledger_root?: string
  algo?: string
}

export type TelemetryEvent = {
  ts_utc: string
  node_id: string
  kind: string
  index?: number
  hash?: string
  prev_hash?: string
  execution_token?: string
  rollup?: RollupTelemetry
  peer_id?: string
  correlation_mask?: string
  details?: Record<string, unknown>
}

export type TelemetryNotification = JsonRpcNotification<'telemetry/event', TelemetryEvent>

export type ToolsCallParams = {
  name: string
  arguments?: Record<string, unknown>
}

export type ToolsListResult = {
  tools: Array<{ name: string; description?: string }>
}

export type ToolsCallResult = {
  content: Array<{ type: 'json'; json: unknown }>
}

