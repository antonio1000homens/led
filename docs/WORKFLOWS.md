# GitHub Actions ownership

The LED repository contains several independently changing areas. Workflows are
deliberately path-scoped so a change only runs the checks or production action
that owns that area.

| Area | Primary paths | Pull request behaviour | Push to `master` |
| --- | --- | --- | --- |
| Enclosure / mechanical | `hardware/enclosure/**` | Run the consolidated fast enclosure validator on every relevant PR. Use Windsor Slicer for explicit full H2D validation or slicing of manifest-declared models. | Repeat fast validation; no automatic full slicing or deployment |
| CircuitPython / MatrixPortal | `code.py`, `hardware/matrixportal/**`, and `shared/**` | Compile board-compatible Python and run firmware/renderer tests | Repeat validation; no automatic firmware deployment. Provisioned boards may be updated manually over trusted-LAN Web Workflow; CircuitPython UF2 remains USB-only |
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

## Concurrency and superseded runs

Validation workflows cancel stale pull-request runs when a newer commit is pushed to the same PR. They use the pull-request head ref as the concurrency key and fall back to the unique workflow run ID for non-PR events, so a production or manually dispatched run is never cancelled merely because a newer PR validation starts.

The enclosure validator uses the same principle with its existing branch/PR-scoped concurrency group because mechanical validation is comparatively expensive.

Production mutations from Backend, Cloudflare and Static Web all share the `led-production` concurrency group. They use `queue: max` with `cancel-in-progress: false`: only one production mutation runs at a time, but later legitimate deployments wait in FIFO order instead of replacing an older pending production job.

Workflow YAML files remain PR validation inputs, but are not production push inputs for Backend, Cloudflare or Static Web. Merging a workflow-only change therefore does not deploy unchanged application/infrastructure content. CircuitPython and Enclosure likewise do not repeat their validation solely because their own workflow YAML changed on `master`.

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
The installer writes `code.py` last and stages the managed `boot.py`, which
keeps Wi-Fi off until the application applies a 10-second delay and 8 dBm limit.
Reserved `CIRCUITPY_WIFI_SSID/PASSWORD` keys must first be renamed to the custom
`WIFI_SSID/PASSWORD` keys; the installer rejects early automatic connection
configuration. Power-cycle after installation. Browser maintenance remains
disabled with these custom credentials.

Lambda packaging follows the same principle: source lives under `backend/`
and `shared/`, while `scripts/package-lambda.sh` flattens the selected
runtime modules into the deployment ZIP so existing Lambda import and handler
names remain unchanged.


## Enclosure validation architecture

`.github/workflows/generate-enclosure-stls.yml` contains environment setup plus
a call to:

`hardware/enclosure/scripts/validate_enclosure.py`

Issue #133 commits the repository to one canonical mechanical architecture: the
modular hinged direct-mount enclosure. Legacy non-hinged backplanes/lids and
earlier hinge prototype directories are not retained as alternate printable
designs.

The canonical OpenSCAD source is
`hardware/enclosure/direct_mount_enclosure.scad`. Thin printable
wrappers live under `hardware/enclosure/parts/`.

CI regenerates all six current printable parts on demand. Before the broader
mechanical checks run, `hardware/enclosure/scripts/verify_canonical_stls.py`
compares each generated mesh with the versioned STL under
`hardware/enclosure/stl/`. The comparison normalizes triangle and vertex
ordering so harmless OpenSCAD facet-order changes do not fail CI, while missing,
extra, or geometrically stale canonical STLs do. CI remains read-only: generated
validation copies are exposed as workflow artifacts rather than committed by
Actions.

The remaining enclosure validation checks mesh health, a coarse
floating-layer/island proxy, the base/backplane rail intersection,
representative hinge sweep clearances, and open/closed assembly previews.

Full Bambu Studio validation and slicing are provided by Windsor Slicer using
only the canonical models declared in `.windsor-slicer.yaml`.

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
