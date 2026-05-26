import { Canvas, useFrame } from '@react-three/fiber'
import { Grid, Line } from '@react-three/drei'
import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import type { McpClient } from '../mcp/client'
import type { TelemetryEvent } from '../mcp/protocol'

type Props = {
  client: McpClient
  onConnectionChange?: (connected: boolean) => void
}

type NodeState = {
  id: string
  quarantined: boolean
  lastPulseMs: number
  lastQuarantineMs: number
}

function stableColorFor(id: string): THREE.Color {
  const hash = Array.from(id).reduce((acc, ch) => (acc * 33 + ch.charCodeAt(0)) >>> 0, 5381)
  const hue = hash % 360
  return new THREE.Color(`hsl(${hue}, 72%, 62%)`)
}

function Layout({
  nodes,
  edges,
  pulseMs,
}: {
  nodes: NodeState[]
  edges: Array<[string, string]>
  pulseMs: number
}) {
  const positions = useMemo(() => {
    const out = new Map<string, THREE.Vector3>()
    const ring = nodes
      .slice()
      .sort((a, b) => a.id.localeCompare(b.id))
      .map((n) => n.id)

    const radius = 3.1
    for (let i = 0; i < ring.length; i++) {
      const a = (i / Math.max(1, ring.length)) * Math.PI * 2
      out.set(ring[i], new THREE.Vector3(Math.cos(a) * radius, 0, Math.sin(a) * radius))
    }
    return out
  }, [nodes])

  return (
    <>
      <Grid
        args={[12, 12]}
        cellColor={'#18223f'}
        sectionColor={'#1c2a57'}
        fadeDistance={20}
        fadeStrength={1}
        infiniteGrid
      />

      {edges.map(([a, b]) => {
        const pa = positions.get(a)
        const pb = positions.get(b)
        const na = nodes.find((n) => n.id === a)
        const nb = nodes.find((n) => n.id === b)
        if (!pa || !pb || !na || !nb) return null
        if (na.quarantined || nb.quarantined) return null
        return (
          <Line
            key={`${a}:${b}`}
            points={[pa, pb]}
            color={'#22d3ee'}
            transparent
            opacity={0.14}
            lineWidth={1}
          />
        )
      })}

      {nodes.map((n) => {
        const p = positions.get(n.id)
        if (!p) return null
        return <Node key={n.id} node={n} position={p} pulseMs={pulseMs} />
      })}

      <MerkleTree pulseMs={pulseMs} />
    </>
  )
}

function Node({ node, position, pulseMs }: { node: NodeState; position: THREE.Vector3; pulseMs: number }) {
  const meshRef = useRef<THREE.Mesh>(null)
  const ringRef = useRef<THREE.Mesh>(null)
  const base = useMemo(() => stableColorFor(node.id), [node.id])
  const emissive = useMemo(() => new THREE.Color('#22d3ee'), [])

  useFrame(() => {
    const now = performance.now()
    const p = meshRef.current
    if (p) {
      p.position.lerp(position, 0.2)
      p.rotation.y += 0.002
    }
    const ring = ringRef.current
    if (ring) {
      ring.position.copy(position)
      ring.rotation.x = Math.PI / 2
      const age = now - node.lastQuarantineMs
      ring.visible = node.quarantined && age < 30_000
      ring.scale.setScalar(1 + Math.min(0.4, age / 2500))
    }

    const mat = p?.material as THREE.MeshStandardMaterial | undefined
    if (!mat) return
    const age = now - pulseMs
    const local = Math.min(1, Math.max(0, 1 - age / 650))
    const hot = Math.max(local, Math.min(1, Math.max(0, 1 - (now - node.lastPulseMs) / 650)))
    mat.emissive = emissive
    mat.emissiveIntensity = node.quarantined ? 0.2 : 0.05 + hot * 2.2
    mat.color = node.quarantined ? new THREE.Color('#fb7185') : base
    mat.opacity = node.quarantined ? 0.55 : 0.38
  })

  return (
    <>
      <mesh ref={meshRef} position={position.toArray()} castShadow>
        <sphereGeometry args={[0.24, 32, 32]} />
        <meshStandardMaterial
          color={base}
          roughness={0.1}
          metalness={0.35}
          transparent
          opacity={0.38}
        />
      </mesh>
      <mesh ref={ringRef}>
        <torusGeometry args={[0.42, 0.02, 16, 96]} />
        <meshStandardMaterial
          color={'#f59e0b'}
          emissive={'#f59e0b'}
          emissiveIntensity={1.7}
          transparent
          opacity={0.7}
        />
      </mesh>
    </>
  )
}

function MerkleTree({ pulseMs }: { pulseMs: number }) {
  const pointsRef = useRef<THREE.Points>(null)
  const rootRef = useRef<THREE.Mesh>(null)
  const geom = useMemo(() => new THREE.BufferGeometry(), [])
  const count = 96

  const base = useMemo(() => {
    const arr = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const t = i / count
      const y = 0.8 + t * 1.6
      const r = (1 - t) * 1.3
      const a = t * Math.PI * 7
      arr[i * 3 + 0] = Math.cos(a) * r
      arr[i * 3 + 1] = y
      arr[i * 3 + 2] = Math.sin(a) * r
    }
    return arr
  }, [])

  const current = useRef<Float32Array>(new Float32Array(base))
  const target = useRef<Float32Array>(new Float32Array(base))

  useEffect(() => {
    geom.setAttribute('position', new THREE.BufferAttribute(current.current, 3))
  }, [geom])

  useFrame(() => {
    const now = performance.now()
    const age = now - pulseMs
    const impl = Math.min(1, Math.max(0, 1 - age / 850))

    for (let i = 0; i < count; i++) {
      const bx = base[i * 3 + 0]
      const by = base[i * 3 + 1]
      const bz = base[i * 3 + 2]
      target.current[i * 3 + 0] = bx * (1 - impl)
      target.current[i * 3 + 1] = by + impl * 0.4
      target.current[i * 3 + 2] = bz * (1 - impl)
    }

    const pos = current.current
    for (let i = 0; i < pos.length; i++) {
      pos[i] += (target.current[i] - pos[i]) * 0.12
    }
    const pts = pointsRef.current
    if (pts) {
      const attr = pts.geometry.getAttribute('position') as THREE.BufferAttribute
      attr.needsUpdate = true
    }
    const root = rootRef.current
    if (root) {
      root.visible = age < 1200
      root.position.set(0, 2.8, 0)
      root.rotation.y += 0.03
      root.scale.setScalar(0.22 + impl * 0.32)
    }
  })

  return (
    <>
      <points ref={pointsRef} geometry={geom} position={[0, 0, 0]}>
        <pointsMaterial
          color={'#22d3ee'}
          size={0.035}
          sizeAttenuation
          transparent
          opacity={0.75}
        />
      </points>
      <mesh ref={rootRef}>
        <icosahedronGeometry args={[0.35, 1]} />
        <meshStandardMaterial
          color={'#22d3ee'}
          emissive={'#22d3ee'}
          emissiveIntensity={2.4}
          transparent
          opacity={0.8}
        />
      </mesh>
    </>
  )
}

export default function TelemetryCanvas({ client, onConnectionChange }: Props) {
  const [nodes, setNodes] = useState<Record<string, NodeState>>(() => ({
    ISA: { id: 'ISA', quarantined: false, lastPulseMs: 0, lastQuarantineMs: 0 },
    SAS: { id: 'SAS', quarantined: false, lastPulseMs: 0, lastQuarantineMs: 0 },
    CRS: { id: 'CRS', quarantined: false, lastPulseMs: 0, lastQuarantineMs: 0 },
    BOA: { id: 'BOA', quarantined: false, lastPulseMs: 0, lastQuarantineMs: 0 },
  }))
  const [pulseMs, setPulseMs] = useState(0)

  useEffect(() => {
    const off = client.onState((st) => onConnectionChange?.(st === 'open'))
    return () => off()
  }, [client, onConnectionChange])

  useEffect(() => {
    const off = client.onEvent((ev: TelemetryEvent) => {
      const now = performance.now()
      if (ev.kind === 'LEDGER_BLOCK' && ev.rollup) {
        setPulseMs(now)
        setNodes((prev) => {
          const next = { ...prev }
          const id = String(ev.node_id || 'node')
          const n = next[id] ?? { id, quarantined: false, lastPulseMs: 0, lastQuarantineMs: 0 }
          next[id] = { ...n, quarantined: false, lastPulseMs: now }
          return next
        })
      }
      if (ev.kind === 'FRAUD_PROOF_QUARANTINE') {
        setNodes((prev) => {
          const next = { ...prev }
          const peer = String(ev.peer_id || 'unknown')
          const n = next[peer] ?? { id: peer, quarantined: false, lastPulseMs: 0, lastQuarantineMs: 0 }
          next[peer] = { ...n, quarantined: true, lastQuarantineMs: now }
          return next
        })
      }
    })
    client.connect()
    return () => off()
  }, [client])

  const nodeList = Object.values(nodes)
  const ids = nodeList.map((n) => n.id).sort()
  const edges: Array<[string, string]> = []
  for (let i = 0; i < ids.length; i++) {
    for (let j = i + 1; j < ids.length; j++) {
      edges.push([ids[i], ids[j]])
    }
  }

  return (
    <Canvas
      dpr={[1, 2]}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      camera={{ position: [0, 4.8, 7.4], fov: 45, near: 0.1, far: 100 }}
    >
      <ambientLight intensity={0.35} />
      <directionalLight position={[4, 7, 2]} intensity={1.3} />
      <Layout nodes={nodeList} edges={edges} pulseMs={pulseMs} />
    </Canvas>
  )
}
