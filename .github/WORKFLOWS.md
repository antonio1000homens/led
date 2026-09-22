# GitHub Actions ownership

The LED repository contains several independently changing areas. Workflows are
deliberately path-scoped so a change only runs the checks or production action
that owns that area.

| Area | Primary paths | Pull request behaviour | Push to `master` |
| --- | --- | --- | --- |
| Enclosure / mechanical | `hardware/enclosure/**` | Regenerate/compare STLs, render assembly/SVG entrypoints, validate meshes and interfaces | Repeat the same validation; no deployment |
| CircuitPython / MatrixPortal | Board runtime files in the repository root plus `hardware/matrixportal/**` | Compile board-compatible Python and run firmware/renderer tests | Repeat validation; firmware is not remotely deployed |
| Backend / AWS | Lambda/backend modules, `infrastructure/led-stack.yaml`, production backend helpers | Run the backend test suite | Test, package Lambda and deploy the CloudFormation backend |
| Cloudflare / DNS | `scripts/cloudflare_dns.py`, `scripts/configure-cloudflare-dns.sh`, `scripts/request-acm-certificate.sh` | Validate helper syntax and Cloudflare infrastructure invariants | Reconcile ACM validation DNS and the LED CloudFront hostname without repackaging Lambda |
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

Cloudflare-only helper changes use `Cloudflare / DNS Reconcile` rather than
the full backend deployment. The workflow:

1. validates the Cloudflare and ACM helper scripts;
2. assumes the existing LED deployment role with GitHub OIDC;
3. loads only the Cloudflare deployment token from SSM;
4. requests or reuses the ACM certificate;
5. reconciles the ACM validation DNS record;
6. reads the existing CloudFront distribution domain from the deployed stack;
7. reconciles the `led.alf-broadcast.co.uk` hostname.

The backend deployment still performs the same DNS reconciliation when a
backend deployment genuinely occurs. Both workflows use the same
`led-production` concurrency group so AWS/Cloudflare/static production
mutations cannot race each other.

## Production versus validation-only inputs

The production backend push trigger is intentionally narrower than its pull
request trigger:

- `infrastructure/led-stack.yaml` is an automatic production input.
- `infrastructure/bootstrap.yaml` is bootstrap/manual infrastructure and does
  not trigger a production backend deploy.
- bootstrap/migration helpers are validated on pull requests but do not trigger
  production changes merely because they are merged.
- tests and documentation never trigger a production deploy on their own.

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
