# Agent Guidance & Implementation Directory (AGENT_GUIDE_LIST.md)

## 1. System Overview
18 repositories are mapped to required agent roles; 16 have both class and JSON definitions and are ready for training.
2 are pending definition/training due to missing class and/or JSON configuration references.

## 2. Agent Mapping by Repository

### ConceptSHOP (concept-shop.online)(custom-shop.online)
* **Agent Class:** Primary: React/Vite Frontend Agent (React Router, Tailwind, SPA architecture); Twin: Firebase + Cloud Integrations Agent (Firestore data models & AWS bounds)
* **JSON Configuration:** `{"repository_name":"ConceptShop","detected_class":"#Retail","structural_health_indicators":["Vite + React 18 SPA backed by a client-side Firebase infrastructure layer","Client-side AWS SDK usage leaks VITE_ environment parameters inside browser scopes","ESLint scripts fail due to an absent linter configuration file mapping"],"recommended_agent_assignment":{"primary_class":"React/Vite frontend agent","twin_context_class":"Firebase + cloud integrations agent"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern ConceptShop by executing React/Vite Frontend Agent (React Router, Tailwind, SPA architecture) tasks with Firebase + Cloud Integrations Agent (Firestore data models & AWS bounds) validation to prevent regressions and secret leaks.

### Mucho3D (mucho3d.com) 
* **Agent Class:** Primary: Runtime Diagnostic & Web Audit Agent; Twin: Environment Health & Configuration Twin
* **JSON Configuration:** `N/A`
* **Status:** Pending Implementation
* **Core Objective:** Govern Mucho3D by executing Runtime Diagnostic & Web Audit Agent tasks with Environment Health & Configuration Twin validation to prevent regressions and secret leaks.

### Powerframe-WAI (wai.powerframe.online)
* **Agent Class:** Pending Definition/Training
* **JSON Configuration:** `N/A`
* **Status:** Pending Definition/Training
* **Core Objective:** Define an agent class and JSON configuration for PORTFOLIO based on its functional scope and governance needs.

### Dealinstinct (Dealinstinct.com)
* **Agent Class:** Primary: Next.js App Router + Plasmic Integration Engineer; Twin: Security/DevOps Hygiene Twin (Mitigate hardcoded script secrets)
* **JSON Configuration:** `{"repository_name":"Dealinstinct","detected_class":"#Web tool","structural_health_indicators":["Next.js 14 App Router project with Plasmic loader integration","Secret risk: scripts/setup-plasmic.sh contains a hardcoded Plasmic token string","Next.js routing risk: both app/layout.js and app/layout.jsx exist","RSC boundary risk: lib/plasmic-server.js breaks server imports via client tags"],"recommended_agent_assignment":{"primary_class":"Next.js App Router + Plasmic integration","twin_context_class":"Security/DevOps hygiene specialist"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern Dealinstinct by executing Next.js App Router + Plasmic Integration Engineer tasks with Security/DevOps Hygiene Twin (Mitigate hardcoded script secrets) validation to prevent regressions and secret leaks.

### Dealinstinct V2 (Dealinstinct.com)
* **Agent Class:** Primary: Next.js App Router + Plasmic Integration Engineer; Twin: Security/DevOps Hygiene Twin (Mitigate hardcoded script secrets)
* **JSON Configuration:** `{"repository_name":"Dealinstinct","detected_class":"#Web tool","structural_health_indicators":["Next.js 14 App Router project with Plasmic loader integration","Secret risk: scripts/setup-plasmic.sh contains a hardcoded Plasmic token string","Next.js routing risk: both app/layout.js and app/layout.jsx exist","RSC boundary risk: lib/plasmic-server.js breaks server imports via client tags"],"recommended_agent_assignment":{"primary_class":"Next.js App Router + Plasmic integration","twin_context_class":"Security/DevOps hygiene specialist"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern Dealinstinct by executing Next.js App Router + Plasmic Integration Engineer tasks with Security/DevOps Hygiene Twin (Mitigate hardcoded script secrets) validation to prevent regressions and secret leaks.

### Powerframe (powerframe.online)
* **Agent Class:** Primary: frontend_spa_orchestrator_agent; Twin: serverless_auth_api_agent
* **JSON Configuration:** `{"repository_name":"Powerframe","detected_class":"#Orchestrator","structural_health_indicators":["Single-package React 18 + Vite + Tailwind SPA (ESM)","Acts as an ecosystem Hub/launcher via src/config/apps.js","Vercel deployment routing present (vercel.json SPA rewrites)","Auth implementation contains hardcoded JWT secret fallback strings","Naming drift: package.json name is bms-dashboard while repo is Powerframe Hub"],"recommended_agent_assignment":{"primary_class":"frontend_spa_orchestrator_agent","twin_context_class":"serverless_auth_api_agent"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern Powerframe by executing frontend_spa_orchestrator_agent tasks with serverless_auth_api_agent validation to prevent regressions and secret leaks.

### Powerframe-CRM (crm.powerframe.online)
* **Agent Class:** Primary: Frontend React/Vite Dashboard Agent; Twin: Firebase + GMS Telemetry Integration Agent
* **JSON Configuration:** `{"repository_name":"Powerframe-CRM","detected_class":"#Web tool","structural_health_indicators":["Vite + React app web dashboard UI using Firebase Auth/Firestore","No env.example/sample exists for required VITE_ environment variables","Contains parallel/duplicated module structures between root and sub-packages"],"recommended_agent_assignment":{"primary_class":"Frontend React/Vite dashboard agent","twin_context_class":"Firebase + GMS telemetry integration agent"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern Powerframe-CRM by executing Frontend React/Vite Dashboard Agent tasks with Firebase + GMS Telemetry Integration Agent validation to prevent regressions and secret leaks.

### Powerframe-GMS (gms.powerframe.online)
* **Agent Class:** Primary: Vite/React Web App Agent (Routing & UI Shell); Twin: Unity Bridge/Integration Agent (postMessage boundary management)
* **JSON Configuration:** `{"repository_name":"powerframe-gms","detected_class":"#Web tool","structural_health_indicators":["Vite + React SPA with Vercel-style api handlers and deployment configurations","Firebase configuration contains placeholder-only REPLACE_ME values","JWT secret has an insecure dev fallback string left in production logic"],"recommended_agent_assignment":{"primary_class":"Vite/React Web App Agent","twin_context_class":"Unity Bridge/Integration Agent"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern Powerframe-GMS by executing Vite/React Web App Agent (Routing & UI Shell) tasks with Unity Bridge/Integration Agent (postMessage boundary management) validation to prevent regressions and secret leaks.

### Powerframe-TPR (tpr.powerframe.online)
* **Agent Class:** Primary: Front-end Web App Maintainer (Static Dashboard + Vite Build); Twin: Node Data-Pipeline & Firebase Sync Worker
* **JSON Configuration:** `{"repository_name":"Powerframe-TPR","detected_class":"#Web tool","structural_health_indicators":["Node/Vite monorepo: root builds static apps to dist/","Data-generation pipeline centralized in root scripts/ emitting raw JSON files","Potential drift risk: multiple package.json manifests with mismatched Vite versions"],"recommended_agent_assignment":{"primary_class":"Front-end web app maintainer","twin_context_class":"Node data-pipeline & sync worker"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern Powerframe-TPR by executing Front-end Web App Maintainer (Static Dashboard + Vite Build) tasks with Node Data-Pipeline & Firebase Sync Worker validation to prevent regressions and secret leaks.

### Powerframe-WMS (wms.powerframe.online)
* **Agent Class:** Primary: React/Vite Frontend + Node (CJS) Data Generation Pipeline Engineer; Twin: JSON-Schema Contract & Telemetry Validation Specialist
* **JSON Configuration:** `{"repository_name":"Powerframe-WMS","detected_class":"#Web tool","structural_health_indicators":["Single React app with a deterministic Node.js data pipeline engine","Bridge surface defined as a JSON schema configuration file at root","Documentation drift risk: specs describe a larger system tree than implemented"],"recommended_agent_assignment":{"primary_class":"React/Vite Frontend + Node Data Generation Engineer","twin_context_class":"JSON-Schema Contract & Telemetry Validation Specialist"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern Powerframe-WMS by executing React/Vite Frontend + Node (CJS) Data Generation Pipeline Engineer tasks with JSON-Schema Contract & Telemetry Validation Specialist validation to prevent regressions and secret leaks.

### PowerStarter (powerstarter.dev)
* **Agent Class:** Primary: TypeScript/React Monorepo Build Platform Engineer; Twin: DevOps & Caddy Infrastructure Orchestration Specialist
* **JSON Configuration:** `{"repository_name":"PowerStarter","detected_class":"#Orchestrator","structural_health_indicators":["pnpm monorepo workspace structure controlled via root yaml and lockfile","Three separate React 18/19 + Vite 5 frontend applications inside /apps","Structural regression: docker-compose references non-existent paths","Incomplete build containers: Dockerfile contexts are omitted from active subdirs"],"recommended_agent_assignment":{"primary_class":"TypeScript/React Monorepo Build Platform Engineer","twin_context_class":"DevOps & Caddy Infrastructure Orchestration Specialist"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern PowerStarter by executing TypeScript/React Monorepo Build Platform Engineer tasks with DevOps & Caddy Infrastructure Orchestration Specialist validation to prevent regressions and secret leaks.

### TheRocketTree-App (therockettree.io)
* **Agent Class:** Primary: TypeScript Monorepo Build Platform Agent (pnpm + Turborepo + Prisma); Twin: Bridge-Chain & Unity Adapter Agent (Zod contracts + layout-token validation)
* **JSON Configuration:** `{"repository_name":"TheRocketTree-App","detected_class":"#Orchestrator","structural_health_indicators":["TypeScript monorepo using pnpm workspaces + Turborepo task graph","Primary runtime apps are Next.js 15 + React 19 using /app router","Shared packages include contracts (Zod), logic (semantic engine), db (Prisma)","Build-time bridge-chain contract exists: apps/gms generates layout artifacts","Unity integration exists via @trt/unity-adapter package"],"recommended_agent_assignment":{"primary_class":"TypeScript Monorepo Build/Platform Agent","twin_context_class":"Bridge-Chain & Unity Adapter Agent"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern TheRocketTree-App by executing TypeScript Monorepo Build Platform Agent (pnpm + Turborepo + Prisma) tasks with Bridge-Chain & Unity Adapter Agent (Zod contracts + layout-token validation) validation to prevent regressions and secret leaks.

### TheRocketTree-Web (therockettree.io)
* **Agent Class:** Primary: Frontend Agent (React/Vite/Tailwind UI Surface); Twin: Docs/Governance Agent (Markdown rules & orchestration logging)
* **JSON Configuration:** `{"repository_name":"TheRocketTree-Web","detected_class":"#Web tool","structural_health_indicators":["Vite + React 18 single-page app (ESM) targeting clean static hosting","Index.html loads thin mount points and imports layout data from external CDNs","No continuous integration or code lint/format configurations present"],"recommended_agent_assignment":{"primary_class":"Frontend agent (React/Vite/Tailwind UI surface)","twin_context_class":"Docs/governance agent"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern TheRocketTree-Web by executing Frontend Agent (React/Vite/Tailwind UI Surface) tasks with Docs/Governance Agent (Markdown rules & orchestration logging) validation to prevent regressions and secret leaks.

### TheRocketTreeUnity (therockettree.io)
* **Agent Class:** Primary: Unity/C# Gameplay Systems Agent (Tree Game Mode State Engine); Twin: Firebase Cloud Functions / TypeScript Backend Agent
* **JSON Configuration:** `{"repository_name":"TheRocketTreeUnity","detected_class":"#Game tool","structural_health_indicators":["Unity project layout pinned explicitly to runtime version 6000.3.2f1","Functions directory lacks package/tsconfig manifests, rendering it unbuildable","Model Context Protocol (MCP) server configuration points to non-existent packages"],"recommended_agent_assignment":{"primary_class":"Unity/C# Gameplay Systems Agent","twin_context_class":"Firebase Cloud Functions / TypeScript Backend Agent"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern TheRocketTreeUnity by executing Unity/C# Gameplay Systems Agent (Tree Game Mode State Engine) tasks with Firebase Cloud Functions / TypeScript Backend Agent validation to prevent regressions and secret leaks.

### Sapient KB (skb.powerstarter.dev)
* **Agent Class:** Primary: Next.js 14/15 & React-Three-Fiber Web Tooling Engineer; Twin: Vercel Serverless Architecture & Monorepo Build Pipeline Specialist
* **JSON Configuration:** `{"repository_name":"Sapient-KB","detected_class":"#Web tool","structural_health_indicators":["pnpm monorepo workspace tracking Next.js 14 with a Next.js 15 upgrade target ADR","Integrates 3D rendering canvases using react-three-fiber and drei libraries","Workspace execution scripts fail due to missing build paths in micro-packages"],"recommended_agent_assignment":{"primary_class":"Next.js & React-Three-Fiber Web Tooling Engineer","twin_context_class":"Vercel Serverless Architecture & Monorepo Pipeline Specialist"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern Sapient-KB by executing Next.js 14/15 & React-Three-Fiber Web Tooling Engineer tasks with Vercel Serverless Architecture & Monorepo Build Pipeline Specialist validation to prevent regressions and secret leaks.

### Bikerinstinct (bikerinstinct.com)
* **Agent Class:** Primary: Next.js App Router Engineer & Headless CMS Core Developer; Twin: Plasmic Visual Integration Specialist & Cloud Security Governance Twin
* **JSON Configuration:** `{"repository_name":"Bikerinstinct","detected_class":"#Web tool","structural_health_indicators":["Next.js 14 project containing a hardcoded projectApiToken inside plasmic.json","Routing clash: duplicate layout extensions (.js and .jsx) bypass providers","Compilation error: local absolute host symlinks pointing to hardcoded user paths"],"recommended_agent_assignment":{"primary_class":"Next.js App Router Engineer & Headless CMS Core Developer","twin_context_class":"Plasmic Visual Integration & Cloud Security Governance Twin"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern Bikerinstinct by executing Next.js App Router Engineer & Headless CMS Core Developer tasks with Plasmic Visual Integration Specialist & Cloud Security Governance Twin validation to prevent regressions and secret leaks.

### WOMmedia (wommedia.nl)
* **Agent Class:** Primary: Next.js (React) Frontend Engineer; Twin: UI/UX + Motion Specialist (Tailwind v4 theme token compliance)
* **JSON Configuration:** `{"repository_name":"WOMmedia","detected_class":"#Web tool","structural_health_indicators":["Next.js 15 App Router using Tailwind CSS v4 via experimental import tokens","Site content is hardcoded in /lib/site-data.js; zero backend systems detected","No infrastructure files, GitHub actions workflows, or root READMEs exist"],"recommended_agent_assignment":{"primary_class":"Next.js (React) frontend engineer","twin_context_class":"UI/UX + motion specialist"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern WOMmedia by executing Next.js (React) Frontend Engineer tasks with UI/UX + Motion Specialist (Tailwind v4 theme token compliance) validation to prevent regressions and secret leaks.

### Trade Agent – V1 (sentient.powerframe.online)
* **Agent Class:** Primary: Node.js/Express Event-Driven Workflow Orchestrator (SQLite Persistent); Twin: React/Vite Dashboard Frontend Engineer & Autonomy Compliance Twin
* **JSON Configuration:** `{"repository_name":"Trade-Agent-V1","detected_class":"#Orchestrator","structural_health_indicators":["Node.js ESM backend (server.js) using Express + better-sqlite3","Local state persistence utilizing SQLite with in-process schema migrations","Integrated Human-in-the-Loop (HITL) workflow via TradingView webhooks","Total absence of Dockerfiles or automated CI/CD configurations"],"recommended_agent_assignment":{"primary_class":"Node.js/Express Event-Driven Workflow Orchestrator","twin_context_class":"React/Vite Dashboard Frontend Engineer & Compliance Twin"}}`
* **Status:** Ready for Training
* **Core Objective:** Govern Trade-Agent-V1 by executing Node.js/Express Event-Driven Workflow Orchestrator (SQLite Persistent) tasks with React/Vite Dashboard Frontend Engineer & Autonomy Compliance Twin validation to prevent regressions and secret leaks.

missing webprojects/functions:
- bis.powerframe.online
- finance.powerframe.online
- AI_guide_plane > sentientOS = sentient.powerframe.online

## 3. Training & Implementation Matrix

| Agent Class | Target Repository | Training Data (JSON Ref) | Implementation Status |
| :--- | :--- | :--- | :--- |
| Primary: React/Vite Frontend Agent (React Router, Tailwind, SPA architecture); Twin: Firebase + Cloud Integrations Agent (Firestore data models & AWS bounds) | ConceptSHOP | `repository_name=ConceptShop` | Ready for Training |
| Primary: Runtime Diagnostic & Web Audit Agent; Twin: Environment Health & Configuration Twin | Mucho3D | N/A | Pending Implementation |
| Pending Definition/Training | PF-WAI | N/A | Pending Definition/Training |
| Primary: Next.js App Router + Plasmic Integration Engineer; Twin: Security/DevOps Hygiene Twin (Mitigate hardcoded script secrets) | Dealinstinct Frontend | `repository_name=Dealinstinct` | Ready for Training |
| Primary: Next.js App Router + Plasmic Integration Engineer; Twin: Security/DevOps Hygiene Twin (Mitigate hardcoded script secrets) | Dealinstinct V2 | `repository_name=Dealinstinct` | Ready for Training |
| Primary: frontend_spa_orchestrator_agent; Twin: serverless_auth_api_agent | Powerframe | `repository_name=Powerframe` | Ready for Training |
| Primary: Frontend React/Vite Dashboard Agent; Twin: Firebase + GMS Telemetry Integration Agent | Powerframe-CRM | `repository_name=Powerframe-CRM` | Ready for Training |
| Primary: Vite/React Web App Agent (Routing & UI Shell); Twin: Unity Bridge/Integration Agent (postMessage boundary management) | Powerframe-GMS | `repository_name=powerframe-gms` | Ready for Training |
| Primary: Front-end Web App Maintainer (Static Dashboard + Vite Build); Twin: Node Data-Pipeline & Firebase Sync Worker | Powerframe-TPR | `repository_name=Powerframe-TPR` | Ready for Training |
| Primary: React/Vite Frontend + Node (CJS) Data Generation Pipeline Engineer; Twin: JSON-Schema Contract & Telemetry Validation Specialist | Powerframe-WMS | `repository_name=Powerframe-WMS` | Ready for Training |
| Primary: TypeScript/React Monorepo Build Platform Engineer; Twin: DevOps & Caddy Infrastructure Orchestration Specialist | PowerStarter | `repository_name=PowerStarter` | Ready for Training |
| Primary: TypeScript Monorepo Build Platform Agent (pnpm + Turborepo + Prisma); Twin: Bridge-Chain & Unity Adapter Agent (Zod contracts + layout-token validation) | TheRocketTree-App | `repository_name=TheRocketTree-App` | Ready for Training |
| Primary: Frontend Agent (React/Vite/Tailwind UI Surface); Twin: Docs/Governance Agent (Markdown rules & orchestration logging) | TheRocketTree-Web | `repository_name=TheRocketTree-Web` | Ready for Training |
| Primary: Unity/C# Gameplay Systems Agent (Tree Game Mode State Engine); Twin: Firebase Cloud Functions / TypeScript Backend Agent | TheRocketTreeUnity | `repository_name=TheRocketTreeUnity` | Ready for Training |
| Primary: Next.js 14/15 & React-Three-Fiber Web Tooling Engineer; Twin: Vercel Serverless Architecture & Monorepo Build Pipeline Specialist | Sapient KB | `repository_name=Sapient-KB` | Ready for Training |
| Primary: Next.js App Router Engineer & Headless CMS Core Developer; Twin: Plasmic Visual Integration Specialist & Cloud Security Governance Twin | Bikerinstinct | `repository_name=Bikerinstinct` | Ready for Training |
| Primary: Next.js (React) Frontend Engineer; Twin: UI/UX + Motion Specialist (Tailwind v4 theme token compliance) | WOMmedia | `repository_name=WOMmedia` | Ready for Training |
| Primary: Node.js/Express Event-Driven Workflow Orchestrator (SQLite Persistent); Twin: React/Vite Dashboard Frontend Engineer & Autonomy Compliance Twin | Trade Agent – V1 | `repository_name=Trade-Agent-V1` | Ready for Training |

---

# 👥 General AI Crew Persona Blueprint

Every repository inside the platform workspace is assigned a distinct **Primary (Execution)** and **Twin (Compliance)** agent pair. Below is the standardized role directory used to guide task synthesis and consensus validation.

---

### 1. The Full-Stack Ecosystem Crew
*Applied to: Dealinstinct, Bikerinstinct, WOMmedia, ConceptSHOP, Powerframe-CRM, TheRocketTree-Web*

*   **Primary Agent: Application Feature Architect**
    *   **Role:** Writes, updates, and refactors user interface layers, API route handlers, configuration wrappers, and core business logic.
    *   **Core Directive:** Deliver clean, modular, and functional TypeScript/JavaScript/Python code matching the specific repository's framework conventions.
*   **Twin Agent: Framework & UX Compliance Auditor**
    *   **Role:** Reviews code written by the Primary Agent before execution or disk commit.
    *   **Core Directive:** Enforce strict type definitions, detect layout anti-patterns, filter out syntax bugs, and ensure seamless routing consistency.

---

### 2. The Data Core & Infrastructure Crew
*Applied to: Powerframe-Hubs, Powerframe-GMS, Powerframe-TPR, Powerframe-WMS, Trade Agent*

*   **Primary Agent: Pipeline & Systems Automation Engineer**
    *   **Role:** Optimizes system query performance, updates data schemas, manages automated background workers, and crafts transactional workflows.
    *   **Core Directive:** Ensure high-throughput data processing, atomic database operations, and resilient message payload configurations.
*   **Twin Agent: Security, Schema & Edge-Case Validator**
    *   **Role:** Acts as an on-device data gatekeeper during the consensus review turn.
    *   **Core Directive:** Scan for SQL injection vulnerabilities, enforce strict input serialization boundaries, verify error-catch fallbacks, and prevent data leakage.

---

### 3. The 3D Graphics & Neural Pipeline Crew (Static Data Context Only)
*Applied to: Sapient KB, TheRocketTreeUnity, Mucho3D, PF-WAI*

*   **Primary Agent: Spatial Math & Tensor Graph Optimizer**
    *   **Role:** Synthesizes transformation matrices, parses tridimensional geometry coordinate arrays, and maps layout metadata blocks.
    *   **Core Directive:** Optimize linear algebra arrays and model parameters under tight local memory budgets.
*   **Twin Agent: Finite-Number & Sandbox Security Sentinel**
    *   **Role:** Audits spatial algorithms and isolated data generation pathways.
    *   **Core Directive:** Flag division-by-zero risks, neutralize infinite floating-point calculations, and enforce strict execution directory boundaries.

---

### 4. The System Diagnostic Crew (Global Workspace Fallback)
*Applied to: Unmapped repositories or corrupted payload targets*

*   **Primary Agent: Runtime Diagnostic Troubleshooter**
    *   **Role:** Evaluates execution trace files, analyzes syntax failures, and builds automated fallback patches.
    *   **Core Directive:** Keep the local automation daemon alive and unblocked without executing unauthorized scripts.
*   **Twin Agent: Low-Privilege Safety Guardian**
    *   **Role:** Locks down environment configurations during error states.
    *   **Core Directive:** Force read-only operations, block unexpected network data calls, and write structured telemetry tracking logs to `.logs/errors.json`.
