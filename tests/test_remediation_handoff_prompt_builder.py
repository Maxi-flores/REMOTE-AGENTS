from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from remediation_handoff.prompt_builder import build_codex_prompt_for_package  # noqa: E402


class TestRemediationHandoffPromptBuilder(unittest.TestCase):
    def test_includes_runtime_contract_and_repo_specific_bounds(self) -> None:
        prompt = build_codex_prompt_for_package(
            {
                "package_id": "pkg_1",
                "title": "Refactor UI",
                "objective": "Apply UX fixes",
                "metadata": {"repository": "ConceptSHOP"},
            }
        )
        text = prompt["prompt_text"]
        self.assertIn("ABSOLUTE COMPILER RUNTIME CONTRACT (STRICT):", text)
        self.assertIn("RAW-SOURCE-ONLY OUTPUT", text)
        self.assertIn("target_repository=ConceptSHOP", text)
        self.assertIn("primary_agent_class=ViteReactPrimaryAgent", text)
        self.assertIn("max_context_chars=12000", text)

    def test_includes_3d_bounds_for_mucho3d(self) -> None:
        prompt = build_codex_prompt_for_package(
            {
                "package_id": "pkg_2",
                "title": "Refactor scene",
                "objective": "Adjust scene graph",
                "metadata": {"repository": "Mucho3D"},
            }
        )
        text = prompt["prompt_text"]
        self.assertIn("primary_agent_class=3DSceneOrchestratorAgent", text)
        self.assertIn("max_context_chars=16000", text)


if __name__ == "__main__":
    unittest.main()
