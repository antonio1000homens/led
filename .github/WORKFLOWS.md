# GitHub Actions ownership

The LED repository contains several independently changing areas. Workflows are
deliberately path-scoped so a change only runs the checks or production action
that owns that area.

| Area | Primary paths | Pull request behaviour | Push to `master` |
| --- | --- | --- | --- |
| Enclosure / mechanical | `hardware/enclosure/**` | Regenerate/compare STLs, render assembly/SVG entrypoints, validate meshes and interfaces | Repeat the same validation; no deployment |
| CircuitPython / MatrixPortal | Board runtime files in the repository root plus `hardware/matrixportal/**` | Compile board-compatible Python and run firmware/renderer tests | Repeat validation; firmware is not remotely deployed |
| Backend / AWS / Cloudflare | Lambda/backend modules, `infrastructure/led-stack.yaml`, production deployment helpers | Run the backend test suite | Test, package Lambda, deploy CloudFormation, reconcile ACM/Cloudflare DNS and publish the backend |
| Static web | `simulator/**`, `scripts/deploy-static.sh` | Run simulator/admin regression tests | Upload simulator/admin assets and invalidate CloudFront |
| Bootstrap/manual tooling | `infrastructure/bootstrap.yaml`, bootstrap/migration scripts, local deployment helpers | Backend validation where applicable | No automatic production mutation |
| Documentation | Markdown and other documentation-only changes | No workflow unless a workflow file is also changed | No deployment |

## Shared files

Some root modules are intentionally shared while the source tree remains flat:

- `formatting.py` is used by both the MatrixPortal renderer and backend publisher.
- `fixtures.py` is used by both firmware fixture mode and the local/backend server.

Changes to these shared files therefore trigger both CircuitPython validation
and the backend workflow. That overlap is intentional.

## Cloudflare ownership

Cloudflare is part of the production backend deployment, not a firmware or
enclosure concern. Changes to:

- `scripts/cloudflare_dns.py`
- `scripts/configure-cloudflare-dns.sh`
- `scripts/request-acm-certificate.sh`

trigger the backend workflow. The backend deployment retains the existing
Windsor account checks and reconciles the ACM validation record and LED
hostname as part of deployment.

## Repository layout direction

The current repository keeps CircuitPython and backend Python modules at the
root because the MatrixPortal copy workflow and Lambda packaging currently
expect those paths. Do not move them casually: a folder move would require
coordinated updates to MatrixPortal copy instructions, imports, unit tests and
`scripts/package-lambda.sh`.

A future structural cleanup can move code toward:

```text
firmware/
backend/
web/
hardware/
infrastructure/
scripts/
tests/
```

The workflow ownership above should remain the contract during that migration:
moving files should update path filters without changing which class of change
causes a production deployment.
