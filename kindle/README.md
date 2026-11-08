# Kindle 天气日历看板

KUAL + FBInk，支持竖屏 1072×1448、横屏 1448×1072，由菜单直接选择，不检测屏幕方向。时间区域仅显示城市与时间，农历信息集中在日历区域。

## 运行与退出

安全推出 USB 磁盘并拔线，在 KUAL → 窗边 InkDesk 选择「每日报告（竖屏）」或「每日报告（横屏）」。KUAL 关闭后显示看板；先显示缓存页面，再获取天气。

**按电源键退出看板并返回主页。** 使用 stock powerd 的 `outOfScreenSaver` / `goingToScreenSaver` 事件区分用户电源操作与看板自身请求的休眠、网络唤醒。RTC 的 `wakeupFromSuspend` 事件只通知刷新，不退出。没有触摸监听、触摸输入读取或抓取，也没有双击退出。

系统界面在看板期间临时暂停绘制，退出时恢复；不停止 framework，不改变开机配置。停止菜单同样可恢复；USB 根目录空文件 `STOP_DASHBOARD` 也可请求停止。

## 刷新规则

启动时立即显示一次，然后按本地时间 **00、10、20、30、40、50 分**更新时间。等待时间为 `下一个十分钟整点 - 当前时间`，会计入秒数。例如：

- 14:52:00 → 15:00:00，等待 8 分钟；
- 14:52:34 → 15:00:00，等待 7 分 26 秒；
- 14:50:00 启动先显示一次，下一次为 15:00:00；
- 绘制或网络处理延迟后重新计算下一个整点，不持续累计偏差。

当前 Asia/Tokyo 时区的偏移是 600 秒的整数倍，使用 epoch 600 秒边界与当地十分钟整点完全一致。休眠提前唤醒时，仍等到整点才更新时间。补绘时保留上次显示的时钟值。

每日报告模式由 Kindle 每天凌晨 01:00 直接更新天气，并下载私有 GitHub 最新报告。日历按本机日期绘制。时钟、电量每十分钟整点同步更新，额外重绘沿用缓存电量。断网保留缓存，失败一小时后重试。

## 省电

保留 Kindle 自动休眠。默认 `DASH_LOW_POWER=1`，仅在 `readyToSuspend` 阶段通过 `rtcWakeup` 安排下一个十分钟整点的唤醒。全程不写 `/sys/power/state`，不调整前光。Wi-Fi 只在获取天气时开启，完成后关闭，退出恢复原开关状态。

系统拒绝 RTC 调度或缺少接口时退回常醒兼容模式，记录 `power: compatibility fallback`。独立电源键事件监听在兼容模式下仍保持运行。`dashboard.log` 中连续的 `RTC armed` 和 `resume received` 才能确认实机定时唤醒成功；调度成功不代表耗电量已经验证。

参考：[KOReader Kindle 电源流程](https://github.com/koreader/koreader/blob/master/frontend/device/kindle/powerd.lua)。没有采用实验项目直接写内核 `mem` 状态的循环。

## 开发和验证

- `python3 kindle/generate_assets.py`：生成背景和图标，需 Pillow、设备字体或私有备份字体。
- `ZIG=/path/to/zig sh kindle/native/build.sh`：编译 ARM 静态绘图程序和事件等待程序，并生成用于预览的本机版本。
- `python3 kindle/preview.py` / `python3 kindle/preview.py --landscape`：使用相同 C 绘图代码生成示例预览、验证时钟局部图像。
- `python3 kindle/test_startup.py`：菜单选方向、暂停/恢复进程所有权。
- `python3 kindle/test_power.py`：RTC 事件调度、失败恢复、网络开关顺序与 Wi-Fi 恢复。
- `python3 kindle/test_schedule.py`：十分钟对齐、秒数、整点、跨日及绘制延迟。
- `python3 kindle/test_button_exit.py`：电源键返回、忽略程序请求的休眠/唤醒及 RTC 唤醒。
- `python3 kindle/install.py`：备份、安装并校验，删除旧触摸监听二进制。保留设备私有 config.sh、字体和天气脚本。

备份在 `.device-config/kindle-backups/`，包含私有配置，请勿提交。USB 模式下无法执行 Kindle 程序；电源键、定时唤醒与耗电必须退出 USB 后实测。
