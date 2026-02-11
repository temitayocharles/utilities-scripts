# Platform Utilities

This repository hosts operational utilities and scanners for platform engineering.

## Guidelines
- All secrets should be written to Vault; `.env.example` is the only env file committed.
- ConfigMaps live in the `configurations` repo; values should be non‑secret.

## Contents
- `scanners/` GitHub scanners and env extraction
- `vault/` auth/init/seed utilities
- `backups/` backup helpers
- `k8s/` cluster scripts
- `image/` build/push helpers
- `security/` gitleaks/trivy/snyk wrappers
- `ci/` pipeline helpers

## Quick Start
```bash
export GH_TOKEN=...
python3 scanners/github_repo_scanner.py --user temitayocharles --dest ./repos --env staging --vault-base kv/temitayo
```
