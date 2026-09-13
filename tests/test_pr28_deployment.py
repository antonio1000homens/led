from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Pr28DeploymentContractTests(unittest.TestCase):
    def test_config_api_cloudfront_origin_preserves_origin_host(self):
        template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        config_behavior = template.split("PathPattern: api/config", 1)[1].split("PathPattern: api/screens", 1)[0]
        self.assertIn("OriginRequestPolicyId: b689b0a8-53d0-40ab-baf2-68738e2966ac", config_behavior)
        self.assertNotIn("OriginRequestPolicyId: 216adef6-5c7f-47e4-b989-5492eafa07d3", config_behavior)

    def test_cloudformation_role_can_manage_config_api_resources(self):
        bootstrap = (ROOT / "infrastructure" / "bootstrap.yaml").read_text(encoding="utf-8")
        self.assertIn("Sid: ApiGatewayV2Manage", bootstrap)
        for action in ("apigateway:GET", "apigateway:POST", "apigateway:PUT", "apigateway:PATCH", "apigateway:DELETE"):
            self.assertIn(action, bootstrap)
        self.assertIn("lambda:GetPolicy", bootstrap)
        self.assertIn("lambda:AddPermission", bootstrap)
        self.assertIn("lambda:RemovePermission", bootstrap)

    def test_github_deploy_role_can_create_admin_token_and_publish_admin_page(self):
        bootstrap = (ROOT / "infrastructure" / "bootstrap.yaml").read_text(encoding="utf-8")
        deploy = (ROOT / "scripts" / "deploy-stack.sh").read_text(encoding="utf-8")
        static = (ROOT / "scripts" / "deploy-static.sh").read_text(encoding="utf-8")
        self.assertIn("Sid: AdminTokenParameter", bootstrap)
        self.assertIn("ssm:GetParameter", bootstrap)
        self.assertIn("ssm:PutParameter", bootstrap)
        self.assertIn("parameter/led/admin/token", bootstrap)
        self.assertIn("/led/admin/token", deploy)
        self.assertIn("/admin.html", bootstrap)
        self.assertIn("simulator/admin.html", static)
        self.assertIn("'/api/config'", static)


if __name__ == "__main__":
    unittest.main()
