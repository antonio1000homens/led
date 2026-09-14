from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ControlPlaneInfrastructureTests(unittest.TestCase):
    def setUp(self):
        self.template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        self.workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.admin = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")
        self.docs = (ROOT / "CONTROL_PLANE.md").read_text(encoding="utf-8")

    def test_runtime_config_is_on_demand_encrypted_dynamodb(self):
        self.assertIn("RuntimeConfigTable:", self.template)
        self.assertIn("Type: AWS::DynamoDB::Table", self.template)
        self.assertIn("BillingMode: PAY_PER_REQUEST", self.template)
        self.assertIn("SSESpecification: {SSEEnabled: true}", self.template)
        self.assertIn("DeletionPolicy: Retain", self.template)

    def test_publisher_only_reads_runtime_config_and_control_role_cannot_read_provider_secrets(self):
        publisher = self.template.split("PublisherRole:", 1)[1].split("PublisherLogGroup:", 1)[0]
        control = self.template.split("ControlRole:", 1)[1].split("ControlLogGroup:", 1)[0]
        self.assertIn("dynamodb:GetItem", publisher)
        self.assertNotIn("dynamodb:PutItem", publisher)
        self.assertIn("dynamodb:GetItem", control)
        self.assertIn("dynamodb:PutItem", control)
        self.assertIn("lambda:InvokeFunction", control)
        self.assertNotIn("ssm:GetParameter", control)
        self.assertNotIn("NATIONAL_RAIL_TOKEN", control)
        control_function = self.template.split("ControlFunction:", 1)[1].split("ControlApi:", 1)[0]
        self.assertNotIn("NATIONAL_RAIL_TOKEN", control_function)
        self.assertNotIn("TODOIST_OAUTH_SECRET_ARN", control_function)

    def test_control_api_is_versioned_and_public_screens_remain_s3_backed(self):
        for route in (
            "GET /api/control/v1/session",
            "GET /api/control/v1/config",
            "GET /api/control/v1/status",
            "GET /api/control/v1/feeds/{feed_id}/options",
            "PATCH /api/control/v1/feeds/{feed_id}",
        ):
            self.assertIn(route, self.template)
        self.assertIn("PathPattern: api/control/v1/*", self.template)
        screens = self.template.split("- PathPattern: api/screens", 1)[1].split("ViewerCertificate:", 1)[0]
        self.assertIn("TargetOriginId: led-s3-origin", screens)
        self.assertNotIn("led-control-api-origin", screens)

    def test_control_lambda_validates_access_configuration_and_workflow_requires_it(self):
        self.assertIn("CF_ACCESS_TEAM_DOMAIN: !Ref CloudflareAccessTeamDomain", self.template)
        self.assertIn("CF_ACCESS_AUD: !Ref CloudflareAccessAudience", self.template)
        self.assertIn("CF_ACCESS_TEAM_DOMAIN: ${{ vars.CF_ACCESS_TEAM_DOMAIN }}", self.workflow)
        self.assertIn("CF_ACCESS_AUD: ${{ vars.CF_ACCESS_AUD }}", self.workflow)
        self.assertIn("cloudflareaccess\\.com", self.workflow)

    def test_admin_bootstraps_access_then_uses_same_origin_api_without_bearer_secret(self):
        self.assertIn("const API='/api/control/v1';", self.admin)
        self.assertIn("credentials:'same-origin'", self.admin)
        self.assertIn("window.location.replace(`${API}/session`);", self.admin)
        self.assertIn("window.history.replaceState(null,'','/admin');", self.admin)
        self.assertIn("'If-Match'", self.admin)
        self.assertNotIn("Admin token", self.admin)
        self.assertNotIn("sessionStorage", self.admin)
        self.assertNotIn("Bearer ", self.admin)

    def test_docs_keep_admin_human_only_and_control_api_service_token_enabled(self):
        self.assertIn("/admin*", self.docs)
        self.assertIn("interactive Google/two-user allow policy only", self.docs)
        self.assertIn("/api/control/v1/*", self.docs)
        self.assertIn("Service Auth", self.docs)
        self.assertIn("CF-Access-Client-Id", self.docs)
        self.assertIn("CF-Access-Client-Secret", self.docs)
        self.assertIn("Do not add an Access application covering `https://<led-host>/api/screens`", self.docs)

    def test_polling_parameters_cannot_drop_below_one_minute(self):
        for parameter in (
            "RailCacheSeconds",
            "ThorpeParkCacheSeconds",
            "ChessingtonCacheSeconds",
            "TodoistCacheSeconds",
            "WeatherCacheSeconds",
        ):
            block = self.template.split(f"{parameter}:", 1)[1].split("\n  ", 1)[0]
            self.assertIn("MinValue: 60", block)
        self.assertIn("ScheduleExpression: rate(1 minute)", self.template)


if __name__ == "__main__":
    unittest.main()
