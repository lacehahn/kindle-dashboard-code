# Kindle Dashboard / InkDesk

适用于已越狱 Kindle Paperwhite 3 的天气、日历与账户余额看板。KUAL 菜单直接选择横屏或竖屏，以 FBInk 和原生栅格绘图程序显示，支持 stock powerd 定时唤醒。

- 横屏 1448×1072、竖屏 1072×1448；时间、电量在启动时读取一次，之后每十分钟整点同步更新。
- Kindle 每天凌晨 01:00（日本时间）直接获取天气，并读取私有 GitHub 仓库中的最新报告；失败保留缓存并重试。
- Mac 本地脚本在登录后执行一次，并由 crontab 每天 20:00 生成、上传 JSON 报告。
- Codex 周额度、重置时间；DeepSeek 按接口返回币种分别显示剩余余额。
- 电源键退出并返回主页，无触摸检测。

## 文档

- [Kindle 安装、显示与省电](kindle/README.md)
- [本地报告与私有 GitHub 数据传输](report/README.md)
- [Mac 定时任务](report/LOCAL_TASKS.md)
- [DeepSeek 配置](report/DEEPSEEK.md)
- [原生程序构建](kindle/native/README.md)

`kindle/` 包含设备脚本、绘图资源、ARM 程序与 C 源码；`report/` 包含报告生成、账户数据读取、本地预览及定时任务安装器。

## 本地配置

复制 `report/config.example.json` 为 `report/config.local.json` 后按文档配置。项目不会提交实际 GitHub 下载配置、令牌、API Key、设备备份、报告快照或账户数据。代码仓库与存放实际报告的私有数据仓库分开使用；不要将私有报告发布到 GitHub Pages。

已有设备安装器会备份现有文件并保留设备配置；它不是未配置设备的一键安装包，具体前置要求见 Kindle 文档。

## 检查

```sh
python3 -m unittest discover -s report -p 'test_*.py'
python3 kindle/test_schedule.py
python3 kindle/test_report_local.py
python3 kindle/test_report_weather.py
```

原生测试需要先按原生构建文档编译 host 程序，报告测试使用本地生成的报告作为夹具。

工作区还保留了 Android 通知转发伴随应用源码（`app/`、Gradle、`scripts/`），说明见 [Android 文档](docs/android-notifier.md)。设备测试输出、APK 和配对配置不随源码提交。
