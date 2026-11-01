# Scouts next-events screen (#278 / PR #279)

The **Scouts · Beavers & Cubs** screen uses two independently fetched OSM ICS
calendars. It is disabled by default. It appears in the admin navigation under
**Calendar & events**, separate from Todoist and football.

## Private feed configuration

Provision these four parameters as **SecureString** in the LED AWS account,
not in the independent Scouts AWS account:

| Group | Primary programme | Supplemental events |
| --- | --- | --- |
| Beavers | `/led/beavers/programme-ics-url` | `/led/beavers/events-ics-url` |
| Cubs | `/led/cubs/programme-ics-url` | `/led/cubs/events-ics-url` |

Each parameter contains the **full private HTTPS ICS URL**, never a calendar ID.
The LED CloudFormation template passes **parameter names only** to the publisher
environment and grants `ssm:GetParameter` on the four named SSM resources.
The publisher decrypts those values internally; never copy URLs from the Scouts
AWS account or expose them in repository files, logs, deployment variables,
simulator or public HTTP screen responses.

The programme feed is the primary source for each group and the events feed
is supplemental. Within a group, the provider combines and de-duplicates events
before selecting the next upcoming event. If a configured upstream fails, the
last successful data for **that group** is retained and marked stale. The other
group remains independent.

For a non-default KMS key, grant the publisher role the narrowly scoped
`kms:Decrypt` permission required for the parameter encryption context.
Using the standard SSM-managed key needs no additional customer-managed key grant.

## Animation and layout

The screen is a **paired transition** in the normal board rotation:

1. A camping tent and its tagline slide in from the right over 2.4
   seconds, then hold for 1.6 seconds before the next-events screen. The editable message defaults to **Be prepared...**.
   It accepts a non-empty printable ASCII string of up to 48 characters.
2. The next screen displays **two equally sized columns**: **Beavers** on the
   left, **Cubs** on the right. Each heading shares its top row with the
   upcoming event's date/time (or ALL DAY), leaving two rows for a word-wrapped
   event title. Longer titles end with an ellipsis.

Unlike the old Todoist-style scrolling agenda, this shows **one next event per
group**. Missing feeds display **Calendar unavailable**, and calendars with
no future events display **No upcoming events**. Both columns are independent.

The MatrixPortal firmware, simulator and board rotation all use screen kinds
`scouts_intro` and `scouts_next_events`. The paired screens share the Cubs
feed's scheduling windows; they are treated as one atomic block in rotation.

## Admin configuration

Navigate to **Calendar & events → Scouts · Beavers & Cubs**. Enable the feed
once the event titles have been approved for public display.

| Setting | Default | Limits |
| --- | --- | --- |
| Enabled | No | Both groups together |
| Provider refresh | 86,400 seconds (24 hours) | 3,600–604,800 seconds (1 hour–7 days) |
| Screen duration | 10 seconds | 2–300 seconds (intro is additional) |
| Scouts intro message | `Be prepared...` | 1–48 printable ASCII characters |
| Schedule windows | Always | Optional Europe/London cron windows |

The shared **polling interval** applies to both groups but each source is
refreshed and cached separately. The **one-hour minimum is enforced by the
admin schema, API validation and CloudFormation parameter bounds**, not just
the displayed form. Failed/stale feeds never retry more often than hourly.

## Publication and privacy

The publisher's per-minute invocation does **not** mean an ICS HTTP request
every minute. It uses the existing S3 last-successful state cache and only
fetches a group when its refresh interval is due. The payload contains only
whitelisted event title/date/time data, stale flags, and admin display options.

**Warning:** `/api/screens` and the simulator are publicly readable. **Event
titles and dates are visible to anyone once the screen is enabled**, but private
calendar URLs, descriptions, locations and attendees are never published.
Inspect the real feeds before enabling them.

Use synthetic ICS in tests; verify live feed recurrence/vendor-specific
properties independently in the LED account before deploying the screen.
