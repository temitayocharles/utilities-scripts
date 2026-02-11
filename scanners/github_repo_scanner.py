#!/usr/bin/env python3
import argparse
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

GITHUB_API = "https://api.github.com"

ENV_LINE_RE = re.compile(r"^([A-Z][A-Z0-9_]{2,})\s*=\s*(.*)$")
K8S_ENV_NAME_RE = re.compile(r"\bname:\s*([A-Z][A-Z0-9_]{2,})\b")

DEFAULT_SCAN_GLOBS = [
    "**/*.env",
    "**/.env.*",
    "**/*.yaml",
    "**/*.yml",
    "**/*.json",
    "**/*.tf",
    "**/*.tfvars",
    "**/Dockerfile",
    "**/docker-compose*.yml",
]

SENSITIVE_HINTS = ("SECRET", "PASSWORD", "TOKEN", "KEY", "PASS", "PRIVATE", "CREDENTIAL", "API")


def run(cmd: List[str], cwd: Path | None = None) -> str:
    res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{res.stderr}")
    return res.stdout.strip()


def gh_headers():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Missing GH_TOKEN or GITHUB_TOKEN")
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}


def gh_get(url: str) -> List[dict]:
    import urllib.request

    req = urllib.request.Request(url, headers=gh_headers())
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    return data


def list_repos(user: str | None, org: str | None) -> List[str]:
    repos = []
    if org:
        page = 1
        while True:
            data = gh_get(f"{GITHUB_API}/orgs/{org}/repos?per_page=100&page={page}")
            if not data:
                break
            repos.extend([r["full_name"] for r in data])
            page += 1
    elif user:
        page = 1
        while True:
            data = gh_get(f"{GITHUB_API}/users/{user}/repos?per_page=100&page={page}")
            if not data:
                break
            repos.extend([r["full_name"] for r in data])
            page += 1
    return repos


def clone_or_pull(repo: str, dest: Path) -> Path:
    repo_dir = dest / repo.split("/")[-1]
    if repo_dir.exists() and (repo_dir / ".git").exists():
        run(["git", "pull"], cwd=repo_dir)
    else:
        run(["git", "clone", f"https://github.com/{repo}.git", str(repo_dir)])
    return repo_dir


def extract_env_keys_from_file(path: Path) -> Set[str]:
    keys: Set[str] = set()
    try:
        content = path.read_text(errors="ignore")
    except Exception:
        return keys

    for line in content.splitlines():
        m = ENV_LINE_RE.match(line.strip())
        if m:
            keys.add(m.group(1))

    # K8s env name patterns
    for m in K8S_ENV_NAME_RE.finditer(content):
        keys.add(m.group(1))

    return keys


def scan_repo(repo_dir: Path) -> Set[str]:
    keys: Set[str] = set()
    for glob in DEFAULT_SCAN_GLOBS:
        for path in repo_dir.glob(glob):
            if path.is_file():
                keys.update(extract_env_keys_from_file(path))
    return keys


def classify_keys(keys: Set[str]) -> Tuple[List[str], List[str]]:
    secrets = []
    configs = []
    for k in sorted(keys):
        if any(h in k for h in SENSITIVE_HINTS):
            secrets.append(k)
        else:
            configs.append(k)
    return configs, secrets


def write_env_example(repo_dir: Path, keys: List[str]) -> None:
    if not keys:
        return
    out = repo_dir / ".env.example"
    lines = [f"{k}=" for k in keys]
    out.write_text("\n".join(lines) + "\n")


def build_vault_seed(repo: str, env: str, base: str, secrets: List[str]) -> Dict[str, dict]:
    data = {k: "" for k in secrets}
    path = f"{base.rstrip('/')}/{env}/{repo}".replace("//", "/")
    return {path: data}


def write_vault_seed(dest: Path, seeds: Dict[str, dict]) -> None:
    out = dest / "vault_seed.json"
    out.write_text(json.dumps(seeds, indent=2) + "\n")


def vault_login(addr: str, user: str, password: str) -> str:
    import urllib.request
    url = f"{addr.rstrip('/')}/v1/auth/userpass/login/{user}"
    payload = json.dumps({"password": password}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    return data["auth"]["client_token"]


def vault_write(addr: str, token: str, path: str, data: dict) -> None:
    import urllib.request
    url = f"{addr.rstrip('/')}/v1/{path}"
    payload = json.dumps({"data": data}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "X-Vault-Token": token}, method="POST")
    with urllib.request.urlopen(req) as resp:
        resp.read()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--user", help="GitHub username")
    p.add_argument("--org", help="GitHub org")
    p.add_argument("--repos", nargs="*", help="Specific repos (full_name)")
    p.add_argument("--dest", default="./repos", help="Clone destination")
    p.add_argument("--env", default="staging")
    p.add_argument("--vault-base", default="kv/temitayo")
    p.add_argument("--write-vault", action="store_true")
    p.add_argument("--vault-addr")
    p.add_argument("--vault-user")
    p.add_argument("--vault-pass")
    args = p.parse_args()

    dest = Path(args.dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    repos = args.repos or list_repos(args.user, args.org)
    if not repos:
        raise SystemExit("No repos found")

    vault_token = None
    if args.write_vault:
        if not (args.vault_addr and args.vault_user and args.vault_pass):
            raise SystemExit("Vault write requested but missing vault creds")
        vault_token = vault_login(args.vault_addr, args.vault_user, args.vault_pass)

    combined_seeds: Dict[str, dict] = {}
    report = []

    for repo in repos:
        repo_dir = clone_or_pull(repo, dest)
        keys = scan_repo(repo_dir)
        configs, secrets = classify_keys(keys)

        write_env_example(repo_dir, keys)

        seed = build_vault_seed(repo, args.env, args.vault_base, secrets)
        combined_seeds.update(seed)

        if args.write_vault and vault_token:
            for path, data in seed.items():
                vault_write(args.vault_addr, vault_token, path, data)

        report.append({
            "repo": repo,
            "configs": configs,
            "secrets": secrets,
            "env_example": str(repo_dir / ".env.example")
        })

    write_vault_seed(dest, combined_seeds)
    (dest / "scan_report.json").write_text(json.dumps(report, indent=2) + "\n")

    print(f"Scanned {len(repos)} repos. Results in {dest}/scan_report.json")


if __name__ == "__main__":
    main()
