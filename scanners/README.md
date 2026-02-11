# Scanners

## GitHub Repo Scanner
Scans repositories for env vars and generates `.env.example` + Vault seed templates.

### Usage
```bash
export GH_TOKEN=...  # or GITHUB_TOKEN
python3 github_repo_scanner.py --user temitayocharles --dest ./repos --env staging --vault-base kv/temitayo
```

### Optional Vault Write
```bash
python3 github_repo_scanner.py \
  --user temitayocharles \
  --dest ./repos \
  --env staging \
  --vault-base kv/temitayo \
  --write-vault \
  --vault-addr http://vault.vault.svc:8200 \
  --vault-user temitayocharles \
  --vault-pass 1221
```

Outputs:
- `repos/<repo>/.env.example`
- `repos/vault_seed.json`
- `repos/scan_report.json`
