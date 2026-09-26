# Cloud slicer POC

This POC makes the existing Bambu Studio slicer MCP usable from a web AI client without a local Mac or VS Code session.

## Architecture

```text
Codex web / ChatGPT
  |
  +-- GitHub plugin -> source edits / commit / PR
  |
  +-- LED Cloud Slicer MCP
        |
        v
  slicer.alf-broadcast.co.uk
        |
  Cloudflare Worker
        | starts/resumes
        v
  dedicated GitHub Codespace
        |
        +-- isolated git worktree at exact commit
        +-- OpenSCAD generation
        +-- Bambu Studio H2D slicing
        +-- result.json / slicer.log / sliced 3MF
```

Printer submission is deliberately out of scope.

## MCP workflow

1. Use GitHub to commit the source change and obtain the full commit SHA.
2. Call `slicer_prepare_workspace(repository, commit)`.
3. Call `slicer_generate_model(workspace, source_path, output_name)` for an enclosure SCAD entrypoint.
4. Call `slicer_inspect_model(path)` if required.
5. Call `slicer_validate_for_print(path, workspace=...)` or `slicer_prepare_print(...)`.
6. Use `slicer_get_diagnostics(log_path)` only when structured categories are insufficient.
7. Use `slicer_get_artifact(path, include_base64=true)` to retrieve a bounded print-ready 3MF.

`workspace` is the first 12 characters of the immutable commit SHA. Generated models are written only below `artifacts/slicer-input/<workspace>/`, which keeps the existing slicer path allowlist intact.

## Codespace

The devcontainer now installs the pinned Bambu Studio build during creation and starts the slicer MCP on port 8000 whenever the Codespace resumes.

Create a dedicated reusable Codespace for `antonio1000homens/led`. Configure this Codespaces secret before starting it:

```text
SLICER_MCP_BEARER_TOKEN=<random origin token>
```

The startup script refuses to expose the cloud origin when the token is absent.

The MCP runs with:

```text
SLICER_MCP_TRANSPORT=streamable-http
SLICER_MCP_HOST=0.0.0.0
SLICER_MCP_PORT=8000
SLICER_MCP_PATH=/mcp
SLICER_MCP_RESOURCE_URL=https://slicer.alf-broadcast.co.uk/mcp
```

Health is available at `/health` and requires the same origin bearer token.

## Cloudflare Worker

The Worker lives in `cloud/slicer-worker/` and is intentionally thin. It does not run Bambu Studio.

It:

- verifies a client bearer token;
- queries the configured user Codespace through GitHub's Codespaces REST API;
- starts the Codespace when stopped;
- waits for a bounded period for the Codespace to become available;
- marks only port 8000 public;
- verifies `/health` using a separate origin bearer token;
- replaces the client credential with the origin credential before proxying MCP traffic.

The public Codespaces port is therefore still protected by the slicer MCP itself. Knowing the `app.github.dev` URL is not sufficient to call the tools.

### Worker configuration

Set the Worker variable:

```text
CODESPACE_NAME=<dedicated-codespace-name>
CODESPACE_FORWARDING_DOMAIN=app.github.dev
```

The forwarding domain is configurable because GitHub documents that it may change.

Set these Worker secrets:

```text
GITHUB_CODESPACES_TOKEN=<narrow user token able to read/start that Codespace and change port visibility>
MCP_CLIENT_TOKEN=<random token used by the Codex/ChatGPT plugin>
ORIGIN_BEARER_TOKEN=<same value as the Codespaces SLICER_MCP_BEARER_TOKEN>
```

Do not reuse the Cloudflare deployment token as `GITHUB_CODESPACES_TOKEN`.

Deploy from `cloud/slicer-worker` with Wrangler after the secrets are configured. The checked-in Worker Custom Domain is:

```text
slicer.alf-broadcast.co.uk
```

Cloudflare creates/manages the DNS record for this Custom Domain; do not create a separate origin CNAME for it.

## Security boundaries

- Repository is fixed to `antonio1000homens/led` by default.
- Workspace preparation accepts only a full 40-character commit SHA.
- Workspaces are detached worktrees outside the main checkout.
- SCAD generation is limited to `hardware/enclosure/`.
- Generated STL output is limited to `artifacts/slicer-input/<workspace>/`.
- Slicing remains constrained by the existing `hardware/` / `artifacts/slicer-input/` allowlist.
- Artifact retrieval is limited to non-empty `.3mf` files below `artifacts/slicer/`.
- Inline artifact transfer defaults to a 10 MiB maximum (`SLICER_MCP_MAX_ARTIFACT_BYTES`).
- Diagnostic output is bounded and bearer Authorization lines are redacted.
- No printer-control credentials are required.

## First live verification

Use a real enclosure wrapper SCAD and a commit from a test branch. The minimum success sequence is:

```text
slicer_prepare_workspace
 -> slicer_generate_model
 -> slicer_validate_for_print
 -> slicer_get_artifact
```

Record cold Codespace startup time, warm request latency, STL generation time, Bambu slice time and generated 3MF size on issue #118.

## Known POC limitation

The web-client credential is currently a static bearer token. If the target Codex/ChatGPT plugin surface requires OAuth rather than a configured bearer secret, replace only the Worker-facing authentication layer; the Codespace origin token and slicer implementation do not need to change.
