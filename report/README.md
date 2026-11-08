# 私有 GitHub 日报 → Kindle

电脑每天日本时间 20:00 生成 JSON，通过本机 SSH 上传到私有仓库的 `reports` 分支。Kindle 用单独的只读令牌从 GitHub Contents API 下载，校验后本地绘制。**不开启 GitHub Pages。** 本机网页仅用于预览。

## 还需配置

1. 创建或指定私有仓库，在 `report/config.local.json` 的 `github_repository` 填 `用户名/仓库名`。仓库 Pages 必须关闭；上传脚本会在推送前确认仓库为私有且 `has_pages=false`，否则拒绝上传。当前电脑 SSH 已验证为 `lacehahn`，负责写入。
2. 在 GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens 创建令牌：只选择这个仓库，Repository permissions 只授予 **Contents: Read-only**（Metadata 只读由 GitHub 默认提供）。不要授予写入或其他仓库权限。
3. 将令牌独占一行保存到本机 `.device-config/github-read-token`，文件已创建为空且权限为 600。不要贴到聊天，不要提交到 Git。该令牌用于验证私有仓库和 Kindle 下载，电脑上传依然走 SSH。
4. DeepSeek 余额可选：建议运行 `python3 report/configure_deepseek.py` 同步配置。也可在本机 `.device-config/report-secrets.json` 保存 `{"DEEPSEEK_API_KEY":"你的Key"}`，权限 600。DeepSeek 只显示接口返回的各币种剩余余额，分别列出，不换算。缺项显示未配置。
5. 城市默认东京；需要时修改 city、latitude、longitude、timezone。Codex 用量只提取本地会话日志中的百分比与快照时间，不读 auth.json、不上传原始会话。

## 执行

```sh
python3 -m pip install -r report/requirements.txt
python3 report/run.py                     # 只在本机生成
python3 report/run.py --publish           # 验证私有属性后通过 SSH 上传
python3 report/preview.py                 # 原生横屏预览
python3 report/preview.py --portrait      # 原生竖屏预览
# 可用 --weather 指向 weatherread 验证输出，检查设备天气覆盖层
python3 -m http.server 8080 --bind 127.0.0.1 --directory report/output
```

当前由 Mac 本地执行：每天日本时间 20:00 的 crontab，加上用户登录后执行一次的 LaunchAgent。旧 Codex 自动任务已移除，不需要 Codex 保持运行。独立运行目录、日志、启停和更新方式见 [LOCAL_TASKS.md](LOCAL_TASKS.md)。DeepSeek Key 的隐藏输入配置命令见 [DEEPSEEK.md](DEEPSEEK.md)。

## Kindle 安装

接入 USB 磁盘模式后：

```sh
python3 kindle/install.py
python3 report/prepare_device.py
```

配置程序会再次验证仓库隐私，写入设备的 `dashboard/report.conf` 和 `dashboard/report-auth.conf`；不在输出里显示令牌。只读令牌不会进入报告或 Git 仓库。不要把电脑的 SSH 私钥或 DeepSeek Key 放到 Kindle。

安全推出并拔线，KUAL → 窗边 InkDesk → 每日报告（横屏）或每日报告（竖屏），菜单直接决定方向。启动时下载，随后每日凌晨 01:00（日本时间）由 Kindle 直接获取最新天气，并从 GitHub 检查最新用量报告；不依赖 Mac 凌晨在线。两项独立保留缓存，失败一小时后重试。用量报告正常为前一晚 20:00 生成。时钟、电量来自 Kindle；启动时读取一次，然后每十分钟整点同时更新，额外重绘不读取电量；电源键返回主页，无触摸检测。

## 数据与完整性

- report.json 为真实 JSON；GitHub 请求使用 `Accept: application/vnd.github.raw+json` 获取原始内容，不把 API 默认的 Base64 包装当作报告。
- 图片在 `bundles/<asset_bundle>/`，文件名和 SHA-256 摘要写入 JSON；同一份报告引用不可变的图片包，避免跨次上传混用资源。
- Kindle 下载后先校验 JSON、所有图片哈希及命令引用，再切换完整缓存指针。下载失败、图片缺失或摘要不匹配不会覆盖旧报告。
- Git 只暂存 report.json 和图片 bundle，不上传网页、配置、令牌、原始会话或项目源码。查看页面请在本机预览。
- 数据源失败时沿用先前快照并标注 stale；无可用值则显示未配置，不从账户余额反推消费。

本机检查：`python3 -m unittest discover -s report -p 'test_*.py'`。已覆盖私有/公开仓库限制、真实 JSON/图片原样传输、Base64 包装拒绝、损坏/缺失图片保留旧缓存、令牌不进入命令行参数或报告。

参考：[GitHub Contents API 及只读权限](https://docs.github.com/en/rest/repos/contents#get-repository-content)、[创建 fine-grained token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)、[DeepSeek 余额 API](https://api-docs.deepseek.com/api/get-user-balance/)。

横屏按 KPW3 的 1448×1072 画布排版，顶部卡片延伸至 y=548，底部卡片至 y=1054，屏幕下边距为18像素。天气下载使用严格 JSON 校验，当前实况和三天预报完整后才替换持久缓存；日历始终由 Kindle 本机日期绘制。
