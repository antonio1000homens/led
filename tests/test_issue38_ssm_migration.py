from pathlib import Path
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Issue38SsmMigrationTests(unittest.TestCase):
    def test_workflow_assumes_oidc_role_before_loading_ssm_and_has_no_bitwarden_action(self):
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")

        self.assertIn("id-token: write", workflow)
        self.assertIn("LED_DEPLOY_SSM_PREFIX", workflow)
        self.assertLess(
            workflow.index("aws-actions/configure-aws-credentials"),
            workflow.index("Load deployment secrets from SSM"),
        )
        self.assertIn("bash scripts/load-ssm-secrets.sh", workflow)

        for stale_reference in (
            "bitwarden/sm-action",
            "BW_ACCESS_TOKEN",
            "BW_NATIONAL_RAIL_TOKEN",
            "BW_SECRET_ID_CF_DEPLOY_API_TOKEN",
        ):
            self.assertNotIn(stale_reference, workflow)

    def test_deploy_role_can_only_read_deployment_secret_hierarchy(self):
        bootstrap = (ROOT / "infrastructure" / "bootstrap.yaml").read_text(encoding="utf-8")
        statement = bootstrap.split("- Sid: ReadDeploymentSecrets", 1)[1].split(
            "- Sid: CallerIdentity", 1
        )[0]

        self.assertIn("Action: ssm:GetParameter", statement)
        self.assertNotIn("ssm:GetParameters\n", statement)
        self.assertNotIn("ssm:GetParametersByPath", statement)
        self.assertIn("parameter/led/deploy/*", statement)
        self.assertNotIn("parameter/led/*\n", statement)
        self.assertNotIn("/led/todoist/oauth", statement)

    def test_loader_requests_exact_parameters_masks_and_exports_values(self):
        loader = ROOT / "scripts" / "load-ssm-secrets.sh"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            call_log = tmp_path / "aws-calls.log"
            github_env = tmp_path / "github-env"
            aws_stub = bin_dir / "aws"
            aws_stub.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    printf '%s\\n' "$*" >> "${AWS_CALL_LOG}"
                    name=''
                    while [[ $# -gt 0 ]]; do
                      case "$1" in
                        --name)
                          name="$2"
                          shift 2
                          ;;
                        *)
                          shift
                          ;;
                      esac
                    done
                    case "${name}" in
                      /led/deploy/national-rail-token)
                        printf '%s\\n' 'rail-secret-value'
                        ;;
                      /led/deploy/cloudflare/api-token)
                        printf '%s\\n' 'cloudflare-secret-value'
                        ;;
                      *)
                        echo "unexpected parameter: ${name}" >&2
                        exit 9
                        ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            aws_stub.chmod(aws_stub.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
                    "AWS_CALL_LOG": str(call_log),
                    "GITHUB_ENV": str(github_env),
                    "AWS_REGION": "eu-west-2",
                    "LED_DEPLOY_SSM_PREFIX": "/led/deploy",
                }
            )
            result = subprocess.run(
                ["bash", str(loader)],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            calls = call_log.read_text(encoding="utf-8")
            self.assertIn("ssm get-parameter --name /led/deploy/national-rail-token", calls)
            self.assertIn("ssm get-parameter --name /led/deploy/cloudflare/api-token", calls)
            self.assertEqual(calls.count("--with-decryption"), 2)

            exported = github_env.read_text(encoding="utf-8")
            self.assertIn("NATIONAL_RAIL_TOKEN<<", exported)
            self.assertIn("rail-secret-value", exported)
            self.assertIn("CF_DEPLOY_API_TOKEN<<", exported)
            self.assertIn("cloudflare-secret-value", exported)

            self.assertIn("::add-mask::rail-secret-value", result.stdout)
            self.assertIn("::add-mask::cloudflare-secret-value", result.stdout)
            non_mask_output = "\n".join(
                line for line in result.stdout.splitlines() if not line.startswith("::add-mask::")
            )
            self.assertNotIn("rail-secret-value", non_mask_output)
            self.assertNotIn("cloudflare-secret-value", non_mask_output)

    def test_loader_fails_closed_without_github_env(self):
        env = os.environ.copy()
        env.pop("GITHUB_ENV", None)
        result = subprocess.run(
            ["bash", str(ROOT / "scripts" / "load-ssm-secrets.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GITHUB_ENV is required", result.stderr)

    def test_bootstrap_script_has_valid_shell_syntax_and_help(self):
        script = ROOT / "scripts" / "bootstrap-ssm-migration.sh"
        syntax = subprocess.run(
            ["bash", "-n", str(script)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

        help_result = subprocess.run(
            ["bash", str(script), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--dry-run", help_result.stdout)
        self.assertIn("BW_NATIONAL_RAIL_TOKEN", help_result.stdout)
        self.assertIn("BW_CF_DEPLOY_API_TOKEN", help_result.stdout)

    def test_local_bootstrap_config_is_exampled_and_gitignored(self):
        example = ROOT / "config" / "bootstrap-ssm-migration.env.example"
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertTrue(example.exists())
        example_text = example.read_text(encoding="utf-8")
        self.assertIn("SSM_PREFIX=/led/deploy", example_text)
        self.assertIn("config/bootstrap-ssm-migration.env", gitignore)
        self.assertNotIn("BW_ACCESS_TOKEN=", example_text)


if __name__ == "__main__":
    unittest.main()
