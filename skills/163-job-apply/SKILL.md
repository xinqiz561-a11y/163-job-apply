---
name: 163-job-apply
description: Prepare and send verified job-application emails from a 163.com account with résumé attachments, previews, deduplication, and explicit approval. Use only for verified email-based applications, not blind bulk mail or guessed addresses.
---

# 163.com 求职投递

Use this skill when the user wants to apply for jobs by email from a 163.com
mailbox. The skill prepares individualized plain-text messages, checks the
recipient and résumé attachment, previews the exact batch, and sends only
after explicit approval.

## Hard boundaries

- Never guess an address or turn a web-application URL into an email address.
- Require a company, position, recipient, source URL, concise match reason,
  `email_verified: true`, and an existing résumé attachment before sending.
- Do not use BCC, undisclosed recipients, or indiscriminate bulk mail.
- Do not request or store the normal 163 password or client authorization code
  in chat, manifests, logs, command arguments, or repository files.
- Treat `smtp.163.com` acceptance as provider acceptance only; it does not prove
  delivery, reading, or an interview invitation.

## Workflow

1. Read [references/schema.md](references/schema.md) and validate the candidate
   manifest with `scripts/validate_candidates.py`.
2. Build drafts with `scripts/build_application_emails.py`. Review company,
   position, recipient, source, match reason, subject, body, and attachment.
3. Keep `approval_state` as `preview` until the user explicitly approves the
   exact candidate IDs. Then set it to `confirmed` with `approved_at` and
   `approved_by`.
4. Run `scripts/send_confirmed_batch.py --dry-run` first. Send only with the
   exact token `--confirm-send SEND_163_BATCH`, a verified recipient, a real
   attachment, a confirmed manifest, and a supplied log path.
5. Use the Windows Credential Manager helper when available. Environment
   variables are supported for local/CI testing but must never be written to
   files or printed.
6. After sending, report sent, skipped, and failed items separately. Keep the
   JSONL send log private; it may contain personal and recipient information.

## Scripts

- `scripts/validate_candidates.py`: offline manifest and attachment checks.
- `scripts/build_application_emails.py`: deterministic draft generation.
- `scripts/send_confirmed_batch.py`: dry-run by default and guarded SMTP send.
- `scripts/store_163_auth_code.py`: verify and store a 163 client code in
  Windows Credential Manager; it never stores a normal mailbox password.
- `scripts/send_with_stored_credential.py`: load the local credential only at
  send time and invoke the guarded sender.
- `scripts/test_163_smtp_connection.py`: login test with no email side effect.
- `scripts/test_skill.py`: offline regression test.

For transport details, read [references/transport.md](references/transport.md).
