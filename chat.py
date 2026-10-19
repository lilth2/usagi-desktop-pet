"""Offline conversation: no account, network requests or saved chat history."""
import random

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QLineEdit, QPushButton


def reply_to(message):
    text = message.strip().lower()
    rules = [
        (("再见", "拜拜", "晚安"), ["呀哈～好好休息，我们下次见！", "晚安！把今天的疲惫放下吧。"]),
        (("难过", "伤心", "焦虑", "烦", "孤独", "压力"), ["乌拉……我在这里陪你。愿意说说发生了什么吗？", "今天辛苦了。可以先停一会儿，不用急着把所有事做好。"]),
        (("累", "困", "休息", "加班"), ["呀哈！伸个懒腰，喝口水，让眼睛休息一下吧。", "辛苦啦，先给自己五分钟休息时间吧！"]),
        (("喜欢", "可爱", "爱你", "抱抱"), ["呀哈～收到你的喜欢啦！送你一个小小的抱抱。", "乌拉呀哈！开心得想蹦两下！"]),
        (("饿", "吃", "饭"), ["乌拉！该补充能量啦，去吃点喜欢的东西吧。"]),
        (("工作", "学习", "作业", "考试"), ["呀哈！先挑一件小事做，完成一点也是进步。", "我陪你加油！专心一小会儿，然后记得休息。"]),
        (("你好", "早安", "早上好", "hello", "hi"), ["呀哈！今天也来陪你啦，想聊点什么？", "乌拉～见到你真开心！今天过得怎么样？"]),
        (("帮助", "会什么", "功能"), ["可以和我聊心情、学习、吃饭或休息。我现在用本地预设台词回复，还不会像 AI 那样理解所有问题哦。"]),
    ]
    for keywords, replies in rules:
        if any(word in text for word in keywords):
            return random.choice(replies)
    return random.choice(["呀哈～我在听，可以再多说一点吗？", "乌拉！虽然我只会一些预设台词，但很乐意陪着你。", "今天有没有一件让你开心的小事？"])


class ChatWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("和乌萨奇聊聊天")
        self.resize(360, 420)
        layout = QVBoxLayout(self)
        self.history = QTextBrowser()
        layout.addWidget(self.history)
        self.history.append("乌萨奇：呀哈！来聊聊天吧～（本地陪聊，关闭窗口后清空记录）")
        shortcuts = QHBoxLayout()
        for text in ("你好", "今天好累", "抱抱"):
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, value=text: self.send(value))
            shortcuts.addWidget(button)
        layout.addLayout(shortcuts)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("说点什么，按回车发送…")
        self.input.setMaxLength(500)
        self.input.returnPressed.connect(lambda: self.send())
        row.addWidget(self.input)
        send = QPushButton("发送")
        send.clicked.connect(lambda: self.send())
        row.addWidget(send)
        layout.addLayout(row)

    def send(self, message=None):
        text = self.input.text().strip() if message is None else message.strip()
        if not text:
            return
        # Plain text insertion prevents user input from being interpreted as HTML.
        from PyQt5.QtGui import QTextCursor
        cursor = self.history.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText("\n\n你：" + text + "\n乌萨奇：" + reply_to(text))
        self.history.setTextCursor(cursor)
        self.history.ensureCursorVisible()
        self.input.clear()
        self.input.setFocus()

    def closeEvent(self, event):
        self.history.clear()
        self.history.setPlainText("乌萨奇：呀哈！来聊聊天吧～（本地陪聊，关闭窗口后清空记录）")
        self.input.clear()
        super().closeEvent(event)
