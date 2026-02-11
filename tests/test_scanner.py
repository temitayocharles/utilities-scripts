import tempfile
from pathlib import Path
from scanners.github_repo_scanner import extract_env_keys_from_file, classify_keys


def test_extract_env_keys_from_file():
    content = """
API_KEY=abc
DATABASE_URL=postgres://
foo=bar
"""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "test.env"
        p.write_text(content)
        keys = extract_env_keys_from_file(p)
        assert "API_KEY" in keys
        assert "DATABASE_URL" in keys
        assert "foo" not in keys


def test_classify_keys():
    configs, secrets = classify_keys({"API_KEY", "PORT", "DB_PASSWORD"})
    assert "PORT" in configs
    assert "API_KEY" in secrets
    assert "DB_PASSWORD" in secrets
