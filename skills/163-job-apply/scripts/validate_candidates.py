#!/usr/bin/env python3
"""Validate a 163 job-application candidate manifest without sending mail."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


EMAIL_RE = re.compile(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")
REQUIRED = ("company", "position", "to", "source_url", "match_reason")


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"profile": {}, "candidates": data}
    if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
        raise ValueError("JSON 根对象必须包含 candidates 数组")
    return data


def valid_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate(manifest: dict[str, Any]) -> dict[str, Any]:
    candidates = manifest["candidates"]
    rows = []
    seen: set[tuple[str, str, str]] = set()
    error_count = 0
    warning_count = 0

    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            rows.append({"index": index, "errors": ["候选项必须是对象"]})
            error_count += 1
            continue

        errors: list[str] = []
        warnings: list[str] = []
        for field in REQUIRED:
            if not str(candidate.get(field, "")).strip():
                errors.append(f"缺少 {field}")

        recipient = str(candidate.get("to", "")).strip()
        if recipient and not EMAIL_RE.fullmatch(recipient):
            errors.append("收件邮箱格式无效")

        if candidate.get("source_url") and not valid_url(candidate["source_url"]):
            errors.append("source_url 必须是 http/https 链接")

        if candidate.get("email_verified") is not True:
            warnings.append("邮箱尚未标记为已核验，禁止发送")

        attachment = candidate.get("resume_path") or candidate.get("attachment_path")
        if attachment:
            if not Path(str(attachment)).is_file():
                errors.append("简历附件不存在")
        else:
            warnings.append("尚未指定简历附件")

        key = (
            recipient.casefold(),
            str(candidate.get("company", "")).strip().casefold(),
            str(candidate.get("position", "")).strip().casefold(),
        )
        if key in seen:
            errors.append("与前面候选项重复")
        elif recipient:
            seen.add(key)

        error_count += len(errors)
        warning_count += len(warnings)
        rows.append(
            {
                "index": index,
                "id": candidate.get("id") or f"candidate-{index:03d}",
                "company": candidate.get("company"),
                "position": candidate.get("position"),
                "to": recipient,
                "errors": errors,
                "warnings": warnings,
                "valid_for_preview": not errors,
                "valid_for_send": not errors and candidate.get("email_verified") is True and bool(attachment),
            }
        )

    return {
        "candidate_count": len(candidates),
        "error_count": error_count,
        "warning_count": warning_count,
        "valid_for_preview": error_count == 0,
        "valid_for_send": error_count == 0 and all(row.get("valid_for_send", False) for row in rows),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-send-ready", action="store_true")
    args = parser.parse_args()

    try:
        report = validate(load_manifest(args.input))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)

    if args.require_send_ready and not report["valid_for_send"]:
        return 1
    return 0 if report["valid_for_preview"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
