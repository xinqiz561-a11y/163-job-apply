#!/usr/bin/env python3
"""Build individualized plain-text application drafts; never sends email."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"profile": {}, "candidates": data}
    if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
        raise ValueError("JSON 根对象必须包含 candidates 数组")
    return data


def compose_body(profile: dict[str, Any], candidate: dict[str, Any]) -> str:
    name = str(profile.get("name", "")).strip() or "求职者"
    major = str(profile.get("major", "")).strip()
    degree = str(profile.get("degree", "")).strip()
    graduation = str(profile.get("graduation", "")).strip()
    phone = str(profile.get("phone", "")).strip()
    email = str(profile.get("email", "")).strip()
    company = str(candidate.get("company", "")).strip()
    position = str(candidate.get("position", "")).strip()
    reason = str(candidate.get("match_reason", "")).strip()

    identity = "，".join(value for value in (degree, major, graduation) if value)
    lines = [
        f"尊敬的{company}招聘负责人：",
        "",
        f"您好！我叫{name}" + (f"，是{identity}学生。" if identity else "。"),
        f"了解到贵公司正在招聘“{position}”岗位，我希望申请该岗位。",
    ]
    if reason:
        lines.extend(["", f"岗位匹配说明：{reason}"])
    lines.extend(
        [
            "",
            "附件为我的个人简历，恳请您查收。如有机会，我希望进一步介绍自己的学习和实践经历。",
            "",
            "感谢您的时间，期待您的回复！",
            "",
            f"{name}",
        ]
    )
    if phone:
        lines.append(f"电话：{phone}")
    if email:
        lines.append(f"邮箱：{email}")
    return "\n".join(lines)


def build(manifest: dict[str, Any], resume: str | None) -> dict[str, Any]:
    profile = manifest.get("profile") or {}
    output_candidates = []
    for index, original in enumerate(manifest["candidates"], start=1):
        candidate = dict(original)
        candidate_id = str(candidate.get("id") or f"candidate-{index:03d}")
        company = str(candidate.get("company", "")).strip()
        position = str(candidate.get("position", "")).strip()
        recipient = str(candidate.get("to", "")).strip().casefold()
        attachment = candidate.get("resume_path") or candidate.get("attachment_path") or resume
        key_material = "|".join((candidate_id, company, position, recipient, str(attachment or "")))
        candidate["id"] = candidate_id
        suffix = f"（{profile['major']}）" if profile.get("major") else ""
        candidate["subject"] = str(
            candidate.get("subject_override")
            or f"应聘{position}——{profile.get('name', '求职者')}{suffix}"
        )
        candidate["body"] = str(candidate.get("body_override") or compose_body(profile, candidate))
        candidate["attachment_path"] = attachment
        candidate["idempotency_key"] = hashlib.sha256(key_material.encode("utf-8")).hexdigest()[:20]
        output_candidates.append(candidate)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "approval_state": "preview",
        "profile": profile,
        "candidates": output_candidates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", type=Path)
    args = parser.parse_args()

    manifest = load_manifest(args.input)
    result = build(manifest, str(args.resume) if args.resume else None)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "count": len(result["candidates"]), "approval_state": "preview"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
