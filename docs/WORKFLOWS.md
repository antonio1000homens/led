# GitHub Actions ownership

The LED repository contains several independently changing areas. Workflows are
deliberately path-scoped so a change only runs the checks or production action
that owns that area.

| Area | Primary paths | Pull request behaviour | Push to `master` |
| --- | --- | --- | --- |
| Enclosure / mechanical | `hardware/enclosure/**` | Run the consolidated enclosure validator: render each current production STL once, compare checked-in meshes, render assembly/SVG views, validate hinge-v2 print geometry/floating-layer islands, and validate meshes/interfaces | Repeat the same validation; no deployment |
| CircuitPython / MatrixPortal | `code.py`, `hardware/matrixportal/**`, and `shared/**` | Compile board-compatible Python and run firmware/renderer tests | Repeat validation; firmware is not remotely deployed |
| Backend / AWS | `backend/**`, `shared/**`, `infrastructure/led-stack.yaml`, production backend helpers | Run the backend test suite | Test, package Lambda and deploy the CloudFormation backend |
| Cloudflare / DNS | `scripts/cloudflare_dns.py`, `scripts/configure-cloudflare-dns.sh`, `scripts/request-acm-certificate.sh` | Validate helper syntax and Cloudflare infrastructure invariants | Reconcile ACM validation DNS and the LED CloudFront hostname without repackaging Lambda |
| Static web | `simulator/**`, `scripts/deploy-static.sh` | Run simulator/admin regression tests | Upload simulator/admin assets and invalidate CloudFront |
| Bootstrap/manual tooling | `infrastructure/bootstrap.yaml`, bootstrap/migration scripts, local deployment helpers | Backend validation where applicable | No automatic production mutation |
| Documentation | Markdown and other documentation-only changes | No workflow unless a workflow file is also changed | No deployment |

## Shared files

Cross-runtime modules live under `shared/`:

- `shared/formatting.py` is used by both the MatrixPortal renderer and backend publisher.
- `shared/fixtures.py` is used by both firmware fixture mode and the local/backend server.

Changes under `shared/**` therefore trigger both CircuitPython validation and
the backend workflow. That overlap is intentional.

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

## Repository layout

Python sources are grouped by runtime ownership:

```text
code.py                  # Wokwi/CircuitPython entrypoint only
hardware/matrixportal/firmware/  # MatrixPortal implementation modules
backend/                 # CPython local server and Lambda modules
shared/                  # modules imported by both runtimes
simulator/
hardware/
infrastructure/
scripts/
tests/
```

Wokwi requires `code.py` at the CircuitPython project root, so that single
entrypoint intentionally remains there. It adds `hardware/matrixportal/firmware/` and `shared/`
to the import path for repository/Wokwi execution. `scripts/stage-firmware.sh`
flattens those modules into `.build/circuitpy/`, and
`scripts/install-firmware.sh` copies the staged application onto a mounted
`CIRCUITPY` drive without removing `settings_local.py` or `lib/`.

Lambda packaging follows the same principle: source lives under `backend/`
and `shared/`, while `scripts/package-lambda.sh` flattens the selected
runtime modules into the deployment ZIP so existing Lambda import and handler
names remain unchanged.


## Enclosure validation architecture

`.github/workflows/generate-enclosure-stls.yml` intentionally contains only environment setup plus a call to:

`hardware/enclosure/direct-mount/scripts/validate_enclosure.py`

That script is the single orchestration point for current mechanical CI. Production printable wrapper SCADs are rendered **once** per run and compared with their checked-in manufacturing STLs; the same run also renders assembly/reference views, validates hinge prototype v2 and the retained hinge-version meshes, then runs mesh/interface validation.

Hinge-v2 validation includes a coarse voxel/layer **floating-island proxy**. It rejects an elevated XY slice component that appears without nearby material in the preceding slice. This targets detached starts such as the roof cantilever found by Bambu Studio, but it is not a replacement for final slicing in Bambu Studio.

## Workflow-generated commits and approval loops

Pull-request workflows should be validation-only by default. Generated files
should normally be produced locally or exposed as workflow artifacts rather
than committed back to an open pull-request branch.

If a temporary or manually dispatched workflow genuinely needs to commit
generated files back to a branch, its commit message **must** contain
`[skip ci]`, for example:

```text
Regenerate enclosure STLs [skip ci]
```

This prevents the resulting `github-actions[bot]` commit from creating a new
`pull_request` synchronization run. Without the skip marker, GitHub can treat
the bot-authored update as a separate contributor-triggered run and leave it in
`action_required` awaiting maintainer approval, even when the repository has
only one human collaborator.

Do not solve this by weakening repository-wide Actions approval settings.
Validation workflows should keep `contents: read`; any temporary generator
that needs `contents: write` should be manually scoped, use `[skip ci]` for
its generated commit, and be removed when it is no longer needed.

`.github/workflows/workflow-policy.yml` enforces the skip-marker rule for any
checked-in workflow containing a direct `git commit` command.
