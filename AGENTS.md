# LED Repository Notes

## MatrixPortal Web Workflow Credentials

- Before uploading application firmware to a MatrixPortal S3 over Web Workflow, retrieve `CIRCUITPY_WEB_API_PASSWORD` from Bitwarden Secrets Manager secret `lan-deploy` (`943c6673-c07a-448b-8c0e-b4e600bc0226`). On `windsor-app1`, the BWS machine token is stored in `~/.config/bws/env` with owner-only permissions and loaded by Bash.
- Keep the secret value out of terminal output and logs; enter it only at the uploader's interactive password prompt.
- Never put the password in this repository, a command-line argument, an environment file, a log, or a report. Keep the BWS token in its owner-only home config; never copy it into the repository, command-line arguments, logs, or reports.
