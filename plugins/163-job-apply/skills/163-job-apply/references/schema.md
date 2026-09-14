# 163 求职投递清单

输入文件是 UTF-8 JSON，根对象包含 `profile` 和 `candidates`。

```json
{
  "profile": {
    "name": "示例候选人",
    "major": "土木工程",
    "degree": "硕士",
    "graduation": "2027届",
    "phone": "13800000000",
    "email": "candidate@example.com"
  },
  "candidates": [
    {
      "id": "demo-company-project-001",
      "company": "示例工程公司",
      "position": "项目管理岗",
      "to": "hr@example.com",
      "email_verified": true,
      "source_url": "https://example.com/careers",
      "email_source": "企业官方招聘页",
      "match_reason": "岗位涉及项目协调和现场管理，土木工程背景可迁移。",
      "resume_path": "C:\\path\\to\\resume.pdf"
    }
  ]
}
```

## 必填字段

每个候选项必须有：`company`、`position`、`to`、`source_url`、
`match_reason` 和 `email_verified`。

`email_verified` 不是 `true` 时可以生成预览，但不能发送。缺少邮箱的
网申岗位应保留在其他清单中，不能转换成猜测的收件地址。

## 生成清单

`build_application_emails.py` 会保留原字段并补充 `id`、`idempotency_key`、
`subject`、`body` 和 `attachment_path`。根对象会包含 `generated_at`、
`approval_state`、`profile` 和 `candidates`。

## 审批和历史日志

生成后的 `approval_state` 必须为 `preview`。用户确认精确批次后，才可以改为
`confirmed`，并填写 `approved_at` 和 `approved_by`。发送日志只保存候选 ID、
公司、岗位、收件邮箱、时间、状态和幂等键，不保存正文、简历内容、密码或
163 客户端授权码。日志文件应放在私有目录，不要提交到 GitHub。
