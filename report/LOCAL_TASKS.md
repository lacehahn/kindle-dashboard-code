# Mac 本地执行

当前已启用两个触发入口：

- 用户登录 Mac 后执行一次：`~/Library/LaunchAgents/dev.inkdesk.report.login.plist`，使用 RunAtLoad；首次加载也会执行一次。
- 每天日本时间 20:00：用户 crontab 中的 `INKDESK_PRIVATE_REPORT` 条目。

crontab 本身支持 `@reboot`，但本项目按用户选择采用登录后的 LaunchAgent，这样任务运行在用户环境中。登录后先等 15 秒，网络失败时再等 30、60 秒重试，总计最多三次；没有常驻循环或 KeepAlive。两个入口共用文件锁，同时触发时其中一个跳过。

电脑需要开机、可执行任务并联网，Codex 不需要运行。定时任务不会唤醒已休眠的 Mac。20:00 由当前 Mac 的 JST 系统时区调度；若更改系统时区应重新确认执行时间。

## 运行位置

独立运行目录：`~/Library/Application Support/InkDesk`。

这个目录包含专用 Python venv、脚本、天气/农历资源、单独的私有仓库工作区以及凭据。任务不依赖 Documents 下的开发目录，也不加载终端配置或 SSH agent 环境。

日志：`~/Library/Application Support/InkDesk/logs/daily-report.log`。超过 2 MB 时保留一个旧日志文件。登录启动器的异常日志为同目录 `login-launch.log`。旧 Codex 自动任务已移除。

## 更新与选择

在项目目录执行：

```sh
# 更新独立运行副本并验证上传，保留已有登录启动设置
python3 report/install_cron.py

# 更新运行副本，启用登录后执行，保留每日20:00
python3 report/install_cron.py --startup login

# 关闭登录后执行，只保留每日20:00
python3 report/install_startup.py --disable

# 重新开启登录后执行
python3 report/install_startup.py --enable

# 手动立即执行一次，输出记录到日志
/bin/sh "$HOME/Library/Application Support/InkDesk/report/daily-report.sh"

# 查看日程
crontab -l
```

`install_cron.py` 会先在最小环境下真实生成并上传一份私有报告，成功后才更新日程；相同 crontab 不重复写入。它仅修改自己标记的条目，并备份原 crontab。修改项目配置或脚本后需要再次安装，才能同步到独立运行目录。
