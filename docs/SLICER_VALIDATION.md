# Cloud slicer validation

This repository supports remote enclosure development without requiring Bambu
Studio to be opened on the home Mac for every iteration.

The design deliberately separates the cheap geometry gate from the expensive
real-slicer gate.

## Execution modes

### 1. Fast enclosure validation

`.github/workflows/generate-enclosure-stls.yml` remains the normal required
mechanical check. It runs on every relevant enclosure PR and does not install
Bambu Studio.

Run it locally/Codespaces with:

```bash
python3 hardware/enclosure/direct-mount/scripts/validate_enclosure.py
```

### 2. Full H2D slicer validation

`.github/workflows/slicer-validation.yml` invokes the real Bambu Studio CLI
with the stock H2D 0.4 mm machine profile, 0.20 mm Standard process profile and
Bambu PLA Basic filament profile.

It is intentionally opt-in while runner setup/slicing cost is measured.

Use either:

- add the PR label `slicer-validation`; or
- run **Enclosure / Slicer validation** manually and provide an STL/3MF path.

PR-triggered runs process at most four selected models by default. If a change
would select more, the workflow fails early and asks for an explicit manual
target instead of consuming a large amount of Actions time.

When the slicer workflow/scripts/devcontainer themselves change and no printable
model changed, an explicitly labelled PR slices the small tracked
`09_centre_boss_desk_stand_PRINT_3.stl` as a self-test. This proves the real
Bambu CLI/profile path without turning full slicing on for ordinary PRs.

Successful runs upload `artifacts/slicer/` for seven days, including:

- the sliced `*.sliced.3mf`;
- the flattened machine/process/filament profiles used;
- the full slicer log;
- `result.json` with normalized diagnostics.

No Bambu Cloud token, printer access code or AWS credential is required for
validation-only slicing.

## Floating-region behaviour

The slicer wrapper preserves the model orientation by default. This is
important: automatic orientation could hide an unsupported/floating region that
exists in the intended print orientation.

The log classifier currently normalizes fatal conditions into:

- `FLOATING_REGION`
- `EMPTY_LAYERS`
- `OUTSIDE_BUILD_VOLUME`
- `PROFILE_MISMATCH`
- `INVALID_GEOMETRY`
- `SLICER_ERROR`
- `MISSING_OUTPUT`

If Bambu Studio emits a floating/floating-cantilever diagnostic while still
returning success, the wrapper still fails the validation.

## Codespaces

The repository contains `.devcontainer/` so the same validation can be run
interactively from a GitHub Codespace.

After the Codespace is created:

```bash
bash scripts/slicer/install-bambu-studio.sh
bash scripts/slicer/slice-stl.sh \
  hardware/enclosure/direct-mount/hinge-prototype-v2/stl/02_middle_stationary_enclosure_HINGE_TEST.stl
```

The Codespace and Actions workflow use the same scripts; workflow YAML does not
contain a separate slicing implementation.

For an orientation experiment:

```bash
SLICER_ORIENT=1 bash scripts/slicer/slice-stl.sh <path-to-model.stl>
```

Outputs are written to `artifacts/slicer/<model>/`.

## Pinned slicer version

The initial implementation pins Bambu Studio to:

```text
v02.08.02.61
```

Override it for an experiment with:

```bash
BAMBU_STUDIO_VERSION=<release-tag> \
  bash scripts/slicer/install-bambu-studio.sh
```

Do not casually float CI to "latest": slicer CLI behaviour and warning text are
part of the validation contract and should be upgraded deliberately.

## Profiles

Bambu's CLI requires full settings rather than the inherited JSON fragments
bundled under `resources/profiles/BBL`.

`scripts/slicer/flatten-bambu-profile.py` resolves the bundled `inherits`
and `include` chains and writes standalone copies under the slicer artifact
directory.

Defaults:

```text
machine:  Bambu Lab H2D 0.4 nozzle
process:  0.20mm Standard @BBL H2D
filament: Bambu PLA Basic @BBL H2D
```

They can be overridden for experimentation:

```bash
SLICER_MACHINE_PROFILE='...' \
SLICER_PROCESS_PROFILE='...' \
SLICER_FILAMENT_PROFILE='...' \
bash scripts/slicer/slice-stl.sh model.stl
```

## Runtime policy

Keep the full slicer job opt-in until representative runs have been measured.

The Action summary records:

- Bambu Studio setup/download time;
- total slicing phase time;
- per-model slice time;
- selected model count.

If typical jobs remain inexpensive, selected enclosure paths can later enable
automatic full slicing. If setup or slice time is substantial, the intended
long-term policy is still valid:

```text
required PR check = fast enclosure validation
optional PR check = real Bambu slicer validation
interactive debug = Codespaces
print preparation = explicit/manual
```

## Future MCP integration

Issue #114 will place MCP tools on top of these scripts. MCP must call the same
`slice-stl.sh`/classification path rather than implementing another slicer
pipeline. Printer/cloud submission remains a later, separately confirmed
operation.
