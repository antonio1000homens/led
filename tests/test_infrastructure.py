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

    def test_deployment_secrets_keep_todoist_out_of_github_and_lambda_environment(self):
        template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertRegex(template, r"NationalRailToken:\n\s+Type: String\n\s+NoEcho: true")
        self.assertNotIn("AWS::SecretsManager::Secret", template)
        self.assertIn("TodoistOAuthParameterName:", template)
        self.assertIn("Default: /led/todoist/oauth", template)
        self.assertIn("ssm:GetParameter", template)
        self.assertIn("ssm:PutParameter", template)
        self.assertNotIn("secretsmanager:GetSecretValue", template)
        self.assertNotIn("secretsmanager:PutSecretValue", template)
        self.assertNotIn("TODOIST_TOKEN:", template)
        self.assertNotIn("TodoistToken:", template)
        self.assertIn("secrets.BW_ACCESS_TOKEN", workflow)
        self.assertIn("vars.BW_NATIONAL_RAIL_TOKEN", workflow)
        self.assertIn("vars.BW_SECRET_ID_CF_DEPLOY_API_TOKEN", workflow)
        self.assertNotIn("BW_TODOIST_TOKEN", workflow)
        self.assertNotIn("BWS_ACCESS_TOKEN", workflow)

    def test_todoist_feed_is_off_by_default_and_oauth_parameter_is_rotatable(self):
        template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        package = (ROOT / "scripts" / "package-lambda.sh").read_text(encoding="utf-8")
        deploy = (ROOT / "scripts" / "deploy-stack.sh").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        oauth_bootstrap = (ROOT / "scripts" / "bootstrap-todoist-oauth.py").read_text(encoding="utf-8")
        calendar = template.split("CalendarSource:", 1)[1].split("TodoistCacheSeconds:", 1)[0]
        self.assertIn("Default: 'off'", calendar)
        self.assertIn("AllowedValues: ['off', todoist]", calendar)
        self.assertIn("AllowedValues: ['off', queue_times]", template)
        self.assertIn("AllowedValues: ['off', open_meteo]", template)
        self.assertIn("TodoistOAuthParameterName:", template)
        self.assertIn("parameter${TodoistOAuthParameterName}", template)
        self.assertIn("TodoistOAuthParameterName:\n    Value: !Ref TodoistOAuthParameterName", template)
        self.assertIn('"${ROOT_DIR}/todoist.py"', package)
        self.assertNotIn("TodoistToken=", deploy)
        self.assertIn('"CalendarSource=${CALENDAR_SOURCE}"', deploy)
        self.assertIn('"TodoistCacheSeconds=${TODOIST_CACHE_SECONDS}"', deploy)
        self.assertIn('"TodoistMaxEvents=${TODOIST_MAX_EVENTS}"', deploy)
        self.assertIn('"TodoistFilterQuery=${TODOIST_FILTER_QUERY}"', deploy)
        self.assertIn('"TodoistTimezone=${TODOIST_TIMEZONE}"', deploy)
        self.assertIn('"CalendarDurationSeconds=${CALENDAR_DURATION_SECONDS}"', deploy)
        self.assertIn('"CalendarPageSeconds=${CALENDAR_PAGE_SECONDS}"', deploy)
        self.assertIn("vars.LED_CALENDAR_SOURCE", workflow)
        self.assertIn("vars.LED_TODOIST_FILTER_QUERY", workflow)
        self.assertIn("https://app.todoist.com/oauth/authorize", oauth_bootstrap)
        self.assertIn("https://api.todoist.com/oauth/access_token", oauth_bootstrap)
        self.assertIn('DEFAULT_SCOPE = "data:read"', oauth_bootstrap)
        self.assertIn('DEFAULT_PARAMETER_NAME = "/led/todoist/oauth"', oauth_bootstrap)
        self.assertIn('"Type": "SecureString"', oauth_bootstrap)
        self.assertIn('"Tier": "Standard"', oauth_bootstrap)
        self.assertIn('"ssm",', oauth_bootstrap)
        self.assertIn("--migrate-secret-id", oauth_bootstrap)
        self.assertIn('"get-secret-value"', oauth_bootstrap)
        self.assertIn("token_urlsafe", oauth_bootstrap)

    def test_hostname_defaults_to_led_subdomain(self):
        template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn("Default: led.alf-broadcast.co.uk", template)
        self.assertIn("led.alf-broadcast.co.uk", workflow)

    def test_deploy_updates_thorpe_park_rides_on_existing_stack(self):
        template = (ROOT / "infrastructure" / "led-stack.yaml").read_text(encoding="utf-8")
        deploy = (ROOT / "scripts" / "deploy-stack.sh").read_text(encoding="utf-8")
        self.assertIn("Hyperia,Stealth,The Swarm,SAW - The Ride,Nemesis Inferno,Colossus,Ghost Train,Rush,Detonator,Tidal Wave", template)
        self.assertIn("LED_THORPE_PARK_RIDES:-Hyperia,Stealth,The Swarm", deploy)
        self.assertIn('"ThorpeParkRides=${THORPE_PARK_RIDES}"', deploy)

    def test_cloudflare_dns_is_pinned_to_windsor_account(self):
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        helper = (ROOT / "scripts" / "cloudflare_dns.py").read_text(encoding="utf-8")
        shell = (ROOT / "scripts" / "configure-cloudflare-dns.sh").read_text(encoding="utf-8")
        self.assertIn("vars.CLOUDFLARE_ACCOUNT_ID", workflow)
        self.assertIn("Windsor Cloudflare account ID", workflow)
        self.assertIn('"account.id": account_id', helper)
        self.assertIn('default="Windsor"', helper)
        self.assertIn("not in the Windsor account", helper)
        self.assertIn('CLOUDFLARE_ACCOUNT_NAME="Windsor"', shell)
        self.assertNotIn("9a5523112f1460d0f77c9ba239d00029", workflow + helper + shell)

    def test_bootstrap_creates_dedicated_private_code_bucket(self):
        bootstrap = (ROOT / "infrastructure" / "bootstrap.yaml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn("CodeBucket:\n    Type: AWS::S3::Bucket", bootstrap)
        self.assertIn("BucketName: !Sub led-code-${AWS::Region}-${AWS::AccountId}", bootstrap)
        self.assertIn("BlockPublicAcls: true", bootstrap)
        self.assertIn("BlockPublicPolicy: true", bootstrap)
        self.assertIn("aws:SecureTransport: false", bootstrap)
        self.assertIn("CodeBucketName:", bootstrap)
        self.assertIn('CODE_BUCKET="led-code-${AWS_REGION}-${ACCOUNT_ID}"', workflow)
        self.assertNotIn("aws2022-lambda-code", bootstrap + workflow)
        self.assertNotIn("vars.CODE_BUCKET", workflow)

    def test_bootstrap_uses_immutable_github_oidc_subject_for_master(self):
        bootstrap = (ROOT / "infrastructure" / "bootstrap.yaml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn("RepoOwnerId:", bootstrap)
        self.assertIn("Default: '36929120'", bootstrap)
        self.assertIn("RepoId:", bootstrap)
        self.assertRegex(bootstrap, r"DeployBranch:\n\s+Type: String\n\s+Default: master")
        self.assertIn(
            "repo:${RepoOwner}@${RepoOwnerId}/${RepoName}@${RepoId}:ref:refs/heads/${DeployBranch}",
            bootstrap,
        )
        self.assertNotIn("repo:${RepoOwner}/${RepoName}:ref:refs/heads/${DeployBranch}", bootstrap)
        self.assertIn("branches:\n      - master", workflow)
        self.assertNotIn("branches:\n      - main", workflow)


if __name__ == "__main__":
    unittest.main()
