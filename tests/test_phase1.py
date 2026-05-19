"""Phase 1 sanity tests."""

from __future__ import annotations

import unittest

from utils.config import load_settings
from utils.paths import ensure_storage_directories, project_root


class Phase1Tests(unittest.TestCase):
    """Validate the initial project scaffold."""

    def test_settings_load(self) -> None:
        settings = load_settings()

        self.assertEqual(settings["market"]["default_index"], "NIFTY50")
        self.assertIn("raw_data_dir", settings["storage"])

    def test_storage_directories_exist(self) -> None:
        settings = load_settings()
        directories = ensure_storage_directories(settings)

        self.assertGreaterEqual(len(directories), 5)
        for directory in directories:
            self.assertTrue(directory.exists())

    def test_project_root_points_to_repo(self) -> None:
        self.assertTrue((project_root() / "main.py").exists())


if __name__ == "__main__":
    unittest.main()
