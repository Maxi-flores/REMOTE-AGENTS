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

from release_gates.policy_loader import list_available_gate_policies, load_named_gate_policy, load_gate_policy  # noqa: E402


class TestReleaseGatesPolicyLoader(unittest.TestCase):
    def test_policy_files_parse_and_validate(self) -> None:
        base = REPO_ROOT / "config" / "release_gates"
        for name in ("default_gate_policy.json", "strict_gate_policy.json", "experimental_gate_policy.json"):
            with self.subTest(name=name):
                payload = load_gate_policy(base / name)
                self.assertIn("policy_id", payload)

    def test_list_policies_returns_expected_profiles(self) -> None:
        names = list_available_gate_policies(REPO_ROOT / "config" / "release_gates")
        self.assertIn("default_gate_policy", names)
        self.assertIn("strict_gate_policy", names)
        self.assertIn("experimental_gate_policy", names)

    def test_missing_policy_returns_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = load_named_gate_policy("not_there", base_dir=tmp)
            self.assertTrue(payload["metadata"]["fallback"])


if __name__ == "__main__":
    unittest.main()

