# Autonomous Expert Roles & Logic Directory (DESIGNATED_AGENTS_LIST.md)

## 1. Core Logic Functions & Domains
* **Intake & Context Domain**: Parses business cases, tokenizes requirements, and maps out initial constraints [1].
* **Architecture & Compiling Domain**: Performs static analysis, creates system topologies, and enforces design patterns.
* **Risk & Security Domain**: Runs automated threat modeling, payload validation, and compliance checks.
* **Pipeline Automation Domain**: Orchestrates CI/CD triggers, artifact compilation, and repository isolation.

## 2. Designated Expert Roles Mapping

### Role: Intake Specialist Agent (ISA)
* **Domain Assignment**: Intake & Context Domain
* **Logic Function**: Converts unstructured text inputs into strict structural configuration JSON payloads.
* **Assigned Repo Targets**: `Sapient-KB`, `Powerframe-Hub`
* **Twin Peer validation**: Intake Twin Auditor (ITA)

### Role: Software Architect Specialist (SAS)
* **Domain Assignment**: Architecture & Compiling Domain
* **Logic Function**: Resolves dependencies, generates module skeletons, and assigns system parameters.
* **Assigned Repo Targets**: `Dealinstinct-Core`, `Dealinstinct-Submodules`
* **Twin Peer validation**: Architecture Twin Auditor (ATA)

### Role: Compliance & Risk Specialist (CRS)
* **Domain Assignment**: Risk & Security Domain
* **Logic Function**: Scans code for vulnerability footprints, checks license compliance, and mocks edge-case data.
* **Assigned Repo Targets**: `Security-Gateway`, `Test-Suite-Validation`
* **Twin Peer validation**: Risk Twin Auditor (RTA)

### Role: Build Orphestation Agent (BOA)
* **Domain Assignment**: Pipeline Automation Domain
* **Logic Function**: Compiles binaries, generates deployment artifacts, and monitors execution states.
* **Assigned Repo Targets**: `Remote-Agents-Core`, `Deployment-Orchestrator`
* **Twin Peer validation**: Build Twin Auditor (BTA)

## 3. Autonomous Cross-Twin Handshake Matrix

| Origin Agent | Target Agent | Handshake Protocol | Payload Schema Reference |
| :--- | :--- | :--- | :--- |
| ISA (Intake) | SAS (Architect) | Deterministic JSON Packet | `schema/intake_handshake.json` |
| SAS (Architect) | CRS (Risk) | Technical Blueprint Matrix | `schema/architecture_blueprint.json` |
| CRS (Risk) | BOA (Build) | Risk Clearance Manifest | `schema/risk_clearance.json` |

