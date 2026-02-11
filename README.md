# Utilities Scripts

Central toolbox for platform operations: scanning, backups, vault, CI helpers, and infra utilities.

## Structure
- `scanners/`: GitHub repo scanning + env/secret extraction
- `vault/`: vault init/auth/seed helpers
- `backups/`: backup/restore scripts
- `k8s/`: cluster utilities
- `image/`: build/push/sign helpers
- `security/`: gitleaks/trivy/snyk wrappers
- `ci/`: CI helper scripts
- `tests/`: unit tests for scripts
- `docs/`: usage/runbooks
- `scripts/`: shared shell/python helpers

## Usage
Each tool has its own README in its folder.

## Dependency Graph
```
utilities-scripts
  -> configurations (scan and generate .env.example)
  -> Vault (seed secrets)
  -> shared-workflows (CI helpers and scanners)
  -> platform-gitops (optional bootstrap helpers)
```
