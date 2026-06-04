# 桌面桌宠 - 乌萨奇 (Usagi)

使用 PyQt5 + QPixmap 贴图渲染的透明无边框桌面宠物应用。

## 准备工作

将乌萨奇的 PNG 图片（建议透明背景）放到项目目录下，命名为 **`usagi.png`**。

推荐图片尺寸约 130×130 像素，支持透明通道（RGBA）。

## 运行

```bash
pip install PyQt5
python desktop_pet.py
```

如果未放置 `usagi.png`，程序会显示橙色占位图提示。

## 交互

| 操作 | 效果 |
|------|------|
| 左键拖拽 | 抓起宠物，缩小至 70%，跟随鼠标移动 |
| 右键点击 | 弹出菜单，选择退出程序 |
| 什么也不做 | 宠物自动在 Idle（浮动呼吸）和 Walk（走动摇摆）间切换 |

## 打包

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "usagi.png;." --name "DesktopPet" desktop_pet.py
```
