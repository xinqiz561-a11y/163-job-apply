#!/usr/bin/env python3
"""Verify 163 SMTP credentials without sending a message."""

from __future__ import annotations

import os
import smtplib
import ssl
import sys


def main() -> int:
    sender = os.environ.get("163_JOB_APPLY_EMAIL", "").strip()
    auth_code = os.environ.get("163_JOB_APPLY_AUTH_CODE", "")
    if not sender or not auth_code:
        print("缺少本机 SMTP 凭据。", file=sys.stderr)
        return 2
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.163.com", 465, context=context, timeout=30) as smtp:
            smtp.login(sender, auth_code)
    except Exception as exc:
        print(f"SMTP 登录测试失败（{type(exc).__name__}）。", file=sys.stderr)
        return 1
    print("SMTP 登录测试通过（未发送邮件）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
