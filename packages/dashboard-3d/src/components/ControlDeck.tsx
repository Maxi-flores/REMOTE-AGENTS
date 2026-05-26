import { useCallback, useMemo, useState } from 'react'
import type { McpClient } from '../mcp/client'

type Props = {
  client: McpClient
  connected: boolean
}

function Toggle({
  label,
  on,
  onToggle,
}: {
  label: string
  on: boolean
  onToggle: (next: boolean) => void
}) {
  return (
    <button
      type="button"
      className="group flex w-full items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-left shadow-glass backdrop-blur-glass transition hover:bg-white/10"
      onClick={() => onToggle(!on)}
    >
      <span className="text-sm text-white/85">{label}</span>
      <span
        className={[
          'relative h-6 w-11 rounded-full border border-white/10 transition',
          on ? 'bg-neon-cyan/30' : 'bg-white/10',
        ].join(' ')}
      >
        <span
          className={[
            'absolute top-1/2 h-5 w-5 -translate-y-1/2 rounded-full bg-white/80 shadow transition',
            on ? 'left-6' : 'left-1',
          ].join(' ')}
        />
      </span>
    </button>
  )
}

export default function ControlDeck({ client, connected }: Props) {
  const [batchBoost, setBatchBoost] = useState(false)
  const [busy, setBusy] = useState(false)
  const batchSize = useMemo(() => (batchBoost ? 200 : 100), [batchBoost])

  const call = useCallback(
    async (name: string, args: Record<string, unknown>) => {
      setBusy(true)
      try {
        await client.callTool({ name, arguments: args })
      } finally {
        setBusy(false)
      }
    },
    [client],
  )

  return (
    <div className="pointer-events-none fixed inset-0">
      <div className="pointer-events-auto absolute left-4 top-4 w-[320px] space-y-3">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3 shadow-glass backdrop-blur-glass">
          <div className="flex items-center justify-between">
            <div className="text-xs uppercase tracking-widest text-white/55">
              MCP Switches
            </div>
            <div
              className={[
                'text-xs',
                connected ? 'text-neon-cyan' : 'text-white/55',
              ].join(' ')}
            >
              {connected ? 'Linked' : 'Offline'}
            </div>
          </div>
          <div className="mt-3 space-y-2">
            <Toggle
              label={`Batch Ceiling (${batchSize})`}
              on={batchBoost}
              onToggle={(next) => {
                setBatchBoost(next)
                void call('batch_ceiling', { batch_size: next ? 200 : 100 })
              }}
            />
            <button
              type="button"
              className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/85 shadow-glass backdrop-blur-glass transition hover:bg-white/10 disabled:opacity-40"
              disabled={busy}
              onClick={() => void call('quarantine_flush', {})}
            >
              Quarantine Flush
            </button>
            <button
              type="button"
              className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/85 shadow-glass backdrop-blur-glass transition hover:bg-white/10 disabled:opacity-40"
              disabled={busy}
              onClick={() => void call('cache_evict', {})}
            >
              Cache Eviction Valve
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-xs text-white/55 shadow-glass backdrop-blur-glass">
          <div>Endpoint: {client.url}</div>
          <div className="mt-1">Tools: batch_ceiling, quarantine_flush, cache_evict</div>
        </div>
      </div>
    </div>
  )
}
