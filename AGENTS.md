# LED Repository Notes

## MatrixPortal Web Workflow Credentials

- The MatrixPortal S3 `CIRCUITPY_WEB_API_PASSWORD` is stored in macOS Keychain.
- During deployment, retrieve it from Keychain and enter it only at the uploader's interactive password prompt.
- Never put the password value in this repository, a command line, environment file, log, or report.
