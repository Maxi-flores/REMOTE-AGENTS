import fs from "node:fs";
import path from "node:path";

// Regenerate from repo root:
//   node docs/generate_enterprise_architecture_drawio.mjs

const outputPath = path.join(
  "docs",
  "REMOTE_AGENTS_SENTIENT_OS_ENTERPRISE_ARCHITECTURE.drawio",
);

const pageNames = [
  "Executive System Overview",
  "Agent Pipeline Architecture",
  "Expert Roles Per Repository",
  "Mission Engine Lifecycle",
  "Consensus + Approval Flow",
  "MCP Tool Router Internals",
  "Semantic Memory Graph",
  "Distributed Execution Roadmap",
  "Sentient OS Integration",
  "Registry Architecture",
];

const palette = {
  frontend: { fill: "#e9f2ff", stroke: "#2f6fb3" },
  backend: { fill: "#eef8f1", stroke: "#3c8b57" },
  governance: { fill: "#fff4df", stroke: "#c9871b" },
  runtime: { fill: "#f2edff", stroke: "#7a57c2" },
  tools: { fill: "#e9fbfb", stroke: "#188b91" },
  repos: { fill: "#f7f7f7", stroke: "#646464" },
  memory: { fill: "#fff0f5", stroke: "#b85078" },
  future: { fill: "#f2f2f2", stroke: "#8a8a8a", dashed: true },
  risk: { fill: "#ffe7e7", stroke: "#c04444" },
  dark: { fill: "#263238", stroke: "#263238" },
};

const crewFamilies = [
  {
    family: "Full-Stack Ecosystem Crew",
    repos: ["Dealinstinct Frontend", "Dealinstinct V2", "Bikerinstinct", "WOMmedia", "ConceptSHOP", "Powerframe-CRM", "TheRocketTree-Web"],
    primary: "Application Feature Architect",
    twin: "Framework & UX Compliance Auditor",
    responsibilities: "UI layers; API routes; configuration wrappers; frontend business logic; routing consistency; framework compliance; UX/layout validation",
    color: "frontend",
    statusByRepo: {
      "Dealinstinct Frontend": "Ready",
      "Dealinstinct V2": "Ready",
      Bikerinstinct: "Ready",
      WOMmedia: "Ready",
      ConceptSHOP: "Ready",
      "Powerframe-CRM": "Ready",
      "TheRocketTree-Web": "Ready",
    },
    notesByRepo: {
      "Dealinstinct Frontend": "Plasmic token and duplicate layout risk noted in guide",
      "Dealinstinct V2": "Plasmic token and duplicate layout risk noted in guide",
      Bikerinstinct: "Hardcoded Plasmic token, layout clash, local path symlink risk",
      WOMmedia: "Hardcoded content; missing infra/CI docs",
      ConceptSHOP: "Client-side AWS/Firebase parameter exposure risk",
      "Powerframe-CRM": "Missing env sample; duplicated module structures",
      "TheRocketTree-Web": "No CI/lint config; CDN layout dependency",
    },
  },
  {
    family: "Data Core & Infrastructure Crew",
    repos: ["Powerframe", "PowerStarter", "TheRocketTree-App", "Powerframe-GMS", "Powerframe-TPR", "Powerframe-WMS", "Trade-Agent-V1"],
    primary: "Pipeline & Systems Automation Engineer",
    twin: "Security, Schema & Edge-Case Validator",
    responsibilities: "Data schemas; background workers; workflow automation; SQLite/Firebase/JSON pipelines; input serialization; data leakage prevention; transactional safety",
    color: "backend",
    statusByRepo: {
      Powerframe: "Ready",
      PowerStarter: "Ready",
      "TheRocketTree-App": "Ready",
      "Powerframe-GMS": "Ready",
      "Powerframe-TPR": "Ready",
      "Powerframe-WMS": "Ready",
      "Trade-Agent-V1": "Ready",
    },
    notesByRepo: {
      Powerframe: "Hub/orchestrator; auth fallback secret and naming drift risk",
      PowerStarter: "pnpm monorepo; docker-compose path and container context drift",
      "TheRocketTree-App": "pnpm/Turborepo/Prisma hub with Unity adapter contracts",
      "Powerframe-GMS": "Placeholder Firebase values and JWT fallback risk",
      "Powerframe-TPR": "Multiple manifests and Vite version drift risk",
      "Powerframe-WMS": "Implemented tree smaller than docs/specs",
      "Trade-Agent-V1": "No Docker/CI; SQLite workflow persistence",
    },
  },
  {
    family: "3D Graphics & Neural Pipeline Crew",
    repos: ["Sapient KB", "TheRocketTreeUnity", "Mucho3D", "PF-WAI"],
    primary: "Spatial Math & Tensor Graph Optimizer",
    twin: "Finite-Number & Sandbox Security Sentinel",
    responsibilities: "3D transforms; geometry arrays; Blender/Houdini/Unity pipeline; finite-number validation; sandbox execution; matrix validation; generated asset safety",
    color: "runtime",
    statusByRepo: {
      "Sapient KB": "Ready",
      TheRocketTreeUnity: "Ready",
      Mucho3D: "Pending",
      "PF-WAI": "Pending",
    },
    notesByRepo: {
      "Sapient KB": "R3F/drei plus monorepo build path risk",
      TheRocketTreeUnity: "Unity 6000.3.2f1; Functions/MCP package gaps",
      Mucho3D: "Guide says pending; registry has 3DSceneOrchestratorAgent",
      "PF-WAI": "Guide says pending; registry has readonly tensor adapter constraints",
    },
  },
  {
    family: "System Diagnostic Crew",
    repos: ["Unmapped repositories", "Corrupted payload targets", "Unknown repo names", "Fallback runtime states"],
    primary: "Runtime Diagnostic Troubleshooter",
    twin: "Low-Privilege Safety Guardian",
    responsibilities: "Read-only diagnostics; syntax failure analysis; fallback patch proposals; lock/error tracking; network blocking; low privilege operation",
    color: "risk",
    statusByRepo: {
      "Unmapped repositories": "Fallback",
      "Corrupted payload targets": "Fallback",
      "Unknown repo names": "Fallback",
      "Fallback runtime states": "Fallback",
    },
    notesByRepo: {
      "Unmapped repositories": "Routes through default_profile in agent_registry.json",
      "Corrupted payload targets": "Read-only diagnostics and structured error telemetry",
      "Unknown repo names": "Low-privilege safety path",
      "Fallback runtime states": "Keep worker loop unblocked without unauthorized scripts",
    },
  },
];

function xmlEscape(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function b64(value) {
  return Buffer.from(value, "utf8").toString("base64");
}

function colorStyle(kind, extra = "") {
  const c = palette[kind] || palette.backend;
  const dashed = c.dashed ? "dashed=1;" : "";
  return `rounded=1;whiteSpace=wrap;html=1;arcSize=8;fillColor=${c.fill};strokeColor=${c.stroke};strokeWidth=2;fontColor=#1f2933;${dashed}${extra}`;
}

function edgeStyle(kind = "normal", extra = "") {
  const stroke = kind === "risk" ? palette.risk.stroke : kind === "future" ? "#777777" : "#59636e";
  const dashed = kind === "future" ? "dashed=1;" : "";
  return `edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeWidth=2;strokeColor=${stroke};${dashed}${extra}`;
}

function diagram(pageName, width, height, build) {
  const state = {
    nextId: 2,
    cells: [
      '<mxCell id="0"/>',
      '<mxCell id="1" parent="0"/>',
    ],
  };
  const api = {
    rect(value, x, y, w, h, kind = "backend", styleExtra = "") {
      const id = String(state.nextId++);
      const style = colorStyle(kind, styleExtra);
      state.cells.push(`<mxCell id="${id}" value="${xmlEscape(value)}" style="${style}" vertex="1" parent="1"><mxGeometry x="${x}" y="${y}" width="${w}" height="${h}" as="geometry"/></mxCell>`);
      return id;
    },
    swim(value, x, y, w, h, kind = "backend") {
      const id = String(state.nextId++);
      const c = palette[kind] || palette.backend;
      const style = `swimlane;html=1;rounded=1;arcSize=8;startSize=34;fontStyle=1;fontSize=14;fillColor=${c.fill};strokeColor=${c.stroke};strokeWidth=2;`;
      state.cells.push(`<mxCell id="${id}" value="${xmlEscape(value)}" style="${style}" vertex="1" parent="1"><mxGeometry x="${x}" y="${y}" width="${w}" height="${h}" as="geometry"/></mxCell>`);
      return id;
    },
    note(value, x, y, w, h, kind = "future") {
      return this.rect(value, x, y, w, h, kind, "shape=note;whiteSpace=wrap;size=18;");
    },
    diamond(value, x, y, w, h, kind = "governance") {
      const id = String(state.nextId++);
      const c = palette[kind] || palette.governance;
      const style = `rhombus;whiteSpace=wrap;html=1;fillColor=${c.fill};strokeColor=${c.stroke};strokeWidth=2;fontColor=#1f2933;`;
      state.cells.push(`<mxCell id="${id}" value="${xmlEscape(value)}" style="${style}" vertex="1" parent="1"><mxGeometry x="${x}" y="${y}" width="${w}" height="${h}" as="geometry"/></mxCell>`);
      return id;
    },
    edge(source, target, label = "", kind = "normal", styleExtra = "") {
      const id = String(state.nextId++);
      const style = edgeStyle(kind, styleExtra);
      state.cells.push(`<mxCell id="${id}" value="${xmlEscape(label)}" style="${style}" edge="1" parent="1" source="${source}" target="${target}"><mxGeometry relative="1" as="geometry"/></mxCell>`);
      return id;
    },
  };
  build(api);
  const model = `<mxGraphModel dx="1800" dy="1100" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="${width}" pageHeight="${height}" math="0" shadow="0"><root>${state.cells.join("")}</root></mxGraphModel>`;
  return `<diagram id="${b64(pageName).slice(0, 22)}" name="${xmlEscape(pageName)}">${model}</diagram>`;
}

function title(api, text, width) {
  api.rect(text, 40, 24, width - 80, 46, "dark", "fontColor=#ffffff;fontSize=20;fontStyle=1;align=left;spacingLeft=18;");
}

function chain(api, labels, x, y, w, h, gap, kinds) {
  const ids = labels.map((label, i) => api.rect(label, x + i * (w + gap), y, w, h, kinds[i] || "backend"));
  ids.slice(0, -1).forEach((id, i) => api.edge(id, ids[i + 1]));
  return ids;
}

const pages = [];

pages.push(diagram(pageNames[0], 2200, 1400, (api) => {
  title(api, "REMOTE-AGENTS + Sentient OS Enterprise Architecture - Executive System Overview", 2200);
  const sentient = api.rect("Sentient OS / Sentient-Control-UI<br><b>3D Command Center</b><br>Mission Center, approvals, telemetry, workspace views", 80, 140, 300, 110, "frontend");
  const gateway = api.rect("API Gateway<br>REST + WS event ingress<br>POST /api/v1/trigger, GET /health, GET /ws/events", 470, 140, 260, 110, "backend");
  const mission = api.rect("Mission Engine<br>Mission contracts, queue adapter, store, planner CLI", 810, 140, 250, 110, "backend");
  const planner = api.rect("Planner<br>Task decomposition<br>risk hints<br>repo scope extraction", 1140, 140, 230, 110, "backend");
  const scheduler = api.rect("Scheduler<br>Local queue adapter<br>.platform_queue/next_task.json", 1450, 140, 230, 110, "runtime");
  const runtime = api.rect("Agent Runtime<br>Primary/Twin execution pair<br>model constraints", 1750, 140, 280, 110, "runtime");
  [sentient, gateway, mission, planner, scheduler, runtime].reduce((a, b) => (api.edge(a, b), b));

  const lifecycle = api.rect("Lifecycle Manager<br>Draft -> planned -> approved -> running -> validated -> archived", 790, 340, 300, 110, "governance");
  const approval = api.rect("Approval Service<br>write, network, deploy, cross-repo approvals", 1130, 340, 300, 110, "governance");
  const consensus = api.rect("Consensus Service<br>Primary proposal + Twin audit + durable decision", 1470, 340, 300, 110, "governance");
  api.edge(mission, lifecycle);
  api.edge(planner, approval);
  api.edge(runtime, consensus);
  api.edge(approval, scheduler, "approval grants");
  api.edge(consensus, runtime, "review result");

  const repoGov = api.rect("Repository Governance<br>repo_governance_router.py<br>legacy registry compatible routing", 240, 560, 290, 120, "governance");
  const mcp = api.rect("MCP Tool Router<br>tool registry, policy, repo boundary, adapter dispatch", 610, 560, 290, 120, "tools");
  const providers = api.rect("Execution Providers<br>local Ollama, isolated task runner, future worker pool", 980, 560, 290, 120, "runtime");
  const repos = api.rect("Managed Repositories<br>Full-stack, data core, 3D/neural, fallback diagnostics", 1350, 560, 290, 120, "repos");
  const memory = api.rect("Memory Service<br>mission, repo, agent, decision, incident, tool trace memory", 1720, 560, 290, 120, "memory");
  api.edge(planner, repoGov);
  api.edge(repoGov, mcp);
  api.edge(mcp, providers);
  api.edge(providers, repos);
  api.edge(repos, memory, "results + traces");
  api.edge(memory, sentient, "telemetry + memory feedback");

  const obs = api.rect("Observability<br>.logs, proof ledger, telemetry strain, forensic replay, health state", 810, 830, 360, 120, "memory");
  const queue = api.rect("Current Worker Loop<br>single local disk queue<br>processing.lock<br>max loop breaker", 1240, 830, 320, 120, "runtime");
  const future = api.rect("Future Distributed Execution<br>leased durable queue, worker pool, risk-tier concurrency", 1630, 830, 360, 120, "future");
  api.edge(runtime, obs, "audit trace");
  api.edge(scheduler, queue, "dispatch");
  api.edge(queue, obs, "status");
  api.edge(queue, future, "roadmap", "future");
}));

pages.push(diagram(pageNames[1], 2600, 1500, (api) => {
  title(api, "Agent Pipeline Architecture", 2600);
  const labels = [
    "User/Operator Request",
    "API Gateway",
    "Mission Creation",
    "Planner",
    "Repo Governance Router",
    "Agent Registry Lookup",
    "Primary Agent",
    "Tool Proposal",
    "Twin Agent Audit",
    "Approval/Consensus",
    "MCP Tool Router",
    "Repository Workspace",
    "Tests/Validation",
    "Result Envelope",
    "Memory Writeback",
    "Sentient OS Telemetry Update",
  ];
  const kinds = ["frontend", "backend", "backend", "backend", "governance", "governance", "runtime", "runtime", "runtime", "governance", "tools", "repos", "backend", "memory", "memory", "frontend"];
  const ids = labels.map((label, i) => {
    const row = i < 8 ? 0 : 1;
    const col = i < 8 ? i : 15 - i;
    return api.rect(label, 70 + col * 305, 150 + row * 310, 235, 95, kinds[i]);
  });
  for (let i = 0; i < 7; i += 1) api.edge(ids[i], ids[i + 1]);
  api.edge(ids[7], ids[8]);
  for (let i = 8; i < ids.length - 1; i += 1) api.edge(ids[i], ids[i + 1]);

  const write = api.diamond("Write Approval<br>file changes, commits, repo mutation", 660, 760, 170, 120, "risk");
  const network = api.diamond("Network Approval<br>external fetch, package install, cloud calls", 910, 760, 170, 120, "risk");
  const deploy = api.diamond("Deploy Approval<br>release, infrastructure, production side effects", 1160, 760, 170, 120, "risk");
  const cross = api.diamond("Cross-Repo Approval<br>multi-repository dependency or branch changes", 1410, 760, 170, 120, "risk");
  [write, network, deploy, cross].forEach((gate) => {
    api.edge(ids[9], gate, "risk check", "risk");
    api.edge(gate, ids[10], "allowed");
  });
  api.note("Risk gates are documentation of intended governance boundaries. This blueprint does not change runtime behavior.", 1760, 760, 430, 120, "future");
}));

pages.push(diagram(pageNames[2], 2600, 1800, (api) => {
  title(api, "Expert Roles Per Repository", 2600);
  let y = 120;
  crewFamilies.forEach((crew) => {
    api.swim(crew.family, 50, y, 2500, 360, crew.color);
    api.rect(`<b>Primary</b><br>${crew.primary}<br><br><b>Twin</b><br>${crew.twin}<br><br><b>Responsibilities</b><br>${crew.responsibilities}`, 80, y + 55, 380, 270, crew.color);
    crew.repos.forEach((repo, i) => {
      const x = 500 + (i % 4) * 500;
      const yy = y + 55 + Math.floor(i / 4) * 140;
      const status = crew.statusByRepo[repo] || "Pending";
      const note = crew.notesByRepo[repo] || "No risk note recorded";
      api.rect(`<b>${repo}</b><br>Crew: ${crew.family}<br>Primary: ${crew.primary}<br>Twin: ${crew.twin}<br>Status: ${status}<br>Risk notes: ${note}`, x, yy, 455, 120, status === "Ready" ? crew.color : status === "Fallback" ? "risk" : "future");
    });
    y += 405;
  });
  api.note("Source blend: AGENT_GUIDE_LIST.md status/risk notes plus config/agent_registry.json legacy routing classes. Requested crew families are normalized here for enterprise readability.", 50, 1710, 2450, 60, "future");
}));

pages.push(diagram(pageNames[3], 2200, 1400, (api) => {
  title(api, "Mission Engine Lifecycle", 2200);
  const states = chain(api, [
    "Draft Mission",
    "Planned",
    "Risk Classified",
    "Awaiting Approval",
    "Scheduled",
    "Running",
    "Consensus Review",
    "Validating",
    "Completed",
    "Memory Archived",
  ], 70, 160, 180, 90, 35, ["backend", "backend", "governance", "governance", "runtime", "runtime", "governance", "backend", "memory", "memory"]);
  const failures = [
    ["Twin Rejected", 250],
    ["Human Rejected", 460],
    ["Tool Failed", 670],
    ["Test Failed", 880],
    ["Lock Timeout", 1090],
    ["Max Loop Breaker", 1300],
    ["Archived to<br>.platform_queue/failed/", 1510],
  ].map(([label, x]) => api.rect(label, x, 520, 180, 90, "risk"));
  api.edge(states[6], failures[0], "audit fail", "risk");
  api.edge(states[3], failures[1], "denied", "risk");
  api.edge(states[5], failures[2], "adapter error", "risk");
  api.edge(states[7], failures[3], "validation fail", "risk");
  api.edge(states[4], failures[4], "processing.lock", "risk");
  api.edge(states[5], failures[5], "loop guard", "risk");
  failures.slice(0, 6).forEach((id) => api.edge(id, failures[6], "failure envelope", "risk"));
  api.rect("Recovery Path<br>diagnostic crew proposes low-privilege patch, records incident memory, waits for human approval before writes", 470, 830, 700, 130, "governance");
  api.rect("Telemetry Path<br>Sentient OS surfaces state, lock, failure reason, consensus notes, and artifact links", 1240, 830, 650, 130, "frontend");
}));

pages.push(diagram(pageNames[4], 2200, 1400, (api) => {
  title(api, "Consensus + Approval Flow", 2200);
  const primary = api.rect("Primary Agent<br>proposes action<br>diff/tool intent/test plan", 120, 180, 260, 110, "runtime");
  const twin = api.rect("Twin Agent<br>validates correctness, safety, repo conventions", 470, 180, 280, 110, "runtime");
  const consensus = api.rect("Consensus Service<br>records decision, refinement, disagreement", 840, 180, 300, 110, "governance");
  const risk = api.diamond("Risk Tier Check<br>low / medium / high / blocked", 1240, 170, 190, 130, "governance");
  const human = api.rect("Human Approval<br>required for writes, network, deploy, cross-repo", 1530, 180, 300, 110, "governance");
  const allowed = api.rect("Execution Allowed<br>durable approval record + policy grant", 1260, 480, 280, 110, "backend");
  const blocked = api.rect("Execution Blocked<br>safe no-op, explanation, audit ledger", 1610, 480, 280, 110, "risk");
  api.edge(primary, twin);
  api.edge(twin, consensus);
  api.edge(consensus, risk);
  api.edge(risk, human, "approval required", "risk");
  api.edge(risk, allowed, "pre-approved low risk");
  api.edge(human, allowed, "approved");
  api.edge(human, blocked, "rejected", "risk");
  const reject = api.rect("Twin Rejection<br>syntax bug, schema drift, leak, unsafe path, non-finite math", 470, 480, 300, 110, "risk");
  const refine = api.rect("Successful Refinement<br>Primary revises plan, Twin re-audits, consensus updates metrics", 840, 480, 300, 110, "governance");
  api.edge(twin, reject, "reject", "risk");
  api.edge(reject, refine, "revise");
  api.edge(refine, consensus, "new decision");
  api.rect("Consensus Metrics<br>approval rate, rejection reasons, agent disagreement, risk tier distribution", 350, 760, 420, 120, "memory");
  api.rect("Durable Approval Record<br>who, when, scope, command/tool, risk class, expiry", 840, 760, 420, 120, "memory");
  api.rect("Audit Ledger<br>decision chain, tool intent, normalized result, memory record id", 1330, 760, 420, 120, "memory");
}));

pages.push(diagram(pageNames[5], 2300, 1500, (api) => {
  title(api, "MCP Tool Router Internals", 2300);
  const ids = chain(api, [
    "Agent Runtime",
    "Tool Intent",
    "Tool Registry",
    "Policy Check",
    "Repo Boundary Check",
    "Path Traversal Guard",
    "Approval Requirement Check",
    "Tool Adapter",
    "Tool Execution",
    "Normalized Result",
    "Audit Trace",
  ], 70, 150, 180, 90, 25, ["runtime", "runtime", "tools", "governance", "governance", "risk", "risk", "tools", "tools", "memory", "memory"]);
  const tools = [
    "workspace_file_router",
    "execute_isolated_task",
    "network_data_fetch",
    "graphics_validate_transform_math",
    "graphics_parse_matrix4",
    "trace_asset_compilation",
  ];
  tools.forEach((tool, i) => {
    const id = api.rect(tool, 220 + i * 330, 520, 285, 80, i < 2 ? "tools" : i === 2 ? "risk" : "runtime");
    api.edge(ids[7], id, "adapter route");
    api.edge(id, ids[8], "execute");
  });
  api.rect("Router Security Envelope<br>tool requests are normalized into explicit intent, then constrained by repo boundary, path guard, policy, and approval requirements before execution.", 340, 800, 760, 130, "governance");
  api.rect("Result Contract<br>status, stdout/stderr or data, files touched, risk events, telemetry hooks, memory writeback references", 1200, 800, 720, 130, "memory");
}));

pages.push(diagram(pageNames[6], 2200, 1500, (api) => {
  title(api, "Semantic Memory Graph", 2200);
  const center = api.rect("Semantic Memory Service<br>append-only records + graph links + retrieval context", 910, 180, 360, 120, "memory");
  const domains = [
    ["Mission Memory", 180, 150],
    ["Repository Memory", 520, 150],
    ["Agent Memory", 1460, 150],
    ["Decision Memory", 180, 520],
    ["Incident Memory", 520, 520],
    ["Tool Trace Memory", 1460, 520],
    ["Architecture Memory", 180, 890],
    ["Performance Memory", 1460, 890],
  ].map(([label, x, y]) => api.rect(label, x, y, 260, 100, "memory"));
  domains.forEach((id) => api.edge(id, center, "indexes"));
  const mission = api.rect("Mission", 770, 520, 150, 70, "backend");
  const task = api.rect("Task", 970, 520, 150, 70, "backend");
  const agent = api.rect("Agent", 1170, 520, 150, 70, "runtime");
  const tool = api.rect("Tool", 770, 690, 150, 70, "tools");
  const repo = api.rect("Repository", 970, 690, 150, 70, "repos");
  const decision = api.rect("Decision", 1170, 690, 150, 70, "governance");
  const incident = api.rect("Incident", 770, 860, 150, 70, "risk");
  const fix = api.rect("Fix", 970, 860, 150, 70, "backend");
  const consensus = api.rect("Consensus", 1170, 860, 150, 70, "governance");
  const record = api.rect("Memory Record", 1370, 860, 170, 70, "memory");
  api.edge(mission, task, "Mission -> Tasks");
  api.edge(task, agent, "Task -> Agents");
  api.edge(agent, tool, "Agent -> Tools");
  api.edge(tool, repo, "Tool -> Repository");
  api.edge(repo, decision, "Repository -> Decisions");
  api.edge(incident, fix, "Incident -> Fix");
  api.edge(consensus, record, "Consensus -> Memory Record");
  api.edge(record, center);
}));

pages.push(diagram(pageNames[7], 2300, 1500, (api) => {
  title(api, "Distributed Execution Roadmap", 2300);
  api.swim("Current Execution", 70, 130, 980, 520, "runtime");
  const current = chain(api, [
    "Single local disk queue",
    ".platform_queue/next_task.json",
    "processing.lock",
    "local Ollama",
    "single worker loop",
  ], 120, 240, 170, 90, 25, ["runtime", "runtime", "governance", "runtime", "runtime"]);
  api.edge(current[4], current[0], "poll next task");
  api.swim("Future Distributed Execution", 1140, 130, 1050, 520, "future");
  const futureLabels = [
    "durable queue",
    "leased tasks",
    "worker pool",
    "Ollama worker",
    "Codex worker",
    "Claude Code worker",
    "MCP worker",
    "browser/runtime worker",
    "future cloud worker",
  ];
  futureLabels.forEach((label, i) => {
    const x = 1190 + (i % 3) * 320;
    const y = 235 + Math.floor(i / 3) * 125;
    const id = api.rect(label, x, y, 260, 80, "future");
    if (i > 0 && i < 3) api.edge(String(Number(id) - 1), id, "", "future");
  });
  api.swim("Concurrency Controls", 270, 780, 1760, 360, "governance");
  ["by repository", "by mission", "by branch", "by hardware budget", "by risk tier"].forEach((label, i) => {
    api.diamond(label, 390 + i * 310, 890, 170, 120, i === 4 ? "risk" : "governance");
  });
  api.note("Roadmap items are intentionally separate from current queue behavior. This diagram does not implement durable queues, leases, or multi-worker execution.", 420, 1210, 1450, 90, "future");
}));

pages.push(diagram(pageNames[8], 2200, 1500, (api) => {
  title(api, "Sentient OS Integration", 2200);
  api.swim("Sentient OS Frontend Modules", 70, 130, 860, 760, "frontend");
  const modules = [
    "Mission Center",
    "Agent Center",
    "Repository Center",
    "Approval Center",
    "Memory Graph",
    "Telemetry Center",
    "Workspace Explorer",
    "3D Operations Room",
  ].map((label, i) => api.rect(label, 130 + (i % 2) * 370, 230 + Math.floor(i / 2) * 145, 300, 90, "frontend"));
  api.swim("REMOTE-AGENTS APIs", 1120, 130, 860, 760, "backend");
  const apis = [
    "POST /api/v1/trigger",
    "GET /health",
    "GET /ws/events",
    "future mission APIs",
    "future approval APIs",
    "future memory APIs",
    "future telemetry APIs",
  ].map((label, i) => api.rect(label, 1180 + (i % 2) * 370, 230 + Math.floor(i / 2) * 145, 300, 90, i < 3 ? "backend" : "future"));
  modules.forEach((m, i) => api.edge(m, apis[Math.min(i, apis.length - 1)], i < 3 ? "current/foundation" : "roadmap", i < 3 ? "normal" : "future"));
  const events = api.rect("Event Stream<br>mission state, agent status, consensus result, approval requirement, logs, telemetry", 650, 1020, 850, 120, "memory");
  api.edge(apis[2], events, "WebSocket events");
  api.edge(events, modules[5], "live update");
  api.edge(events, modules[7], "3D room state");
}));

pages.push(diagram(pageNames[9], 2300, 1500, (api) => {
  title(api, "Registry Architecture", 2300);
  api.swim("Canonical Registries", 70, 140, 720, 620, "governance");
  const regs = [
    "config/registries/repositories.json",
    "config/registries/agents.json",
    "config/registries/tools.json",
    "config/registries/models.json",
    "config/registries/policies.json",
  ].map((label, i) => api.rect(label, 140, 230 + i * 95, 560, 70, "governance"));
  api.swim("Legacy Compatibility", 880, 140, 600, 620, "runtime");
  const legacy = api.rect("legacy config/agent_registry.json", 960, 260, 430, 90, "runtime");
  const router = api.rect("repo_governance_router.py", 960, 430, 430, 90, "governance");
  const routing = api.rect("runtime-compatible routing", 960, 600, 430, 90, "backend");
  api.edge(legacy, router);
  api.edge(router, routing);
  api.swim("Future Consumers", 1570, 140, 650, 620, "future");
  const consumers = [
    "Mission Planner",
    "Lifecycle Manager",
    "Capability Registry",
    "Tool Router",
    "Sentient OS UI",
  ].map((label, i) => api.rect(label, 1650, 230 + i * 95, 470, 70, "future"));
  regs.forEach((reg, i) => api.edge(reg, consumers[i] || consumers[0], "canonical", "future"));
  api.edge(routing, consumers[0], "compat bridge", "future");
  api.edge(consumers[0], consumers[1], "", "future");
  api.edge(consumers[1], consumers[2], "", "future");
  api.edge(consumers[2], consumers[3], "", "future");
  api.edge(consumers[3], consumers[4], "", "future");
  api.note("Current repository includes canonical registry files and legacy config/agent_registry.json. The board shows the intended evolution without changing router or queue code.", 320, 900, 1600, 110, "future");
}));

const mxfile = `<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="2026-05-29T00:00:00.000Z" agent="Codex" version="24.7.17" type="device">
${pages.join("\n")}
</mxfile>
`;

fs.writeFileSync(outputPath, mxfile, "utf8");

const xml = fs.readFileSync(outputPath, "utf8");
const diagramCount = (xml.match(/<diagram /g) || []).length;
if (diagramCount !== pageNames.length) {
  throw new Error(`Expected ${pageNames.length} pages but found ${diagramCount}`);
}
for (const name of pageNames) {
  if (!xml.includes(`name="${xmlEscape(name)}"`)) {
    throw new Error(`Missing page: ${name}`);
  }
}

console.log(`Generated ${outputPath}`);
console.log(`Pages: ${diagramCount}`);
