ROLE: CODEBASE ARCHAEOLOGIST & EXTRACTOR 

You are an isolated extraction agent. Your assignment is to thoroughly audit the current standalone repository file structure, configuration manifests, and documentation to determine its structural signature. 

EXTRACTION CRITERIA 

Analyze the codebase files and extract data against these target indicators: 

Primary dependencies (e.g., package.json, requirements.txt, Cargo.toml). 

Infrastructure files (e.g., Dockerfiles, .env.example, workflows/). 

Core domain patterns (e.g., views, schemas, controllers, engine assets). 

OUTPUT JSON SCHEMA Requirement 

Generate an explicit layout summarizing the metadata needed for agent configuration. Use this exact formatting: { "repository_name": "string", "detected_class": "#Retail | #Web tool | #Game tool | #Orchestrator | #Unknown", "structural_health_indicators": ["list", "of", "findings"], "recommended_agent_assignment": { "primary_class": "string", "twin_context_class": "string" }, "immediate_priority_actions": ["action_1", "action_2"] } 

Execute evaluation now. Input code context files below: 

 

 

{ 

  "project": "Mucho3D", 

  "class": "monorepo", 

  "git_ready": true, 

  "agent_assignment_class": "repo-agent-contract:monorepo-root", 

  "immediate_governance_step": "Initialize at git repo root (no cloning needed); run baseline diagnostics (lint/build/tests) and confirm .env.local contains no secrets (it appears to be dev-only config)." 

} 

 

 

{ "repository_name": "ConceptShop", "detected_class": "#Retail", "structural_health_indicators": [ "Single-package Node.js frontend (npm) with package.json + package-lock.json at repo root", "Vite + React 18 SPA (vite.config.js, index.html, src/main.jsx, src/App.jsx) using react-router-dom", "TailwindCSS + PostCSS configured (tailwind.config.js, postcss.config.js, src/index.css)", "Firebase-centric data layer: Auth/Firestore/Storage/Analytics (src/firebase/) with domain collections like products, orders, groupOrders, shipments", "Client-side AWS SDK usage for S3/Lambda (src/aws/config.js) configured via VITE_ env variables", "Environment template present (.env.example) including Firebase + AWS + optional shipping carrier keys", "Domain/UI structure is conventional: src/pages/* (Dashboard/Orders/Products/Stakeholders/Shipping/Forecasting/etc), src/components/, src/context/, src/services/", "No README/License/Makefile detected at repo root (discoverability/onboarding gap)", "No Dockerfile / docker-compose / GitHub Actions workflows detected (infra/CI gap)", "ESLint is wired in package.json scripts but no ESLint config file detected (.eslintrc / eslint.config.), so npm run lint likely fails", "No test runner config detected (no Jest/Vitest/Cypress config found)" ], "recommended_agent_assignment": { "primary_class": "React/Vite frontend agent (React Router, Tailwind, SPA architecture)", "twin_context_class": "Firebase + cloud integrations agent (Firestore modeling, Auth flows, Storage, AWS/Lambda boundary)" }, "immediate_priority_actions": [ "Add a minimal README.md covering setup (npm install), env requirements (.env.example), and scripts (npm run dev|build|preview|lint)", "Add a valid ESLint config (eslint.config.js or .eslintrc.) consistent with React + Vite, or remove the lint script if intentionally unused", "Add baseline CI workflow to run npm ci, npm run lint, and npm run build on PRs", "Re-evaluate client-side AWS credential usage (avoid VITE_AWS_SECRET_ACCESS_KEY in the browser; prefer server-side/Lambda + federated auth)" ] } 

 

 

{ 

  "project": "portfolio", 

  "class": "node-vite-react-app", 

  "git_ready": true, 

  "agent_assignment_class": "repo-agent-contract/single-repo-app (scope: this repository at /home/runner/work/PORTFOLIO/PORTFOLIO)", 

  "immediate_governance_step": "No repo setup/isolation required: .git present, origin remote configured, and working tree is clean (no uncommitted files). Proceed with normal agent initialization; only trigger isolation/diagnostics if env/secret files (e.g., .env.local) appear in future changes." 

} 

 

 

{ 

  "repository_name": "Dealinstinct", 

  "detected_class": "#Web tool", 

  "structural_health_indicators": [ 

    "Next.js 14 App Router project with Plasmic loader integration (@plasmicapp/loader-nextjs, @plasmicapp/host).", 

    "Primary dependency manifest: package.json + package-lock.json (npm-based); no Python/Rust/Go/etc manifests detected.", 

    "Core structure: app/ (App Router + catch-all route app/[...slug]/page.jsx), components/ (Plasmic loader init), lib/ (Plasmic fetch helper), scripts/ (Plasmic setup scripts).", 

    "No infra/ops scaffolding detected at repo root (no Dockerfile, docker-compose, .env.example, Terraform, or .github/workflows).", 

    "Secret risk: scripts/setup-plasmic.sh contains a hardcoded Plasmic token string (should be removed/revoked and replaced with env-based config).", 

    "Next.js routing risk: both app/layout.js and app/layout.jsx exist; this can cause ambiguity/conflicts for the App Router layout entrypoint.", 

    "RSC boundary risk: lib/plasmic-server.js imports components/plasmic-init.js which is marked 'use client'; this pattern commonly breaks server imports in Next.js.", 

    "scripts/setup-plasmic.sh references many @/components/* files that are not present in this repo, suggesting the script is stale or copied from another project." 

  ], 

  "recommended_agent_assignment": { 

    "primary_class": "Next.js App Router + Plasmic integration", 

    "twin_context_class": "Security/DevOps hygiene (secrets, env, CI scaffolding)" 

  }, 

  "immediate_priority_actions": [ 

    "Remove/revoke the hardcoded Plasmic token in scripts/setup-plasmic.sh and switch to environment-variable configuration.", 

    "Add minimal onboarding docs and config scaffolding (README + .env.example including NEXT_PUBLIC_PLASMIC_API_TOKEN, and basic run steps).", 

    "Normalize the App Router entrypoints (choose a single app/layout.*) and ensure Plasmic loader usage respects Next.js server/client boundaries." 

  ] 

} 

 

 

{ 

  "repository_name": "Powerframe", 

  "detected_class": "#Orchestrator", 

  "structural_health_indicators": [ 

    "Single-package React 18 + Vite + Tailwind SPA (ESM) with minimal scripts: dev/build/preview", 

    "Acts as an ecosystem Hub/launcher: app registry in src/config/apps.js points to external app URLs and repos", 

    "Vercel deployment routing present (vercel.json SPA rewrites) and Vite dev proxy routes /api to localhost:5000", 

    "Serverless-style endpoints present under api/ (health + auth/) using jsonwebtoken + bcryptjs", 

    "Auth implementation is dev-grade: in-memory user store per function file and a hardcoded JWT secret fallback string", 

    "Documentation inconsistency: architecture.md/description.md describe a much larger dashboard structure not present in src/", 

    "Missing standard repo entry docs (no README/CONTRIBUTING/LICENSE found at root) and no .github/workflows CI detected", 

    "Naming drift: package.json name is bms-dashboard while repo and docs describe Powerframe Hub" 

  ], 

  "recommended_agent_assignment": { 

    "primary_class": "frontend_spa_orchestrator_agent", 

    "twin_context_class": "serverless_auth_api_agent" 

  }, 

  "immediate_priority_actions": [ 

    "Reconcile/replace architecture.md and description.md (and add a root README) so docs match the actual Hub/launcher codebase", 

    "Harden api/auth/: require JWT_SECRET via environment (add .env.example) and replace in-memory user store with a real identity/session strategy or remove the endpoints if Firebase-only auth is intended", 

    "Add baseline CI workflow (install + build) to prevent regressions and make structural signature explicit" 

  ] 

} 

 

 

{ "repository_name": "Powerframe-CRM", "detected_class": "#Web tool", "structural_health_indicators": [ "Primary runtime is a single Vite + React app (package.json at repo root) with npm run dev/build/preview scripts.", "Primary dependencies indicate a web dashboard UI: react, react-router-dom, tailwindcss, framer-motion, firebase.", "No backend service code detected; persistence/auth appear to be Firebase Auth + Firestore via src/firebase/.", "Environment-dependent configuration is required (import.meta.env.VITE_FIREBASE_, VITE_GMS_OPERATOR_ENDPOINT), but no .env.example/.env.sample file exists.", "No CI workflows found (.github/workflows absent) and no container/infra manifests detected (no Dockerfile/compose/vercel/netlify/fly/etc.).", "Documentation exists (description.md, subscription.md) and describes a GMS/telemetry control-plane concept, but referenced toolchain versions don’t match the actual package.json versions (e.g., docs mention newer React/Vite/Tailwind than installed).", "Repository contains parallel/duplicated module structures (src/layout/primitives/* and apps/crm/src/layout/primitives/, plus multiple design-system/layoutTokens.js locations), suggesting an incomplete monorepo split or staged migration.", "Auth flow includes a local-dev session fallback in src/context/AuthContext.jsx, implying production SSO integration is not yet wired." ], "recommended_agent_assignment": { "primary_class": "Frontend React/Vite dashboard agent", "twin_context_class": "Firebase + GMS telemetry integration agent" }, "immediate_priority_actions": [ "Add a root README.md with install/run steps and required VITE_FIREBASE_/VITE_GMS_OPERATOR_ENDPOINT environment variables.", "Add a root .env.example that enumerates required VITE_* keys (no secrets) for local bootstrapping.", "Decide whether apps/crm/ is a real sub-package or a scratch area; either wire it into the build (with its own manifest) or remove/relocate to avoid drift and duplicated primitives.", "Add a minimal GitHub Actions workflow to run npm ci + npm run build on PRs to establish baseline structural health." ] } 

 

 

{ "repository_name": "powerframe-gms", "detected_class": "#Web tool", "structural_health_indicators": [ "Vite + React SPA with React Router routes under /gms/* (see src/App.jsx).", "Serverless API endpoints present under api/* (Vercel-style handlers) including JWT auth stubs in api/auth/.", "Deployment routing configured for Vercel rewrites in vercel.json (SPA fallback + /api/ passthrough).", "Auth is split between Firebase client auth (src/context/AuthContext.jsx, src/firebase/) and separate serverless JWT auth stubs (api/auth/), with dev/localStorage session fallbacks in src/App.jsx.", "Firebase config is placeholder-only (src/firebase/config.js contains REPLACE_ME_* values).", "JWT secret has an insecure dev fallback (process.env.JWT_SECRET || "powerframe-dev-secret-change-in-production" in api/auth/).", "UI shell and domain structure is page/layout/context oriented: src/layouts/, src/pages/, src/context/, src/components/.", "Layout design tokens are generated via apps/gms/scripts/sync-layout-tokens.js and consumed by global CSS imports in src/main.jsx.", "Bridge/Unity integration is currently documentation + fixtures only (docs/bridge/, apps/gms-hub/lab-json-bridge.config.json), not a runtime integration.", "No CI workflow files detected under .github/workflows/ and no container manifests (no Dockerfile / compose) at repo root." ], "recommended_agent_assignment": { "primary_class": "Vite/React Web App Agent (routing, UI shell, client state)", "twin_context_class": "Unity Bridge/Integration Agent (event contracts, postMessage/bridge lab, serverless API boundary)" }, "immediate_priority_actions": [ "Add a root README.md describing dev/build (npm run dev, npm run build), deploy (Vercel), and required env/config (Firebase + JWT secret).", "Introduce a .env.example (or equivalent) for required runtime secrets/config, and remove reliance on hardcoded JWT fallback for any non-local environment.", "Decide on a single source of truth for authentication (Firebase-only vs serverless JWT API) and align client/session handling accordingly.", "Audit and align route namespaces (/gms vs any legacy /bms paths referenced in layout/navigation) to avoid broken navigation after deploy." ] } 

 

 

{ 

  "repository_name": "Powerframe-TPR", 

  "detected_class": "#Web tool", 

  "structural_health_indicators": [ 

    "Node/Vite-based monorepo: root vite.config.mjs builds apps/time-planner/index.html to dist/.", 

    "Primary app lives in apps/time-planner/ (static HTML/JS/CSS) with a gradual TSX/CSS-modules “layout bridge” in apps/time-planner/src/.", 

    "Data-generation pipeline is centralized in root scripts/*.cjs, emitting JSON into both data/ and apps/time-planner/data/.", 

    "Repo-level configuration is explicit and centralized in config/app.config.json and config/prompt-logic.config.json.", 

    "Deployment is Vercel-oriented (vercel.json at root and app/content scopes). No Docker/terraform/workflow automation detected.", 

    "Validation guardrails exist (npm run validate, npm run lint:layout) and docs describe the intended architecture and safety rules.", 

    "Potential drift risk: multiple package.json/package-lock.json (root + apps/time-planner/) and mismatched Vite versions (root vs app).", 

    "Core domain modules are present in apps/time-planner/js/*engine.js (state/sync/AI scaffolding), apps/time-planner/js/notes-cloud-sync.js, and view modules under apps/time-planner/js/views/." 

  ], 

  "recommended_agent_assignment": { 

    "primary_class": "Front-end web app maintainer (static dashboard + Vite build/deploy)", 

    "twin_context_class": "Node data-pipeline & sync/orchestration maintainer (generators + Firebase sync worker)" 

  }, 

  "immediate_priority_actions": [ 

    "Establish a clean baseline by running the existing repo checks: npm ci && npm run validate && npm run lint:layout && npm run build.", 

    "Reduce dependency drift by deciding whether apps/time-planner/ should keep its own package.json/lockfile or defer to the root, then align Vite versions accordingly.", 

    "Add lightweight CI (at least validate + build) if automated verification is desired for future changes." 

  ] 

} 

 

 

{ 

  "repository_name": "TheRocketTree-App", 

  "detected_class": "#Orchestrator", 

  "structural_health_indicators": [ 

    "TypeScript monorepo using pnpm workspaces (apps/, packages/) + Turborepo task graph (build/dev/lint/test/typecheck).", 

    "Primary runtime apps are Next.js 15 + React 19 (e.g., apps/trt, apps/powerstarter, apps/powerframe) using the /app router layout.", 

    "Shared platform packages include contracts (Zod schemas), logic (semantic engine), db (Prisma client/schema), core (Firebase client/admin), ui (React component exports).", 

    "Prisma generation is explicitly wired into Turbo (db:generate depends on DATABASE_URL) and CI provides a SQLite fallback (DATABASE_URL=file:./dev.db).", 

    "A build-time “bridge-chain” contract exists: apps/gms generates canonical layout artifacts (layout-tokens.css + layout-matrix.json) and scripts/ci-bridge-check.js validates consumers (crm/wms/tpr/gms-hub).", 

    "Unity integration exists via packages/apps: @trt/unity-adapter (TS bridge + Zod validation) and a Unity project subtree at apps/unity-adapter/unity/Assets/.", 

    "Infrastructure is GitHub Actions CI + Vercel deployment workflows; no Dockerfile/docker-compose detected; env templates are provided via multiple .env.example files.", 

    "Version pinning is mostly clear (root packageManager pnpm@9.15.9, engines node 20.x) but CI workflow sets PNPM_VERSION=9.4.0, which may drift from the repo’s declared pnpm version." 

  ], 

  "recommended_agent_assignment": { 

    "primary_class": "TypeScript Monorepo Build/Platform Agent (pnpm + Turborepo + Next.js + Prisma)", 

    "twin_context_class": "Bridge-Chain & Unity Adapter Agent (GMS layout artifacts + JSON/CSS contract validation)" 

  }, 

  "immediate_priority_actions": [ 

    "Standardize tooling to Node 20 and the repo-declared pnpm version (pnpm@9.15.9 via Corepack) to avoid CI/local drift.", 

    "Treat apps/gms compiled layout artifacts as the canonical layout contract; regenerate via apps/gms scripts before downstream layout work.", 

    "When running build/typecheck/CI tasks locally, always provide DATABASE_URL (e.g., file:./dev.db) so Prisma client generation succeeds.", 

    "Use pnpm ci:bridge-chain as the first-line contract check for any changes affecting layout tokens, bridge outputs, or consumer configs.", 

    "Confirm which apps/* folders are “real” runnable apps vs. contract-only consumers (crm/wms/tpr/gms-hub) and keep agent routing/tasking aligned to that split." 

  ] 

} 

 

 

{ 

  "repository_name": "WOMmedia", 

  "detected_class": "#Web tool", 

  "structural_health_indicators": [ 

    "Next.js 15 App Router structure under /app with routes for /, /projects, /studio, /journal, /contact.", 

    "Primary dependencies: next, react/react-dom, framer-motion, lucide-react (see package.json).", 

    "Tailwind CSS v4 is configured via app/globals.css using @import \"tailwindcss\" and @theme tokens (no tailwind.config.js present).", 

    "UI is componentized under /components, with animation helpers under /components/motion.", 

    "Site content is hardcoded in /lib/site-data.js (no backend/CMS/data layer detected).", 

    "Contact page is frontend-only (no API route or submission wiring detected).", 

    "No infrastructure files detected: no Dockerfile, no docker-compose, no .env.example.", 

    "No GitHub Actions workflows detected under .github/workflows.", 

    "No README/CONTRIBUTING/LICENSE files detected at the repo root." 

  ], 

  "recommended_agent_assignment": { 

    "primary_class": "Next.js (React) frontend engineer", 

    "twin_context_class": "UI/UX + motion (Tailwind + Framer Motion) specialist" 

  }, 

  "immediate_priority_actions": [ 

    "Add a README documenting local setup (npm install/npm run dev), build/lint scripts, and deployment expectations.", 

    "Add a CI workflow to run npm ci, npm run lint, and npm run build on pull requests." 

  ] 

} 

 

 

 

{ 

  "repository_name": "TheRocketTree-Web", 

  "detected_class": "#Web tool", 

  "structural_health_indicators": [ 

    "Frontend is a Vite + React 18 single-page app (ESM) with TailwindCSS/PostCSS", 

    "Dependency manifests present: package.json + package-lock.json", 

    "Source layout is clean and componentized: src/pages (composition), src/components (sections), src/components/ui (primitives), src/data/siteContent.js (copy/content)", 

    "Deployment target appears to be static hosting (Vite build outputs dist); no runtime services or env vars indicated", 

    "No CI/workflow automation detected (.github/workflows absent) and no tests/lint configs detected in repo root", 

    "index.html is a thin mount-point that loads /src/main.jsx; uses external CDNs (Google Fonts, Font Awesome)" 

  ], 

  "recommended_agent_assignment": { 

    "primary_class": "Frontend agent (React/Vite/Tailwind UI surface)", 

    "twin_context_class": "Docs/governance agent (markdown governance + orchestration logs)" 

  }, 

  "immediate_priority_actions": [ 

    "Add CI build workflow to run npm ci + npm run build on PRs", 

    "Add baseline lint/format tooling (or document formatting conventions) to prevent style drift across src/components" 

  ] 

} 

 

 

 

{ 

  "repository_name": "PowerStarter", 

  "detected_class": "#Orchestrator", 

  "structural_health_indicators": [ 

    "pnpm monorepo workspace structure controlled via root pnpm-workspace.yaml and lockfile", 

    "Three separate React 18/19 + Vite 5 frontend applications housed within the /apps directory: @trt/powerstarter, @trt/gms-hub, and @trt/webframe-cms", 

    "Two shared modules located within the /packages directory: @trt/state-multiplexer (state synchronization framework) and @trt/utils (shared helpers)", 

    "Infrastructure orchestration configuration exists via root docker-compose.yml employing a Caddy reverse-proxy (Caddyfile)", 

    "Structural regression detected: docker-compose configuration references an absolute directory path ./apps/the-rocket-tree-app which does not exist in the current tree", 

    "Incomplete build containers: Dockerfile contexts are omitted from the active application subdirectories preventing clean compose up operations", 

    "No continuous integration pipeline configuration (.github/workflows) or centralized multi-package test harness provided" 

  ], 

  "recommended_agent_assignment": { 

    "primary_class": "TypeScript/React Monorepo Build Platform Engineer", 

    "twin_context_class": "DevOps & Caddy Infrastructure Orchestration Specialist" 

  }, 

  "immediate_priority_actions": [ 

    "Reconcile the root docker-compose.yml configuration to map directly to existing apps (@trt/powerstarter, @trt/gms-hub, @trt/webframe-cms) and prune references to the non-existent the-rocket-tree-app directory", 

    "Generate localized multi-stage Dockerfiles within each active app directory targeting static asset production to allow the root Caddy proxy to mount target volumes successfully", 

    "Establish standard workspace-level pnpm testing pipelines and hook up continuous integration templates to execute multi-package verification checks on incoming pull requests" 

  ] 

} 

 

 

{ "repository_name": "Powerframe-WMS", "detected_class": "#Web tool", "structural_health_indicators": [ "Single Node.js/Vite/React app at repo root (package.json) with UI code under apps/wms/src/", "Deterministic data pipeline (scripts/.cjs) generates and validates derived models in data/.json consumed by the frontend UI", "Bridge and contract surface present as a JSON schema configuration (apps/wms/lab-json-bridge.config.json) alongside an ingest validator system (apps/wms/src/services/unityIngest.js)", "No CI/CD automation pipelines configured (no .github/workflows/* files detected)", "No containerization or environment scaffolding provided (no Dockerfile, docker-compose, or .env.example manifests found)", "Documentation drift risk: description.md files specify a larger component/module layout tree than what is currently implemented under apps/wms/src/", "No diagnostic layer found: complete absence of test suites, test configurations, or automated testing harnesses inside package.json scripts" ], "recommended_agent_assignment": { "primary_class": "React/Vite Frontend + Node (CJS) Data Generation Pipeline Engineer", "twin_context_class": "JSON-Schema Contract & Telemetry Validation Specialist (Unity Bridge Boundary)" }, "immediate_priority_actions": [ "Inject a GitHub Actions CI workflow to run npm clean-install, npm run validate, and npm run build on incoming Pull Requests", "Introduce a standardized top-level repository README containing local developer setup steps (npm install, npm run dev, npm run build) along with a structural map of the data generation/validation pipeline", "Reconcile existing architectural specification files with the concrete apps/wms/src/ filesystem layout by either pruning non-existent feature scopes or flagging them as future development roadmap milestones" ] } 

 

 

{ 

  "repository_name": "TheRocketTreeUnity", 

  "detected_class": "#Game tool", 

  "structural_health_indicators": [ 

    "Unity project root layout verified: standard Assets/, Packages/, and ProjectSettings/ directories are present.", 

    "Unity Editor runtime version is pinned explicitly to 6000.3.2f1 within ProjectSettings/ProjectVersion.txt.", 

    "Primary ecosystems are managed via Unity packages inside Packages/manifest.json (including com.unity.test-framework, com.unity.timeline, com.unity.ugui, and com.unity.nuget.newtonsoft-json).", 

    "A co-located Firebase Cloud Functions v2 TypeScript module exists at functions/src/index.ts, but the functions/ directory completely lacks its corresponding package.json and tsconfig.json manifests, rendering it non-buildable as-is.", 

    "No CI/CD automation pipelines configured (the entire .github/workflows directory is absent from the repository structure).", 

    "Bridge adapter designs and contract configurations are restricted to documentation-only blueprints under docs/bridge/, with no current runtime execution paths found.", 

    "The root mcp.json file defines an Model Context Protocol (MCP) server path pointing to Packages/com.unity.mcp.bridge/Server/dist/index.js, but no such directory exists in-repo. Concurrently, Packages/manifest.json targets this package to an invalid placeholder URL (https://github.com).", 

    "Core logic and domain engines are centralized cleanly under Assets/Scripts/GameMode and Assets/Scripts/TreeGameMode, managing state machines and tree runtime controllers." 

  ], 

  "recommended_agent_assignment": { 

    "primary_class": "Unity/C# Gameplay Systems Agent (Tree Game Mode State Engine & Asset Pipelines)", 

    "twin_context_class": "Firebase Cloud Functions / TypeScript Backend Agent (Firestore Contracts & Synchronization Endpoints)" 

  }, 

  "immediate_priority_actions": [ 

    "Resolve the TypeScript infrastructure debt by introducing missing package.json and tsconfig.json manifests into the functions/ workspace to make its compilation path deterministic.", 

    "Reconcile the broken Model Context Protocol (MCP) bridge architecture by either pruning the missing local paths from mcp.json or fixing the invalid git endpoint reference inside Packages/manifest.json.", 

    "Deploy a GitHub Actions workflow pipeline to automatically execute Unity EditMode/PlayMode testing passes alongside basic TypeScript syntax checking tasks on future codebase revisions." 

  ] 

} 

 

 

{ 

  "repository_name": "Sapient-KB", 

  "detected_class": "#Web tool", 

  "structural_health_indicators": [ 

    "pnpm multi-package monorepo workspace detected with unified configurations at the root level.", 

    "Web frontend is powered by Next.js and React, explicitly tracking version 14.2.35 within apps/web/package.json.", 

    "Architecture documentation (ADR) references an upgrade target of Next.js 15.5.15, creating an active version mismatch against the actual implemented package manifests.", 

    "Integrates complex 3D rendering systems using @react-three/fiber and @react-three/drei inside components like TreeCanvas.tsx.", 

    "Contains unmanaged micro-packages and directories (e.g., apps/powerframe-gms, apps/cli-tools) that lack isolated package.json manifests and build pipelines.", 

    "A Vercel deployment infrastructure file (vercel.json) is present, indicating a serverless cloud-hosting target.", 

    "Testing framework uses native node:test runners, but the monorepo contains absolutely no CI/CD pipeline automation (.github/workflows is absent).", 

    "The root pnpm workspace execution script depends on workspace-wide builds, but individual packages completely lack 'build' commands in their local manifests, causing pipeline breaks." 

  ], 

  "recommended_agent_assignment": { 

    "primary_class": "Next.js 14/15 & React-Three-Fiber Web Tooling Engineer", 

    "twin_context_class": "Vercel Serverless Architecture & Monorepo Build Pipeline Specialist" 

  }, 

  "immediate_priority_actions": [ 

    "Reconcile the package version mismatch by executing the upgrade from Next.js 14.2.35 to 15.5.15 as specified by the ADR blueprints.", 

    "Establish local package.json manifests and individual 'build' script parameters for apps/powerframe-gms and apps/cli-tools to prevent workspace-wide compilation crashes.", 

    "Inject a .github/workflows/ci.yml configuration matrix to automatically run pnpm lint, node:test suites, and Next.js verification builds on all active PRs." 

  ] 

} 

 

 

{ 

  "repository_name": "Bikerinstinct", 

  "detected_class": "#Web tool", 

  "structural_health_indicators": [ 

    "Next.js 14 (App Router) + React 18 project scaffolded explicitly for Plasmic visual CMS integration (@plasmicapp/loader-nextjs, @plasmicapp/host).", 

    "No README, LICENSE, or documentation detected at the repository root, leaving deployment intent and onboarding guidelines completely undefined.", 

    "No CI/CD workflows, Docker configurations, or environment templates detected, creating a lack of local or cloud deployment validation pipelines.", 

    "High security risk: plasmic.json contains a hardcoded, committed projectApiToken field that must be extracted into a runtime secret.", 

    "Next.js routing ambiguity: both app/layout.js and app/layout.jsx exist in the same tree; Next.js will prefer the .js variant, bypassing the PlasmicRootProvider wrapper inside the .jsx layout.", 

    "Invalid component implementation: app/page.jsx invokes a client component directly as a standard function call (Page({ params: {} })) instead of rendering it as valid JSX, which will cause runtime/build failures.", 

    "Broken environment configuration: contains a machine-local absolute symlink components/external pointing to an absolute host path (/home/max/Powerframe/src/components), which instantly fails compilation on clean checkouts.", 

    "Core domain pattern relies on a dynamic catch-all route (app/[...slug]/page.jsx) that matches path vectors to fetch and render raw Plasmic visual components dynamically." 

  ], 

  "recommended_agent_assignment": { 

    "primary_class": "Next.js App Router Engineer & Headless CMS Core Developer", 

    "twin_context_class": "Plasmic Visual Integration Specialist & Cloud Security Governance Twin" 

  }, 

  "immediate_priority_actions": [ 

    "Purge and rotate the hardcoded Plasmic API credentials out of plasmic.json, shifting secrets to non-committed environment variables.", 

    "Resolve the routing structure clash by removing duplicate layouts and ensuring the PlasmicRootProvider correctly wraps the true application root.", 

    "Fix app/page.jsx to properly render the client page component using valid JSX notation rather than direct functional execution.", 

    "Eradicate the absolute system symlink and refactor cross-project local assets into standard relative dependencies or an independent module package.", 

    "Establish a primary repository validation workflow (.github/workflows/ci.yml) to automate the execution of npm run lint and npm run build loops." 

  ] 

} 

 

 

{ 

  "repository_name": "Trade-Agent-V1", 

  "detected_class": "#Orchestrator", 

  "structural_health_indicators": [ 

    "Node.js ESM backend (server.js) using Express + better-sqlite3; single-process service entry point managed via npm run dev/npm start loops.", 

    "Local state persistence utilizing SQLite with in-process schema migration logic (db/sqlite.js) managing canonical signals and events_journal tables.", 

    "Optional OpenAI-based asynchronous enrichment engine (ai/llm-enrichment.js) gated by OPENAI_API_KEY and configurable via environment variables.", 

    "Integrated Human-in-the-Loop (HITL) workflow consisting of TradingView webhook ingestion, an explicit approval endpoint (/api/signals/:id/approve), and a polling dashboard UI.", 

    "Dedicated autonomy control subsystem (src/autonomyController.js, config/autonomy.json) with strict safety guidelines and paper-only simulation flags.", 

    "Frontend architecture is structured as a decoupled React/Vite application located under apps/dashboard, pre-configured with Tailwind CSS and a local API developer proxy.", 

    "Self-contained isolated integration and stress test runner present (test-suite.js) mapped natively to the npm run check script command.", 

    "Complete absence of Dockerfiles, docker-compose.yml configurations, or automated CI pipelines within the repository structure (.github/workflows is absent)." 

  ], 

  "recommended_agent_assignment": { 

    "primary_class": "Node.js/Express Event-Driven Workflow Orchestrator (SQLite Persistent)", 

    "twin_context_class": "React/Vite Dashboard Frontend Engineer & Autonomy Operational Compliance Twin" 

  }, 

  "immediate_priority_actions": [ 

    "Construct a GitHub Actions pipeline (.github/workflows/ci.yml) to automate backend integration verification and production-ready dashboard builds.", 

    "Package the distributed runtime footprint into a containerized deployment structure utilizing a multi-stage Dockerfile and docker-compose orchestration.", 

    "Formalize development blueprints within a standardized README, covering webhook secret rotation (TRADINGVIEW_WEBHOOK_SECRET), environment fallbacks, and local volume mounting requirements." 

  ] 

} 

 
