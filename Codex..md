# Codex: Autonomous 3D Agent Architecture (Meteor Lake Setup)

## 📌 System Goal
To build a highly efficient, 24/7 autonomous agent system that monitors incoming tasks, processes spatial/geometric reasoning, and executes Python mesh-generation scripts inside Blender via the Model Context Protocol (MCP) — optimized strictly for local execution on an Intel Core Ultra 5 (Meteor Lake) platform.

---

## 💻 Hardware Context & Constraints
All code, model parameters, and runner scripts developed in this repository must comply with the following host constraints:
* **Host Processor:** Intel Core Ultra 5 (Meteor Lake).
* **Architecture Limitations:** Hybrid chip with 4 Performance Cores (P-Cores) and 8 Efficient Cores (E-Cores). Low-power NPU (11 TOPS) is bypassed for heavy text tasks.
* **System Memory:** 32GB RAM total.
* **Primary Compute Target:** Integrated Intel Arc GPU (via OpenVINO/Vulkan) or localized P-Cores.

---

## 🛠️ Software Stack & Infrastructure Configuration

### 1. Model Runner (Ollama Backend)
* **API Endpoint:** `http://localhost:11434`
* **Thread Budget:** Strictly locked to `num_thread: 4` to prevent execution from spilling into slow E-Cores.
* **Memory Strategy:** `OLLAMA_KEEP_ALIVE=-1` is set in the host environment to force active models to remain permanently resident in the 32GB RAM buffer for zero-latency wake cycles.

### 2. Model Selection
* **Primary Reasoning & Coding Agent:** `qwen2.5-coder:3b`
  * *Reasoning:* Best-in-class token generation for code synthesis and strict structural layouts (`bpy` API) under tight memory bandwidth constraints.
* **Router / Gatekeeper Agent (Optional):** `phi3:mini` or `llama3:8b` (Quantization: Q5_K_M)
  * *Reasoning:* Handing triage and initial filtering.

---

## 🛡️ Core Engineering Guardrails (Strict Enforcement)

Every agent loop, pipeline script, or automation workflow introduced into this repository **must** adhere to the following rules:

1. **The Iteration Kill-Switch:** No autonomous script generation loop may attempt self-correction or execution retry logic more than **5 consecutive times** for a single task. Upon hitting the limit, the agent must halt, write to `.logs/errors.json`, and await human input.
2. **Context Caching Enforcement:** Because tool structures for Blender MCP are large, scripts interacting with Ollama must maintain persistent API sessions or implement strict message trimming to prevent the CPU from rebuilding massive context histories on every prompt turn.
3. **RAM Protection:** Keep individual model footprints under 8GB total VRAM/RAM profile to guarantee a healthy safety margin for Windows 11 and active Blender workspaces.

---

## 🗂️ Project Directory Structure Blueprint
Maintain the repository layout as follows to keep code and agent artifacts organized:
```text
├── .github/              # CI/CD workflows
├── .logs/                # Automated agent error and runtime logs
├── config/               # Ollama, MCP, and host configuration profiles
├── src/
│   ├── orchestrator/     # Core 24/7 Python automation loops
│   ├── routers/          # Input triage and intent classification logic
│   └── tools/            # MCP clients, Blender handlers, and script validators
├── tests/                # Validation scripts for checking code synthesis
├── CODEX.md              # System blueprint (This file)
└── README.md             # Project overview
```

---

## 🚀 How to Feed this Codex to Coding Tools
When using an AI coding assistant inside this repository, append this instruction to your prompt:
> *"Read `CODEX.md` in the root folder. Match all Python script generation, loop mechanisms, thread counts, and model API calls to the exact specifications, limits, and hardware guardrails outlined in the blueprint."*
