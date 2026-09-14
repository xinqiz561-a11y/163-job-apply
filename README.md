# 163-job-apply

一个面向 Codex 的 163.com 求职简历邮件投递 skill/plugin。

它把“岗位来源核验 → 清单校验 → 个性化邮件草稿 → 人工确认 → 163 SMTP
发送 → 私有 JSONL 结果记录”封装成可复用流程。项目只支持 163 邮箱，暂不
包含 Gmail、Outlook 或招聘网站自动填表。

## 功能

- 核验企业、岗位、收件邮箱和来源，并结合用户自行填写的专业与背景校验岗位匹配理由；
- 自动生成主题、正文并附加 PDF 简历；
- 默认只预览，不连接 SMTP；
- 真实发送需要确认清单状态和精确确认词；
- 通过幂等键避免同一批次和已有日志中的重复发送；
- 支持 Windows Credential Manager，授权码只在发送进程中读取；
- 不向仓库写入真实简历、手机号、账号、授权码或投递日志。

## 环境

- Python 3.10 或更高版本；
- 163 邮箱已开启客户端服务；
- 163 客户端授权码（不是网页登录密码）；
- Windows Credential Manager 方案需要 `pywin32`：

```powershell
python -m pip install pywin32
```

## 快速使用

1. 复制 `examples/candidates.example.json`，在 `profile` 中填写自己的专业、学历和毕业届次，并替换为自己的岗位清单与简历路径。专业不限，由用户自行选择或填写。
2. 在本机校验清单：

```powershell
python skills/163-job-apply/scripts/validate_candidates.py .\candidates.json --require-send-ready
```

3. 生成预览：

```powershell
python skills/163-job-apply/scripts/build_application_emails.py .\candidates.json --resume .\resume.pdf --output .\preview.json
```

4. 人工检查 `preview.json`，确认精确的候选项后，把根对象的
   `approval_state` 改成 `confirmed`，并填写 `approved_at`、`approved_by`。
5. 先做 dry-run：

```powershell
python skills/163-job-apply/scripts/send_confirmed_batch.py .\preview.json --dry-run --log-path .\private\send-log.jsonl
```

6. Windows 上验证并保存授权码：

```powershell
python skills/163-job-apply/scripts/store_163_auth_code.py --email yourname@163.com
python skills/163-job-apply/scripts/send_with_stored_credential.py --email yourname@163.com --mode test-connection
```

7. 发送已确认批次：

```powershell
python skills/163-job-apply/scripts/send_with_stored_credential.py `
  --email yourname@163.com `
  --mode send `
  --manifest .\preview.json `
  --log-path .\private\send-log.jsonl `
  --confirm-send SEND_163_BATCH
```

也可以只在当前进程设置 `163_JOB_APPLY_EMAIL` 和
`163_JOB_APPLY_AUTH_CODE`，然后直接运行 `send_confirmed_batch.py`；不要把
这两个变量写进仓库文件。

## 测试

测试不连接真实邮箱：

```powershell
python skills/163-job-apply/scripts/test_skill.py
```

CI 只运行离线校验和发送保护测试，不保存或使用任何真实邮箱凭据。

## 安全边界

- “SMTP accepted”不等于对方已读或已入箱；
- 不猜测邮箱，不把网申岗位伪装成邮件投递；
- 不使用 BCC 或隐藏收件人；
- 不在日志中保存正文、简历内容、密码或授权码；
- 批量发送仍需要人工确认，默认最多 10 个候选项。

详细规则见 `skills/163-job-apply/SKILL.md`、`SECURITY.md` 和
`skills/163-job-apply/references/`。
