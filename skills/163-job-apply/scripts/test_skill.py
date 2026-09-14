#!/usr/bin/env python3
"""Offline regression tests for the 163-job-apply skill."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VALIDATE = ROOT / "validate_candidates.py"
BUILD = ROOT / "build_application_emails.py"
SEND = ROOT / "send_confirmed_batch.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="163-job-apply-test-") as folder:
        temp = Path(folder)
        resume = temp / "resume.pdf"
        resume.write_bytes(b"%PDF-test")
        source = temp / "candidates.json"
        preview = temp / "preview.json"
        log = temp / "sent.jsonl"
        source.write_text(
            json.dumps(
                {
                    "profile": {
                        "name": "测试候选人",
                        "major": "土木工程",
                        "degree": "硕士",
                        "graduation": "2027届",
                        "phone": "13800000000",
                    },
                    "candidates": [
                        {
                            "id": "demo-001",
                            "company": "示例工程公司",
                            "position": "项目管理岗",
                            "to": "hr@example.com",
                            "email_verified": True,
                            "source_url": "https://example.com/jobs",
                            "match_reason": "涉及项目协调，土木背景可迁移。",
                            "resume_path": str(resume),
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        checked = run(str(VALIDATE), str(source), "--require-send-ready")
        assert checked.returncode == 0, checked.stderr or checked.stdout

        built = run(str(BUILD), str(source), "--output", str(preview))
        assert built.returncode == 0, built.stderr or built.stdout
        manifest = json.loads(preview.read_text(encoding="utf-8"))
        assert manifest["approval_state"] == "preview"
        assert manifest["candidates"][0]["subject"]
        assert manifest["candidates"][0]["body"]
        assert manifest["candidates"][0]["idempotency_key"]

        dry = run(str(SEND), str(preview), "--dry-run")
        assert dry.returncode == 0, dry.stderr or dry.stdout
        dry_report = json.loads(dry.stdout)
        assert dry_report["ready"] is True
        assert len(dry_report["would_send"]) == 1

        log.write_text(
            json.dumps(
                {
                    "id": "demo-001",
                    "idempotency_key": manifest["candidates"][0]["idempotency_key"],
                    "status": "sent",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        repeated = run(str(SEND), str(preview), "--dry-run", "--log-path", str(log))
        assert repeated.returncode == 0, repeated.stderr or repeated.stdout
        repeated_report = json.loads(repeated.stdout)
        assert len(repeated_report["would_send"]) == 0
        assert repeated_report["skipped"][0]["reason"] == "已发送或本批次重复"

        blocked = run(
            str(SEND),
            str(preview),
            "--confirm-send",
            "SEND_163_BATCH",
            "--log-path",
            str(log),
        )
        assert blocked.returncode != 0
        assert "approval_state" in blocked.stderr

    print("PASS: validation, draft generation, dry-run, deduplication, and send guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
