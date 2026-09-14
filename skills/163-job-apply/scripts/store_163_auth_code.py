#!/usr/bin/env python3
"""Verify and store a 163 client authorization code in Windows Credential Manager."""

from __future__ import annotations

import argparse
import getpass
import re
import smtplib
import ssl
import sys

try:
    import win32cred
except ImportError:
    win32cred = None


EMAIL_RE = re.compile(r"^[^@\s<>]+@163\.com$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="要使用的 163.com 邮箱地址")
    args = parser.parse_args()
    email = args.email.strip()
    if not EMAIL_RE.fullmatch(email):
        print("只接受形如 name@163.com 的邮箱地址。", file=sys.stderr)
        return 2
    if win32cred is None:
        print("缺少 pywin32，请先运行: python -m pip install pywin32", file=sys.stderr)
        return 2

    code = getpass.getpass("请输入163客户端授权码（不是邮箱登录密码）：").strip()
    if not code:
        print("未输入授权码。", file=sys.stderr)
        return 2

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.163.com", 465, context=context, timeout=30) as smtp:
            smtp.login(email, code)
    except Exception as exc:
        print(f"SMTP 登录失败，未保存授权码（{type(exc).__name__}）。", file=sys.stderr)
        return 1

    target = f"Codex-163-job-apply/{email}"
    try:
        win32cred.CredWrite(
            {
                "Type": win32cred.CRED_TYPE_GENERIC,
                "TargetName": target,
                "UserName": email,
                "CredentialBlob": code,
                "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
            },
            0,
        )
    except Exception as exc:
        print(f"SMTP 登录成功，但写入 Windows Credential Manager 失败（{type(exc).__name__}）。", file=sys.stderr)
        return 1

    print("SMTP 登录验证通过；163客户端授权码已保存到 Windows Credential Manager。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
