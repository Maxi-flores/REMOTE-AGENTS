# Remote-Agents Pipeline: Automated Design-Genome & Self-Healing UI

## 1. System Overview
This repository automates the end-to-end design, generation, and quality assurance lifecycle of targeted web applications. The system bypasses traditional, manual UI asset creation by chaining semantic model understanding with deterministic headless browser testing and automated code-healing.

### Orchestration Stack
- **Core Agent / Executor:** Cline (CLI-driven workspace manipulation)
- **Semantic Expansion & Vision Evaluator:** Qwen (2.5/3.2 + Vision Variants)
- **Asset / Token Generator:** OpenAI / Codex

---

## 2. Pipeline Phase 1: Design-Genome Extraction (`skills.md`)

When a new theme keyword is initiated (e.g., `"liquid glacier - theme"`), the system must execute the following protocol to generate the repository's baseline `skills.md` file.

### Step 1: Token Generation Protocol
Pass the theme name to Qwen using the exact schema envelope below. Do not accept free-form conversational text.

```json
{
  "system_instruction": "Act as a Principal Design Token Compiler. Translate the user theme into deterministic UI parameters.",
  "required_output_format": "Strict JSON only",
  "schema": {
    "theme_name": "string",
    "palette": {
      "primary": "HEX",
      "secondary": "HEX",
      "background_canvas": "HEX",
      "surface_card": "HEX",
      "accent_glow": "HEX"
    },
    "effects": {
      "backdrop_blur": "string (e.g., '12px')",
      "surface_opacity": "float (0.00 to 1.00)",
      "border_radius": "string (e.g., '16px')"
    },
    "typography": {
      "font_heading": "string (Google Font Name)",
      "font_body": "string (Google Font Name)",
      "base_size": "string",
      "line_height_multiplier": "float"
    }
  }
}
```

### Step 2: Reference Image Rendering
The generated JSON parameters must be concatenated into an atomic prompt string and transmitted to the OpenAI DALL-E 3 API. 
- **Prompt Formula:** `Comprehensive, high-fidelity UI/UX component kit layout preview showcasing dashboards, buttons, inputs, and cards. Style rules: Clean modern web design, strictly utilizing the following token values: [INSERT PALETTE & EFFECTS JSON]. No text distortion, no low-resolution elements.`
- Save the resulting URL/Image asset to `/.design_genome/reference_render.png`.

### Step 3: Compiling `skills.md`
Codex / Qwen must map the JSON tokens and the baseline component template into the root `skills.md` file. Cline will use this file as its immutable design guardrail.

```markdown
<!-- Saved directly to target_repo/skills.md -->
# System Skills & Design Genome: [THEME_NAME]

## 1. Core Visual Tokens
- Primary: [HEX]
- Secondary: [HEX]
- Background: [HEX]
- Surface Card: [HEX]
- Opacity/Blur: [OPACITY] / [BLUR]

## 2. Typography Rules
- Headings: [FONT_HEADING], Weight: 700
- Body Text: [FONT_BODY], Weight: 400

## 3. Mandatory Component Styles (Tailwind / CSS Baseline)
- Buttons must use `bg-[PRIMARY]` with a backdrop blur of `backdrop-blur-[BLUR]` and an opacity modifier of `bg-opacity-[OPACITY]`.
- All cards must use `rounded-[BORDER_RADIUS]` and a subtle shadow wrapper matching `[ACCENT_GLOW]`.

## 4. Agent Execution Constraint
- You are strictly forbidden from writing inline CSS or utilizing Tailwind colors outside of this genome map. Any component generation must match these structural variables.
```

---

## 3. Pipeline Phase 2: Autonomous UI/UX Stress Testing & Self-Healing

Once Cline builds out the application infrastructure based on `skills.md`, the repository must enter an automated evaluation loop.

### Compiler Runtime Contract (Strict)
When processing runtime bug payloads, layout break reports, or Qwen-Vision contrast failures, the active code compiler must comply with all requirements below.

1. Output format:
- Return raw, production-ready source code only.
- Do not emit markdown wrappers, code fences, explanations, greetings, or non-code characters.
- Ensure imports, brackets, tags, and syntax are fully closed.

2. Design-genome enforcement:
- Every generated line must inherit active `skills.md` visual tokens and typography variables.
- Do not introduce arbitrary inline style overrides or hardcoded attributes that deviate from the genome map.
- Preserve repository-native contrast matrices, opacity modifiers, and canvas/background token usage.

3. Failure isolation and repair:
- Isolate failing component boundaries before editing.
- Refactor container layout metrics natively to preserve responsive scaling.
- Resolve the reported exception/log failure without breaking parent execution semantics.
- Emit the fully refactored source file payload as the only output artifact.
