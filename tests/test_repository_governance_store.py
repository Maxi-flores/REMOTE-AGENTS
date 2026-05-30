from __future__ import annotations

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

from repository_governance.contracts import (  # noqa: E402
    create_audit_record,
    create_governance_profile,
    create_health_snapshot,
)
from repository_governance.store import RepositoryGovernanceStore  # noqa: E402


class TestRepositoryGovernanceStore(unittest.TestCase):
    def test_store_can_upsert_read_and_list_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RepositoryGovernanceStore(Path(tmp) / ".governance" / "repositories.json")
            profile = create_governance_profile(
                repository_name="ConceptSHOP",
                repository_group="spa_ui_frontends_vite_react",
                status="active",
                risk_tier="high",
            )
            store.upsert_profile(profile)
            loaded = store.get_profile("ConceptSHOP")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["repository_name"], "ConceptSHOP")
            self.assertEqual(len(store.list_profiles()), 1)

    def test_store_can_append_and_list_health_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RepositoryGovernanceStore(Path(tmp) / ".governance" / "repositories.json")
            snapshot = create_health_snapshot(
                repository_name="ConceptSHOP",
                status="warning",
                warnings=["lint config missing"],
            )
            store.append_health_snapshot(snapshot)
            snapshots = store.list_health_snapshots("ConceptSHOP")
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(snapshots[0]["status"], "warning")

    def test_store_can_append_and_list_audit_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RepositoryGovernanceStore(Path(tmp) / ".governance" / "repositories.json")
            record = create_audit_record(
                repository_name="ConceptSHOP",
                actor="mission-engine",
                action="evaluate:write",
                operation="write",
                decision="needs_approval",
                risk_tier="high",
            )
            store.append_audit_record(record)
            records = store.list_audit_records("ConceptSHOP")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["decision"], "needs_approval")


if __name__ == "__main__":
    unittest.main()
