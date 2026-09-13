from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InfrastructureContractTests(unittest.TestCase):
    def test_cloudfront_uses_private_oac_and_does_not_expose_state_prefix(self):
        template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        self.assertIn("AWS::CloudFront::OriginAccessControl", template)
        self.assertIn("BlockPublicAcls: true", template)
        self.assertIn("BlockPublicPolicy: true", template)
        policy = template.split("HostingBucketPolicy:", 1)[1].split("Outputs:", 1)[0]
        self.assertIn("${HostingBucket.Arn}/index.html", policy)
        self.assertIn("${HostingBucket.Arn}/api/*", policy)
        self.assertNotIn("${HostingBucket.Arn}/state/", policy)

    def test_screens_path_is_not_cached_by_cloudfront(self):
        template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        self.assertIn("PathPattern: api/screens", template)
        self.assertIn("CachePolicyId: 4135ea2d-6df8-44a3-9df3-4b5a84be39ad", template)

    def test_scheduler_runs_once_per_minute(self):
        template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        self.assertIn("Type: AWS::Scheduler::Schedule", template)
        self.assertIn("ScheduleExpression: rate(1 minute)", template)

    def test_runtime_secret_is_noecho_and_github_uses_bitwarden_uid_variables(self):
        template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertRegex(template, r"NationalRailToken:\n\s+Type: String\n\s+NoEcho: true")
        self.assertIn("secrets.BW_ACCESS_TOKEN", workflow)
        self.assertIn("vars.BW_NATIONAL_RAIL_TOKEN", workflow)
        self.assertIn("vars.BW_SECRET_ID_CF_DEPLOY_API_TOKEN", workflow)
        self.assertIn("must contain a Bitwarden secret UID", workflow)
        self.assertNotIn("BWS_ACCESS_TOKEN", workflow)

    def test_hostname_defaults_to_led_subdomain(self):
        template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn("Default: led.alf-broadcast.co.uk", template)
        self.assertIn("led.alf-broadcast.co.uk", workflow)


if __name__ == "__main__":
    unittest.main()
