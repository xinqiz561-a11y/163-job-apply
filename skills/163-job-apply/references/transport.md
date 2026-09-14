# 163 SMTP 传输

163 SMTP 发送使用客户端授权码，不使用网页登录密码。

- 常见服务器：`smtp.163.com`
- 常见 SSL 端口：`465`
- 发送前应以 163 邮箱“客户端设置”页面显示的参数为准。
- 授权码应通过 Windows Credential Manager 或运行时环境变量提供。
- 不要把授权码写入 JSON、PowerShell 历史、命令行参数、日志或 Git。

发送器默认 dry-run。真实发送必须同时满足：

1. 清单已验证；
2. 附件存在；
3. 邮箱已经核验；
4. `approval_state` 为 `confirmed` 且有批准信息；
5. 提供 `--log-path`；
6. 提供精确确认词 `SEND_163_BATCH`。

日志中的 `status: sent` 表示 SMTP 服务接受了邮件，不等于对方邮箱已经
投递、阅读或回复。
