# LED Repository Notes

## MatrixPortal Web Workflow Credentials

- Before using authenticated MatrixPortal Web Workflow features, retrieve `CIRCUITPY_WEB_API_PASSWORD` from Bitwarden Secrets Manager secret `LAN-DEPLOY` (`46d4f1fe-be23-4d57-9c5b-b4e700c2acd3`). On `windsor-app1`, the BWS machine token is stored in `~/.config/bws/env` with owner-only permissions and loaded by Bash.
- Keep the secret value out of terminal output and logs. For firmware uploads, enter it only at the uploader's interactive password prompt.
- Never put the password in this repository, a command-line argument, an environment file, a log, or a report. Keep the BWS token in its owner-only home config; never copy it into the repository, command-line arguments, logs, or reports.
- For background serial capture, pipe the Bitwarden value directly to `upload-firmware-wifi.py --password-stdin` inside a detached tmux session; never store it on disk or expose it in process arguments.
