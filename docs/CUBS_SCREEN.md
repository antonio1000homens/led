# Cubs agenda screen (#278)

The **CUBS** screen is a separate calendar-agenda feed, styled like the Todoist screen.
It is disabled by default. The LED publisher fetches the original OSM ICS feed
independently; the Scouts application is neither queried nor granted access.

## Security and AWS account separation

All commands below must run with credentials for the **LED AWS account**, not the
Scouts AWS account. No cross-account roles, shared buckets, Lambda invocations,
or CloudFormation imports are needed.

The Scouts repo is a reference for the upstream feed **format** only. It defines
two sources: **Cubs Programme** (primary) and **Cubs Events** (optional).
Never copy values from Scouts Lambda configuration, paste a private URL into
GitHub, put it in a deployment environment variable, or print the URL in logs.

Create these parameters in the LED AWS account using an appropriate confidential
provisioning method (the commands below read the value interactively, rather than
placing the URL directly in shell history):

```bash
# Run only against the LED account and verify your AWS identity first.
aws sts get-caller-identity
read -rs -p 'Cubs Programme private ICS URL: ' CUBS_URL; echo
aws ssm put-parameter --name /led/cubs/programme-ics-url \
  --type SecureString --value "$CUBS_URL" --overwrite
unset CUBS_URL
```

Repeat with parameter `/led/cubs/events-ics-url` to enable the optional
Cubs Events feed. Creating only the Programme parameter is supported.

The CloudFormation parameters `CubsProgrammeParameterName` and
`CubsEventsParameterName` identify parameter **names**, not secrets.
The publisher role has only `ssm:GetParameter` on the two LED-account parameters.
If these parameters use a customer-managed KMS key rather than the default
AWS-managed SSM key, explicitly grant the publisher role `kms:Decrypt`
on that key, scoped to the required parameter encryption context.

The private ICS URL is fetched server-side and is absent from the runtime
configuration, admin API, S3 screen payload, MatrixPortal firmware and simulator.

**Privacy:** `/api/screens` and the simulator are publicly readable.
Cubs event **titles and times are therefore public when this feed is enabled**.
Only these fields are published, not location, description, attendee or email
data. Inspect the feed titles before enabling it if titles themselves are sensitive.

## Configuration and refresh

Deploy the LED backend, CloudFormation stack and MatrixPortal firmware together.
Create the parameter(s), then enable **Cubs** on the LED admin page.
This is a separate feed from **Calendar / Todoist**; both can rotate independently.

| Setting | Default | Limits |
| --- | --- | --- |
| Enabled | No | independent from Todoist |
| Provider refresh | 86,400 s (24 h) | 3,600–604,800 s (1 h–7 days) |
| Screen duration | 10 s minimum | 2–300 s; pagination increases effective duration |
| Visible event count | 6 | 1–12 events |

The existing per-minute LED publisher uses its S3 last-successful feed cache.
An enabled Cubs feed is refreshed only when due. Missing/upstream-failing feeds
leave the last good data in place and are marked stale, with a bounded one-hour
retry delay for stale or empty data. Disabling Cubs removes its screen and
stops upstream polling.

The MatrixPortal and simulator share Todoist's three-visible-row sliding
pages, date/time column, long-title marquee and dynamic screen duration.
Screen ID: `cubs`; kind: `calendar_agenda`; source: `cubs_ics`.

Use synthetic ICS in tests. Verify the actual upstream calendar structure
against the LED account's independently configured source. In particular,
check any unsupported vendor-specific recurrence properties before enabling
the screen in production.
