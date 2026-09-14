#!/usr/bin/env python3
"""Run the guarded sender with a credential loaded only at runtime."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    import win32cred
except ImportError:
    win32cred = None


SEND_SCRIPT = Path(__file__).with_name("send_confirmed_batch.py")
TEST_SCRIPT = Path(__file__).with_name("test_163_smtp_connection.py")


def read_code(email: str) -> str:
    if win32cred is None:
        raise RuntimeError("pywin32 is not installed")
    target = f"Codex-163-job-apply/{email}"
    item = win32cred.CredRead(target, win32cred.CRED_TYPE_GENERIC, 0)
    value = item.get("CredentialBlob", b"")
    if not isinstance(value, bytes):
        return str(value)
    try:
        utf8_value = value.decode("utf-8")
    except UnicodeDecodeError:
        utf8_value = ""
    if utf8_value and "\x00" not in utf8_value:
        return utf8_value
    return value.decode("utf-16-le").rstrip("\x00")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--mode", choices=("test-connection", "send"), required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--log-path", type=Path)
    parser.add_argument("--confirm-send")
    parser.add_argument("--smtp-host", default="smtp.163.com")
    parser.add_argument("--smtp-port", type=int, default=465)
    args = parser.parse_args()

    try:
        code = read_code(args.email.strip())
    except Exception as exc:
        print(f"无法读取本机163授权码（{type(exc).__name__}）。", file=sys.stderr)
        return 2

    child_env = os.environ.copy()
    child_env["163_JOB_APPLY_EMAIL"] = args.email.strip()
    child_env["163_JOB_APPLY_AUTH_CODE"] = code
    try:
        if args.mode == "test-connection":
            command = [sys.executable, str(TEST_SCRIPT)]
        else:
            if not args.manifest or not args.log_path:
                print("send 模式必须提供 --manifest 和 --log-path。", file=sys.stderr)
                return 2
            if args.confirm_send != "SEND_163_BATCH":
                print("send 模式必须提供 --confirm-send SEND_163_BATCH。", file=sys.stderr)
                return 2
            command = [
                sys.executable,
                str(SEND_SCRIPT),
                str(args.manifest),
                "--confirm-send",
                "SEND_163_BATCH",
                "--log-path",
                str(args.log_path),
                "--smtp-host",
                args.smtp_host,
                "--smtp-port",
                str(args.smtp_port),
            ]
        return subprocess.run(command, env=child_env, check=False).returncode
    finally:
        code = ""
        child_env["163_JOB_APPLY_AUTH_CODE"] = ""


if __name__ == "__main__":
    raise SystemExit(main())
