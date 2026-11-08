## 0.1.1 更新

界面统一使用主设备 / 从设备；在「设备 → 隐藏待机通知」中关闭「同步连接状态」类别，后台同步及新消息通知继续运行。系统后台任务管理仍可能显示应用运行状态。

# 墨信 / InkNotifier

把小米 14 的系统通知，经免费开源 ntfy 通道加密同步到 Bigme HiBreak。两台手机各自有移动数据或 Wi-Fi 即可，无需同一局域网。原生 Android APP（Java + Android Views），同一 APK 分发送端和接收端，最低 Android 8.1。

## 已实现的 0.1.0

- 应用通知白名单，默认微信与常见短信应用；首次授权不上传旧通知。
- AES-256-GCM 端到端认证加密；配对密钥由 Android Keystore 加密保存；关闭备份及设备迁移。
- HTTPS ntfy 发布和持续订阅，不依赖 Google 推送服务，也不使用 USB 转发网络。
- 本地待发队列、接收端持久化确认、断线重试、重复通知去重、同一通知原位更新。
- 网络切换触发重连；仅在消息处理时申请最多 30 秒的短时 CPU 唤醒，队列确认后提前释放。发送后可短时查询确认，兼容厂商延迟后台订阅连接的情况。
- 黑白大字收件箱、搜索、未读筛选、本地已读与删除、阅读模式静默通知。
- 7 天历史和消息有效期、连接诊断、测试消息、重连及解除配对。
- 开机及 APP 更新后尝试恢复用户已开启的同步；进程被强制停止或厂商限制恢复时，需解锁并打开 APP。

本版使用配对码，USB 调试时可由脚本自动配对；二维码和蓝牙直连尚未实现。重要联系人例外提醒、远程回复、同步清除主力机通知也尚未实现。

## 手机上怎么用

1. 两台安装同一个 APK，小米选择「主力机」，创建配对；HiBreak 选择「墨水屏手机」，输入小米提供的配对码。配对码含密钥，仅交给自己的设备。
2. 小米允许「读取通知」，选择要转发的应用，然后开启同步。
3. HiBreak 开启接收并允许显示通知。可开启阅读模式，让新消息静默进入通知栏和收件箱。
4. 在小米点击「发送测试消息」。等待小米页面出现「设备确认收到」，并在 HiBreak 刷新收件箱。
5. 在两机应用设置中允许后台运行；HyperOS 还需检查自启动及电池管理。应用会显示常驻连接通知。

锁屏默认使用隐藏内容的公开通知版本。本地标记已读不会修改微信等原应用的聊天已读状态。图片、语音、音视频通话不转发。Android 15+ 敏感通知可能被系统隐藏，不能保证同步验证码。长通知会按 ntfy 的消息大小限制截短，并显示省略号。

默认转发服务是 ntfy.sh，免费服务受额度和可用性限制。支持无鉴权、可写可订阅的 HTTPS 自托管 ntfy；此版未提供服务端账号/令牌设置。自托管软件免费，服务器和移动数据可能产生费用。随机主题与认证加密共同降低风险，但免费公共主题没有服务端访问控制，不能保证抵御主题被泄露后的恶意限流。

## 构建

需要 JDK 17、Android SDK Platform 35 / Build Tools 35.0.0。Gradle Wrapper 使用 8.11.1，Android Gradle Plugin 8.9.3。

```sh
# local.properties 中配置 sdk.dir，或设置 ANDROID_HOME
./scripts/build.sh assembleDebug testDebugUnitTest lintDebug
```

输出：`app/build/outputs/apk/debug/app-debug.apk`。当前依赖仅 AndroidX Core 和 OkHttp；不需要 Android Studio 或付费推送 SDK。使用 Android Studio 导入此目录也可以开发。

## 当前电脑与真机调试

已安装 Homebrew JDK 17、Android command-line tools、SDK 35、Build Tools、ADB。最新 ADB 37 在本机曾发生 USB 读取崩溃，项目调试脚本优先使用 Google 官方 ADB 35.0.2，存放在 `~/.cache/inknotifier/adb35/platform-tools`。可用 `INK_ADB` 指定其他 ADB。

```sh
./scripts/adb.sh devices -l
./scripts/adb.sh -s DEVICE_SERIAL install -r app/build/outputs/apk/debug/app-debug.apk

# 仅调试 APK 支持私有文件导入；不在命令行或日志中输出配对密钥
python3 scripts/provision_devices.py --sender SENDER_SERIAL --receiver RECEIVER_SERIAL

# 从当前 UI 树读取控件位置并操作，不硬编码点击坐标
python3 scripts/device_ui.py DEVICE_SERIAL
python3 scripts/device_ui.py DEVICE_SERIAL --tap '开始同步'

# 两台先完成配对并开启同步；会创建合成测试通知和重启接收端
python3 scripts/smoke_devices.py --sender SENDER_SERIAL --receiver RECEIVER_SERIAL --mobile
```

`--mobile` 会暂时关闭两机 Wi-Fi，检查移动网络及主力机熄屏接收，然后恢复先前开启的 Wi-Fi。测试不读取其他应用聊天数据库。设备状态测试只输出测试消息和队列计数。设备截图、密钥和临时数据库不提交 Git。`.device-config/pair.json` 包含此配对的共享密钥，目录及文件权限限制为当前用户；换电脑后重新配对即可。

## 项目结构

- `MainActivity`：角色与配对、控制、应用选择、收件箱及阅读界面。
- `NotificationBridge`：Android 通知监听与过滤。
- `SyncService`：remoteMessaging 前台服务，HTTPS 转发和订阅、接收确认及系统提醒。
- `Store`：SQLite 持久化队列、通知实例版本、收件箱、已处理事件。
- `Crypto` / `Protocol`：认证加密、协议验证、长度限制、有效期。
- `Config`：HTTPS 地址验证、密钥保护、配对码与调试导入。

## 验证记录

单元测试覆盖密文往返、随机 IV、防篡改、错误密钥、协议方向及过期拒绝、中文/emoji 截断和 JSON 转义后的长度限制。构建、五项单元测试和 Android Lint 已通过。Lint 仍有中文文案国际化、同步写入少量配对设置和电池优化豁免等提示；本版用于个人侧载调试。

2026-10-12 最后一轮两台真机的 8 项检查全部通过：系统通知、重复去重、原位更新、接收确认、停止进程后补收和缓存重放、两机关闭 Wi-Fi 的移动网络同步、两机熄屏的移动网络同步、最终队列清空。移动网络在亮屏状态观察到约 2.16 秒到达；发送前小米为 Dozing、Bigme 为 Asleep 时观察到约 12.53 秒到达，接收确认也成功返回。延迟是本次测试样本，不是保证值。测试后恢复原来开启的 Wi-Fi。本地测试记录和 APK 不随源码提交。

还检查了 ntfy 缓存中的测试数据，确认消息负载均为密文且未超过消息大小限制，测试记录仅保存在本地。短时熄屏测试不能代表长时间 Doze 或 24 小时耗电；重启设备、长时间待机、微信真实消息以及不同运营商网络仍需继续实测。
