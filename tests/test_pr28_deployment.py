from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Pr28DeploymentContractTests(unittest.TestCase):
    def test_control_api_cloudfront_origin_preserves_origin_host_and_access_header(self):
        template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        control_behavior = template.split("PathPattern: api/control/v1/*", 1)[1].split("PathPattern: api/screens", 1)[0]
        self.assertIn("OriginRequestPolicyId: b689b0a8-53d0-40ab-baf2-68738e2966ac", control_behavior)
        self.assertNotIn("OriginRequestPolicyId: 216adef6-5c7f-47e4-b989-5492eafa07d3", control_behavior)

    def test_control_api_lambda_proxy_uses_post_integration_method(self):
        template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        integration = template.split("ControlApiIntegration:", 1)[1].split("ControlConfigRoute:", 1)[0]
        self.assertIn("IntegrationType: AWS_PROXY", integration)
        self.assertIn("IntegrationMethod: POST", integration)
        self.assertIn("PayloadFormatVersion: '2.0'", integration)

    def test_cloudformation_role_can_manage_control_api_and_runtime_table_resources(self):
        bootstrap = (ROOT / "infrastructure" / "bootstrap.yaml").read_text(encoding="utf-8")
        self.assertIn("Sid: ApiGatewayV2Manage", bootstrap)
        for action in (
            "apigateway:GET",
            "apigateway:POST",
            "apigateway:PUT",
            "apigateway:PATCH",
            "apigateway:DELETE",
            "apigateway:TagResource",
            "apigateway:UntagResource",
        ):
            self.assertIn(action, bootstrap)
        self.assertIn("lambda:GetPolicy", bootstrap)
        self.assertIn("lambda:AddPermission", bootstrap)
        self.assertIn("lambda:RemovePermission", bootstrap)
        self.assertIn("Sid: RuntimeConfigTableManage", bootstrap)
        self.assertIn("dynamodb:CreateTable", bootstrap)
        self.assertIn("dynamodb:UpdateTable", bootstrap)
        self.assertIn("table/led-runtime-config", bootstrap)

    def test_github_deploy_role_publishes_admin_without_legacy_admin_token(self):
        bootstrap = (ROOT / "infrastructure" / "bootstrap.yaml").read_text(encoding="utf-8")
        deploy = (ROOT / "scripts" / "deploy-stack.sh").read_text(encoding="utf-8")
        static = (ROOT / "scripts" / "deploy-static.sh").read_text(encoding="utf-8")
        self.assertNotIn("Sid: AdminTokenParameter", bootstrap)
        self.assertNotIn("parameter/led/admin/token", bootstrap)
        self.assertNotIn("/led/admin/token", deploy)
        self.assertIn("/admin", bootstrap)
        self.assertIn("/admin.html", bootstrap)
        self.assertIn("simulator/admin.html", static)
        self.assertIn("'/api/control/v1/*'", static)

    def test_stack_deploy_prints_recent_events_when_cloudformation_fails(self):
        deploy = (ROOT / "scripts" / "deploy-stack.sh").read_text(encoding="utf-8")
        self.assertIn("CloudFormation deployment failed; recent stack events:", deploy)
        self.assertIn("cloudformation describe-stack-events", deploy)
        self.assertIn("StackEvents[0:30]", deploy)


if __name__ == "__main__":
    unittest.main()
