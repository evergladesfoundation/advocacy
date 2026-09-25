# CDMP monitor onboarding

## Add an application

Editing `data/cdmp/applications.json` is required and is not enough on its own.

1. Open the plan in EnerGov and copy the plan GUID from the URL. The page title is the CDMP number.
2. Add an entry with `cdmpNumber`, `planGuid`, `sharepointFolderUrl`, and `notes`.
3. Create the SharePoint folder for that plan.
4. Set `sharepointFolderUrl` to the folder path inside the drive named by `GRAPH_DRIVE_ID`. Uploads use Microsoft Graph `PUT /drives/{drive-id}/root:/{path}:/content`. Until that path is set, a new recent file is reported as a failure and is not marked seen, so the next run tries again.

No code change is required for application #8 or later.

## What a run does

`python -m cdmp_monitor run` checks every configured plan once.

- Attachments already in `data/cdmp/state.json` are ignored.
- A new attachment older than 7 days is written to state and left out of the email, the download, and the summary.
- A new attachment from the last 7 days is downloaded, summarized, uploaded, then written to state.
- The run always prints a digest. It emails that digest unless `--log-only` is set.
- The digest says how many applications were checked and lists any that failed.

The scheduled workflow stays in log-only mode until alerts are turned on. Log-only mode records older attachments and reports recent ones without downloading, summarizing, uploading, or emailing them. Recent files stay unseen so the first real alert run can still file them.

## Secrets

Never commit these. Use `.env` locally and GitHub Actions secrets for the schedule.

- `CLAUDE_API_KEY` and optional `CLAUDE_MODEL` (default `claude-sonnet-4-5`)
- `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, `GRAPH_DRIVE_ID`
- `MAIL_TO`, `MAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`

Mail uses the same SMTP settings as the daily policy monitor.

## Retention

Downloaded PDFs are not deleted from SharePoint. Folders grow indefinitely. The job only keeps a local copy long enough to summarize and upload it.

## Heartbeat

The daily email is the heartbeat. Silence means the job did not send, not that nothing changed. Who is paged when that email stops is still unset.
