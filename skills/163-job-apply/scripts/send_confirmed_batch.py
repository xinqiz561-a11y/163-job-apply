#!/usr/bin/env python3
"""Send only an explicitly confirmed 163 SMTP batch."""

from __future__ import annotations

import argparse
import json
import os
import re
import smtplib
import ssl
import sys
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any


EMAIL_RE = re.compile(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")
CONFIRM_TOKEN = "SEND_163_BATCH"


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
        raise ValueError("发送清单必须是包含 candidates 数组的对象")
    return data


def read_sent_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("status") == "sent" and item.get("idempotency_key"):
            keys.add(str(item["idempotency_key"]))
    return keys


def candidate_error(candidate: dict[str, Any]) -> str | None:
    if candidate.get("email_verified") is not True:
        return "邮箱未核验"
    recipient = str(candidate.get("to", "")).strip()
    if not EMAIL_RE.fullmatch(recipient):
        return "邮箱格式无效"
    attachment = candidate.get("attachment_path")
    if not attachment or not Path(str(attachment)).is_file():
        return "简历附件不存在"
    if not candidate.get("subject") or not candidate.get("body"):
        return "缺少主题或正文"
    if not str(candidate.get("source_url", "")).startswith(("http://", "https://")):
        return "缺少有效来源链接"
    return None


def make_message(sender: str, candidate: dict[str, Any]) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = str(candidate["to"]).strip()
    message["Subject"] = str(candidate["subject"])
    message.set_content(str(candidate["body"]))
    attachment = Path(str(candidate["attachment_path"]))
    message.add_attachment(
        attachment.read_bytes(),
        maintype="application",
        subtype="pdf" if attachment.suffix.casefold() == ".pdf" else "octet-stream",
        filename=attachment.name,
    )
    return message


def append_log(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="只检查，不连接邮箱")
    parser.add_argument("--confirm-send")
    parser.add_argument("--log-path", type=Path)
    parser.add_argument("--max-count", type=int, default=10)
    parser.add_argument("--delay-seconds", type=float, default=3.0)
    parser.add_argument("--smtp-host", default="smtp.163.com")
    parser.add_argument("--smtp-port", type=int, default=465)
    args = parser.parse_args()

    try:
        manifest = load(args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    candidates = manifest["candidates"]
    if len(candidates) > args.max_count:
        print(json.dumps({"error": f"候选项数量 {len(candidates)} 超过本次上限 {args.max_count}"}, ensure_ascii=False), file=sys.stderr)
        return 2

    if not args.dry_run:
        if manifest.get("approval_state") != "confirmed":
            print("拒绝发送：approval_state 不是 confirmed。", file=sys.stderr)
            return 2
        if not manifest.get("approved_at") or not manifest.get("approved_by"):
            print("拒绝发送：缺少 approved_at 或 approved_by。", file=sys.stderr)
            return 2
        if args.confirm_send != CONFIRM_TOKEN:
            print("拒绝发送：缺少精确确认标记。", file=sys.stderr)
            return 2
        if not args.log_path:
            print("拒绝发送：实际发送必须提供 --log-path。", file=sys.stderr)
            return 2

    sent_keys = read_sent_keys(args.log_path) if args.log_path else set()
    report = {"dry_run": args.dry_run, "ready": True, "would_send": [], "skipped": [], "errors": []}
    local_keys: set[str] = set()
    selected: list[dict[str, Any]] = []
    for candidate in candidates:
        error = candidate_error(candidate)
        key = str(candidate.get("idempotency_key", ""))
        if error:
            report["errors"].append({"id": candidate.get("id"), "error": error})
            continue
        if key and (key in sent_keys or key in local_keys):
            report["skipped"].append({"id": candidate.get("id"), "reason": "已发送或本批次重复"})
            continue
        local_keys.add(key)
        selected.append(candidate)
        report["would_send"].append(
            {
                "id": candidate.get("id"),
                "company": candidate.get("company"),
                "position": candidate.get("position"),
                "to": candidate.get("to"),
                "subject": candidate.get("subject"),
                "attachment": candidate.get("attachment_path"),
            }
        )

    if report["errors"]:
        report["ready"] = False
    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ready"] else 1
    if not report["ready"]:
        print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    sender = os.environ.get("163_JOB_APPLY_EMAIL", "").strip()
    auth_code = os.environ.get("163_JOB_APPLY_AUTH_CODE", "")
    if not sender or not auth_code:
        print("拒绝发送：未找到 163_JOB_APPLY_EMAIL 或 163_JOB_APPLY_AUTH_CODE。", file=sys.stderr)
        return 2

    context = ssl.create_default_context()
    results = []
    try:
        with smtplib.SMTP_SSL(args.smtp_host, args.smtp_port, context=context, timeout=30) as smtp:
            smtp.login(sender, auth_code)
            for candidate in selected:
                message = make_message(sender, candidate)
                smtp.send_message(message)
                event = {
                    "id": candidate.get("id"),
                    "idempotency_key": candidate.get("idempotency_key"),
                    "to": candidate.get("to"),
                    "company": candidate.get("company"),
                    "position": candidate.get("position"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "sent",
                }
                append_log(args.log_path, event)
                results.append(event)
                if args.delay_seconds > 0:
                    time.sleep(args.delay_seconds)
    except Exception as exc:
        error = {"timestamp": datetime.now(timezone.utc).isoformat(), "status": "failed", "error": type(exc).__name__}
        append_log(args.log_path, error)
        print(json.dumps({"sent": results, "failure": error}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(json.dumps({"sent": results, "skipped": report["skipped"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
