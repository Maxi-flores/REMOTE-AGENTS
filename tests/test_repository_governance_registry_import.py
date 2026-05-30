from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from repository_governance.registry_import import (  # noqa: E402
    import_profiles_from_repositories_registry,
    profile_from_repository_registry_record,
)


class TestRepositoryGovernanceRegistryImport(unittest.TestCase):
    def test_profile_from_repository_registry_record(self) -> None:
        profile = profile_from_repository_registry_record(
            {
                "name": "ConceptSHOP",
                "group": "spa_ui_frontends_vite_react",
                "category": "Retail",
                "status": "Ready for Training",
                "primary_agent_class": "ViteReactPrimaryAgent",
                "twin_agent_class": "ViteReactTwinAgent",
                "structural_health_indicators": ["Secret risk: hardcoded JWT"],
            }
        )
        self.assertEqual(profile.repository_name, "ConceptSHOP")
        self.assertEqual(profile.status, "active")
        self.assertEqual(profile.risk_tier, "high")
        self.assertEqual(profile.primary_agent_class, "ViteReactPrimaryAgent")

    def test_import_helper_creates_profiles_from_repository_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "repositories.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "repositories": [
                            {
                                "name": "Powerframe",
                                "group": "monorepos_and_hubs",
                                "category": "Orchestrator",
                                "status": "Ready for Training",
                                "structural_health_indicators": ["Vite build present"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            profiles = import_profiles_from_repositories_registry(path)
            self.assertEqual(len(profiles), 1)
            self.assertEqual(profiles[0].repository_name, "Powerframe")
            self.assertIn("build", profiles[0].required_checks)

    def test_import_helper_does_not_modify_canonical_registry(self) -> None:
        registry_path = REPO_ROOT / "config" / "registries" / "repositories.json"
        before = registry_path.read_text(encoding="utf-8")
        profiles = import_profiles_from_repositories_registry(registry_path)
        after = registry_path.read_text(encoding="utf-8")
        self.assertGreater(len(profiles), 0)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
