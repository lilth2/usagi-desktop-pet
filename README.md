# 吉伊卡哇桌宠 · Chiikawa

在现有 PyQt5 桌宠项目上换肤，保留透明置顶、拖拽、小范围散步、离线关怀、菜单开关和退出。新增本地时间问候、时间外观、持久化设置和身体部位动画。没有网络服务、付费 API 或音频。

## 启动

Windows 双击 `dist/ChiikawaPet.exe`（本地构建产物），或在已配置的本机双击 `启动吉伊卡哇.bat`。旧的 `启动乌萨奇.bat` 继续兼容，打开同一新版程序。

源码运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python desktop_pet.py
```

## 交互与设置

- 双击：随时遍历全部7张图片，时间规则仅用于启动选图。同轮无重复，下一轮首张避开上一张；双击同时弹出当前时段关怀语，手动文案独立轮播，不推进自动文案或五分钟计时。
- 左键拖动：抓起时等比缩小，松手恢复；最后放下的位置成为散步中心。
- 散步：左右各 30 像素内折返，每次 8–14 秒，间隔 15–30 秒。
- 关怀：Windows 读取距离最后一次键鼠输入的时间，持续使用约 30 分钟提醒一次；空闲 5 分钟或休眠长间隔重置。只读空闲时间，不读键鼠内容，不保存使用记录。
- 右键菜单：关怀开关、一句暖心话、散步开关、陪伴与时间设置、退出。
- 设置页：陪伴、外观时间、时间问候。可编辑时间段、默认问候、多条文案以及深夜素材选择。
- 睡眠外观暂停散步/闲置摇摆，提醒计时照常；单击保留轻柔动画反馈，时间状态不会被永久改变。

关怀气泡按桌宠大小自动收缩（常见文案约168×71逻辑像素），带指向角色的尾巴；长文限高滚动。快速双击只更新一个气泡，重要提醒优先。

## 默认时间表

采用电脑当前本地时间，包含开始、不包含结束。

| 问候 | 时间 |
|---|---|
| 早上好 | 06:00–11:00 |
| 中午好 | 11:00–14:00 |
| 下午好 | 14:00–18:00 |
| 晚上好 | 18:00–次日06:00 |

| 外观 | 时间 / 素材 |
|---|---|
| 午睡 | 12:30–14:00，5.png |
| 夜间睡眠 | 23:00–次日06:00，5.png |
| 晚间清醒 | 18:00–23:00，1.png / 7.png 中间背向角色（深夜初始偏好可选，轮播包含全部合规素材） |
| 普通 | 其余时间，3.png 中间的吉伊卡哇；双击可选2/4/6透明角色和相关电脑道具 |

问候与外观独立配置。睡眠 > 深夜 > 普通；启动按本地时间选择外观；之后双击和周期轮播均使用全部7张，不再按时间强制纠正用户选图。默认每5分钟换图并显示时间问候；启动和首次展示某时段以原创主文案开头，之后「主文案→辅助A→主文案→辅助B」轮播。单一调度器，不补播休眠错过的轮次。关闭气泡仅隐藏，不换图、不推进文案、不重置计时。睡眠问候延后至互动或睡醒，错过的时段不补发。关怀和问候用单一气泡排队。

最新行为与验证见 [时间问候与轮播修复报告](docs/rotation/验收报告.md)。时间问候设置中分别编辑主文案、辅助文案、间隔和免打扰；旧关怀语按时段保留。

## 素材与数据

- 原始照片不覆盖，副本在 `assets/chiikawa/originals/`（本机保留、不上传）；处理图在 `assets/chiikawa/processed/`。
- 统一 320×320 透明画布，脚底/接触面 y=280，透明角色按头部实际宽度与横向中心统一比例（约140px头宽，320px画布），电脑道具与角色保持原始相对比例；等比缩放，不生成缺失肢体或连续帧。
- 2/4/6/7已去背景，2/4保留电脑和键盘，7只提取中间角色。2图和7图的少量下缘补绘单独保存并明确标注。
- 使用连续局部网格生成透明PNG图集：耳朵、手臂、身体相对运动，五官核心区域固定。3图额外提供可见双脚交替抬动；不将被遮挡/卧姿素材的整图位移称作真实步态。
- 1/3/5继续使用原有透明角色，5只做6秒缓慢呼吸。设置 → 陪伴 → 动画效果，可选「仅整图动画」「整图＋身体动画」「减少动画」；默认整图＋身体。
- 身体图集与整图摇摆/缩放/点击弹动独立叠加，窗口仍为120×120，拖拽与点击区域不变。
- 配置：`%APPDATA%\UsagiPet\settings.json`。内部目录保留稳定名称；保存前备份 `.json.bak`，原子写入。未知字段、自定义问候和记录保留，损坏文件不覆盖。
- 旧代码/素材本机备份在 `backups/`，运行与打包均不读取旧角色资源。
- 最新交付见 [身体动画报告](docs/body-animation/交付报告.md) 和 [七图动画预览](docs/body-animation/index.html)；首次换肤记录保留在 [历史验收报告](docs/chiikawa/验收报告.md)。

## 开发、测试与构建

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python tools/prepare_assets.py
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python tools/capture_ui.py
.\build.ps1
```

PyInstaller 沿用原有单文件、无控制台模式，将处理图和图标一起打包，产物 `dist/ChiikawaPet.exe`。原始图与备份不打包。

仅源码开发环境支持时间预览（不修改电脑系统时间，不写入个人数据）：

```powershell
$env:CHIIKAWA_DEV='1'
.\.venv\Scripts\python desktop_pet.py --preview-time 2026-10-19T23:00
```

也可通过开发环境设置页的「开发预览」调整时间。打包版忽略开发预览开关。测试覆盖时间边界、轮播隔离、原有提醒、数据保留及 Qt 原生交互；硬件休眠和多显示器限制见验收报告。

基于 [ruochengwu/usagi-desktop-pet](https://github.com/ruochengwu/usagi-desktop-pet) 修改；用户 GitHub 仓库地址与历史记录继续保留。


## 身体动画源文件

- 四张高清透明图：`assets/chiikawa/body_sources/2-clean-alpha.png`、`4-clean-alpha.png`、`6-clean-alpha.png`、`7-clean-alpha.png`。
- 完整网格源：`assets/chiikawa/animation_sources/<角色>/source.png`、`rig-author.json`、`rig.json`、`masks/`。控制区域连续变形，不需要把关节剪开再拼接。
- 最小补绘区：`2-bottom-contour-repair.png`、`2-repair-region.png`、`7-bottom-contour-repair.png`；不冒充原图内容，没有补出隐藏脚或站立身体。
- 运行图集：`assets/chiikawa/processed/animations/`，32帧/动作，20份PNG图集；运行只用PyQt5，不需要NumPy、Pillow或网络。
- 开发烘焙：编辑各角色 `rig-author.json` 的控制点/范围/幅度后运行 `python tools/author_body_animation.py`；`python tools/prepare_assets.py` 会走同一新流程，不会用旧不透明场景覆盖新素材。
- `python tools/capture_body_runtime.py` 可重现原生三模式对照。动画预览页支持棋盘格、深色、浅色及「固定整图，只验证身体」模式。
