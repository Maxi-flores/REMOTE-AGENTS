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

from release_gates.promotion_loader import (  # noqa: E402
    list_available_promotion_profiles,
    load_named_promotion_profile,
    load_promotion_profile,
)


class TestReleasePromotionLoader(unittest.TestCase):
    def test_profiles_parse_and_validate(self) -> None:
        base = REPO_ROOT / "config" / "release_gates" / "promotion_profiles"
        for name in (
            "dev_promotion_profile.json",
            "staging_promotion_profile.json",
            "production_promotion_profile.json",
        ):
            payload = load_promotion_profile(base / name)
            self.assertIn("profile_id", payload)

    def test_list_profiles_returns_expected(self) -> None:
        names = list_available_promotion_profiles(REPO_ROOT / "config" / "release_gates" / "promotion_profiles")
        self.assertIn("dev_promotion_profile", names)
        self.assertIn("staging_promotion_profile", names)
        self.assertIn("production_promotion_profile", names)

    def test_missing_profile_returns_fallback(self) -> None:
        payload = load_named_promotion_profile("not_there", base_dir=REPO_ROOT / "config" / "release_gates" / "promotion_profiles" / "none")
        self.assertTrue(payload["metadata"]["fallback"])


if __name__ == "__main__":
    unittest.main()

