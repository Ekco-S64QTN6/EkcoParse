"""Configuration path defaults and overrides."""

import tempfile
import unittest
from pathlib import Path

from ekco_parse.config import Config


class TestConfigPaths(unittest.TestCase):
    def test_default_paths_follow_current_home_directory(self):
        config = Config({})
        self.assertEqual(config.log_dir, Path.home() / "Games" / "Project1999" / "Logs")
        self.assertEqual(config.maps_dir, Path.home() / "Games" / "Project1999" / "maps")

    def test_map_directory_can_be_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            maps_dir = Path(tmp) / "custom maps"
            config = Config({
                "map": {"maps_dir": str(maps_dir)},
                "log_tailer": {"log_dir": str(Path(tmp) / "logs")},
            })
            self.assertEqual(config.maps_dir, maps_dir)
            self.assertEqual(config.log_dir, Path(tmp) / "logs")


if __name__ == "__main__":
    unittest.main()
