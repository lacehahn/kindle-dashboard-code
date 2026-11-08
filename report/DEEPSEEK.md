# DeepSeek 配置

## 自动查询余额

1. 在 DeepSeek 开放平台创建 API Key：https://platform.deepseek.com/ 。这应是开放平台 API Key，不是 GitHub 令牌或网页登录 Cookie。
2. 在本机终端执行：

```sh
python3 "/Users/lance/Documents/ChatGPT/InkNotifer/report/configure_deepseek.py"
```

3. 按提示粘贴 Key，输入不会显示。程序先调用 `GET https://api.deepseek.com/user/balance` 验证，成功后把 Key 同步保存到项目 `.device-config/report-secrets.json` 和已安装运行目录的同名私有文件，权限为 600。它不会显示 Key，也不会将 Key 写入报告或推送到 GitHub。
4. 立即生成并更新一次报告（也可以等待下次登录或20:00）：

```sh
/bin/sh "$HOME/Library/Application Support/InkDesk/report/daily-report.sh"
```

不需要重新安装定时任务。Key 无效或网络验证失败时不保存新 Key，不影响原配置。不要把 Key 发送到聊天。

## 显示内容

看板仅显示接口实际返回的各币种总可用余额，例如 CNY 与 USD 分别列出，不换算、不相加。没有返回的币种不会填零。未配置 Key 时显示“未配置”；请求失败时保留上次余额快照。

接口还提供赠送余额、充值余额及是否可用，但看板不展示这些明细。它不提供本周消费和累计 Tokens。旧的本地消费汇总不再用于界面。

官方文档：https://api-docs.deepseek.com/api/get-user-balance/ 。
