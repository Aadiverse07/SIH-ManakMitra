# Phase 23 — Working BIS Product Certification Application Workflow

## What changed
- Replaced the certification page's dummy application form with a resumable four-step workflow.
- Step 1 collects applicant/company/factory details.
- Step 2 collects product/Indian Standard details and supports authenticated document uploads.
- Step 3 provides a testing-readiness checklist.
- Step 4 reviews the saved application and hands the user off to the official BIS ManakOnline portal.
- Drafts are persisted per signed-in user in Supabase and can be resumed later.
- Added application-number generation.
- Added JSON application-summary download.
- Added optional SMTP email delivery; the UI reports the real delivery status instead of claiming a demo email was sent.

## Database
Run `database/migrations/0015_certification_applications.sql` in the project's Supabase/Postgres database.

## Email
Set these backend environment variables if real email delivery is desired:
- `SMTP_HOST`
- `SMTP_PORT` (default 587)
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM`

If SMTP is not configured, the application is still saved and the UI explicitly reports that the email was not sent.

## Important scope boundary
The workflow prepares and tracks the applicant's information. It does not pretend to submit an official BIS application or issue a BIS licence. The final step links to the official BIS ManakOnline portal for the actual online submission.
