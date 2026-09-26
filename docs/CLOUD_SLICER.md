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

The checked-in Wrangler config sets the dedicated Codespace name and its port. The repository variable `CODESPACE_NAME` must match it; the deployment workflow checks this before deploying.

Run **Actions → Cloud Slicer / Deploy Worker** or let it run when Worker files change on `master`. It uses the dedicated `led-github-cloud-slicer-deploy-role` GitHub OIDC role, which can read only `/led/cloud-slicer/*` SSM parameters. The workflow deploys the Worker and pipes the four required `SecureString` values from SSM directly to Wrangler. Secret values are masked and never written to workflow logs or files.

Create these parameters in `eu-west-2`:

```text
/led/cloud-slicer/github-codespaces-token
/led/cloud-slicer/mcp-client-token
/led/cloud-slicer/origin-bearer-token
/led/cloud-slicer/cloudflare-api-token
```

The GitHub token must be able to inspect and start the dedicated Codespace and make port 8000 public. For a fine-grained token, grant Codespaces metadata read and Codespaces lifecycle admin write for the `led` repository, plus the Codespaces port visibility operation. A classic personal access token needs the `codespace` scope.

For the first Worker creation, the Cloudflare token needs Workers Admin on the Windsor account and Workers Routes Write on the `alf-broadcast.co.uk` zone. The Worker and custom domain have now been created. For ongoing workflow deploys, use a token scoped to Editor for the `led-cloud-slicer` Worker; keep Workers Routes Write only if a deployment will change the custom domain. Put the active token at `/led/cloud-slicer/cloudflare-api-token`. Rotate tokens by updating their SSM parameter and rerunning the workflow. The Worker receives these secrets:

```text
GITHUB_CODESPACES_TOKEN=<narrow user token able to read/start that Codespace and change port visibility>
MCP_CLIENT_TOKEN=<random token used by the Codex/ChatGPT plugin>
ORIGIN_BEARER_TOKEN=<same value as the Codespaces SLICER_MCP_BEARER_TOKEN>
```

Do not reuse the Cloudflare deployment token as `GITHUB_CODESPACES_TOKEN`.

The checked-in Worker Custom Domain is:

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

The repository includes an authenticated end-to-end MCP client for this gate:

```bash
bash scripts/slicer/run-codespace-mcp-smoke.sh
```

It uses the current full Git commit by default and exercises the actual Streamable HTTP MCP path:

```text
authenticated MCP connection
 -> slicer_prepare_workspace
 -> slicer_generate_model
 -> slicer_validate_for_print
 -> slicer_get_artifact
 -> verify downloaded size + SHA-256
```

The default real model is:

```text
hardware/enclosure/direct-mount/hinge-prototype-v2/02_middle_stationary_enclosure_HINGE_TEST.scad
```

The retrieved print-ready 3MF is written below:

```text
artifacts/slicer-smoke/
```

Override the commit/source when needed:

```bash
bash scripts/slicer/run-codespace-mcp-smoke.sh \
  --commit <40-character-sha> \
  --source hardware/enclosure/.../part.scad \
  --output-name part.stl
```

The script never prints the bearer token. It reports workspace/commit identity, selected Bambu profiles, structured slicer categories, artifact size/SHA-256 and per-stage timings. On a slicer validation failure it retrieves bounded diagnostics instead of downloading an artifact.

Record cold Codespace startup time, warm request latency, STL generation time, Bambu slice time and generated 3MF size on issue #118.

## Known POC limitation

The web-client credential is currently a static bearer token. If the target Codex/ChatGPT plugin surface requires OAuth rather than a configured bearer secret, replace only the Worker-facing authentication layer; the Codespace origin token and slicer implementation do not need to change.
