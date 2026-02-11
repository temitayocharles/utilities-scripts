#!/usr/bin/env python3
"""Seed Vault KV v2 from .env.example + optional .env values.

Requires:
- vault CLI in PATH
- VAULT_ADDR set

Usage:
  python3 seed_vault_from_env.py --env staging --repo fintech-user-service --service api \
    --env-example /path/to/.env.example --env-file /path/to/.env \
    --base-path kv/temitayo --write
"""

import argparse
import os
import subprocess
from pathlib import Path


def parse_env_file(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def vault_login(username: str, password: str) -> None:
    if not username or not password:
        return
    subprocess.run(
        ["vault", "login", "-method=userpass", f"username={username}", f"password={password}"],
        check=True,
    )


def vault_put(path: str, values: dict) -> None:
    if not values:
        return
    args = ["vault", "kv", "put", path]
    for k, v in values.items():
        args.append(f"{k}={v}")
    subprocess.run(args, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, help="Environment name, e.g. staging")
    parser.add_argument("--repo", required=True, help="Repo name")
    parser.add_argument("--service", required=True, help="Service name")
    parser.add_argument("--env-example", required=True, help="Path to .env.example")
    parser.add_argument("--env-file", required=False, help="Path to .env with values")
    parser.add_argument("--base-path", default="kv/temitayo", help="Vault base path")
    parser.add_argument("--vault-username", default=os.getenv("VAULT_USERNAME", ""))
    parser.add_argument("--vault-password", default=os.getenv("VAULT_PASSWORD", ""))
    parser.add_argument("--write", action="store_true", help="Write to Vault")
    args = parser.parse_args()

    env_example = Path(args.env_example)
    env_values = parse_env_file(Path(args.env_file)) if args.env_file else {}

    # keys from .env.example
    keys = parse_env_file(env_example).keys()
    payload = {}
    for key in keys:
        val = env_values.get(key) or os.getenv(key, "")
        if val:
            payload[key] = val

    vault_path = f"{args.base_path}/{args.env}/{args.repo}/{args.service}"

    print(f"Vault path: {vault_path}")
    print(f"Keys detected: {len(list(keys))}")
    print(f"Keys with values: {len(payload)}")

    if args.write:
        vault_login(args.vault_username, args.vault_password)
        vault_put(vault_path, payload)
        print("Write complete")
    else:
        print("Dry run only. Use --write to write to Vault.")


if __name__ == "__main__":
    main()
