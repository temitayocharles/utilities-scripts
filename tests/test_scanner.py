import tempfile
import unittest
from pathlib import Path

from scanners.github_repo_scanner import extract_env_keys_from_file, classify_keys


class TestScanner(unittest.TestCase):
    def test_extract_env_keys_from_file(self):
        content = """API_KEY=abc
DATABASE_URL=postgres://
foo=bar
"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.env"
            p.write_text(content)
            keys = extract_env_keys_from_file(p)
            self.assertIn("API_KEY", keys)
            self.assertIn("DATABASE_URL", keys)
            self.assertNotIn("foo", keys)

    def test_classify_keys(self):
        configs, secrets = classify_keys({"API_KEY", "PORT", "DB_PASSWORD"})
        self.assertIn("PORT", configs)
        self.assertIn("API_KEY", secrets)
        self.assertIn("DB_PASSWORD", secrets)


if __name__ == "__main__":
    unittest.main()
