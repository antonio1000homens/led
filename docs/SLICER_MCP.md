# Slicer MCP

The LED slicer MCP exposes the repository's proven Bambu Studio slicing
pipeline to MCP-capable clients without duplicating slicer logic.

It is the next layer above:

```text
scripts/slicer/slice-stl.sh
        |
        +-- GitHub Actions full slicer validation
        +-- Codespaces/manual slicing
        +-- Slicer MCP
```

The MCP **does not start a printer job** in this phase.

## Runtime

The server uses the official MCP Python SDK v2 and supports:

- `stdio` — default; suitable for a local coding agent or an MCP client
  running inside a Codespace;
- `streamable-http` — suitable for interactive Codespaces experiments.

Install dependencies:

```bash
python3 -m pip install -r mcp_servers/slicer/requirements.txt
```

Start in stdio mode:

```bash
bash scripts/run-slicer-mcp.sh
```

Start Streamable HTTP:

```bash
SLICER_MCP_TRANSPORT=streamable-http \
SLICER_MCP_HOST=0.0.0.0 \
SLICER_MCP_PORT=8000 \
bash scripts/run-slicer-mcp.sh
```

The HTTP endpoint is then:

```text
http://localhost:8000/mcp
```

The server is stateless in HTTP mode.

## Tools

### `slicer_capabilities`

Reports:

- the Bambu Studio provider;
- executable/profile discovery;
- the pinned/default profile choices;
- allowed repository roots;
- whether printer handoff is available;
- the remote-Cloudflare endpoint posture.

No credential values are returned.

### `slicer_inspect_model`

Inspects one STL/3MF and returns basic mesh metadata including dimensions,
vertices/faces and watertightness.

Only these roots are allowed:

```text
hardware/
artifacts/slicer-input/
```

Path traversal or arbitrary filesystem access is rejected.

### `slicer_list_profiles`

Lists H2D-oriented Bambu machine/process profiles and installed filament
profiles from the Bambu Studio profile tree.

### `slicer_slice`

Runs the same `scripts/slicer/slice-stl.sh` implementation used by GitHub
Actions.

Defaults remain:

```text
machine:  Bambu Lab H2D 0.4 nozzle
process:  0.20mm Standard @BBL H2D
filament: Bambu PLA Basic @BBL H2D
orient:   false
```

Keeping `orient=false` by default is intentional: automatic orientation can
hide a floating/cantilever problem in the CAD's intended print orientation.

Outputs remain below:

```text
artifacts/slicer/
```

Raw Bambu stdout/stderr is not returned in the MCP response. The shared
slicer log is retained in the generated artifact directory instead.

### `slicer_validate_for_print`

Runs a real slice and returns the same normalized fatal categories used in CI,
plus `ready_for_print`.

### `slicer_prepare_print`

Produces a validated pre-sliced 3MF and metadata for a later printer-provider
handoff.

It always returns:

```json
{
  "print_started": false,
  "printer_handoff_available": false
}
```

until the explicitly confirmed printer integration phase is implemented.

## Codespaces

The devcontainer installs MCP dependencies and forwards port 8000 for
interactive testing.

Examples:

```bash
# stdio
bash scripts/run-slicer-mcp.sh

# HTTP
SLICER_MCP_TRANSPORT=streamable-http \
SLICER_MCP_HOST=0.0.0.0 \
bash scripts/run-slicer-mcp.sh
```

Port 8000 is not made public automatically. Do not expose an unauthenticated
MCP server as a permanent public Codespaces port.

## Cloudflare / remote endpoint decision

### No new endpoint is required for this phase

The current implementation does **not** change Cloudflare DNS, CloudFront,
API Gateway, or `backend/config_api.py`.

That is deliberate.

The existing protected control API:

```text
/api/control/v1/*
```

is an LED runtime-configuration plane backed by a short-running Lambda.
It reads/writes feed configuration and invokes the publisher. It is not an
appropriate transport for an MCP service that orchestrates GitHub Actions,
slicer artifacts or later printer workflows.

Codespaces and stdio MCP therefore require no new Cloudflare endpoint.

### A permanent cloud-AI MCP will require a dedicated endpoint

If ChatGPT or another cloud AI must connect directly to the slicer MCP without
an active Codespace/local host, deploy a **separate** protected MCP endpoint.

Reserve:

```text
https://led.alf-broadcast.co.uk/mcp/slicer
```

or, if operational separation is preferable:

```text
https://slicer-mcp.alf-broadcast.co.uk/mcp
```

Requirements for that future endpoint:

1. Streamable HTTP only; do not use the legacy SSE transport.
2. Stateless MCP requests where possible.
3. Cloudflare Access authentication for machine clients.
4. A dedicated origin/runtime; do not route it into `led-control-api`.
5. No Bambu LAN access code in the edge runtime.
6. The edge/orchestrator should trigger/query GitHub Actions and return job
   status/artifact references rather than perform CPU-heavy slicing itself.
7. A dedicated repo-scoped GitHub App or similarly narrow credential stored in
   an appropriate secret store; do not reuse the Cloudflare deployment token.
8. Cache disabled for the MCP path.
9. Explicit request/body/time limits and audit logging.
10. Printer submission remains a separate explicitly confirmed operation.

A Cloudflare Worker could be a suitable lightweight orchestration origin, but
that would introduce the repository's first Worker deployment and its own
GitHub credential lifecycle. It should therefore be implemented as a separate
phase rather than hidden inside the current DNS deployment workflow.

## Bambu printer provider

The planned printer phase should reuse the existing
`@rowbotik/bambu-printer-mcp` implementation rather than duplicating MQTT or
FTPS.

Its recommended H2-family path is already compatible with this architecture:

```text
Bambu Studio CLI
     |
     v
pre-sliced .gcode.3mf
     |
     v
bambu-printer-mcp
     |
     v
AMS validation / upload / explicit print
```

The external printer MCP currently requires LAN reachability for printer
operations. A Codespace/GitHub-hosted runner therefore cannot directly reach
the home H2D unless a private-network path is added. Cloud-only printer
submission, if pursued, must remain separate from the validated LAN handoff.

## Security

- No arbitrary shell command tool is exposed.
- Input paths are allow-listed.
- Output paths are confined under `artifacts/slicer/`.
- MCP callers choose profile names/bed/orientation, not executable paths.
- Captured slicer process output is not reflected directly to the client.
- No Bambu, AWS or Cloudflare credential is needed for inspect/slice/validate.
- There is no `slicer_print` tool in this phase.

## Tests

Run:

```bash
python3 -m unittest discover -s tests -p 'test_slicer_mcp.py' -v
```

The tests cover:

- expected MCP tool registration;
- allow-listed filesystem access;
- STL inspection;
- shared-script invocation;
- structured result handling;
- timeout handling;
- proof that prepare-print never starts a printer.
