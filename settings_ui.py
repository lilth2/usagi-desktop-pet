"""Resizable local settings; unknown stored fields and custom text are preserved."""
import copy
from datetime import datetime
from PyQt5.QtCore import Qt, QTime, QTimer
from PyQt5.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QWidget,QTabWidget,
 QCheckBox,QTimeEdit,QTableWidget,QTableWidgetItem,QHeaderView,QDialogButtonBox,
 QLabel,QScrollArea,QMessageBox,QPushButton,QHBoxLayout,QComboBox,QLineEdit,QSpinBox)
from theme import DIALOG_STYLE
from schedule import validate


class SettingsDialog(QDialog):
    def __init__(self,pet):
        super().__init__(pet,Qt.Window)
        self.setAttribute(Qt.WA_QuitOnClose,False)
        self.pet=pet
        self.setWindowTitle('吉伊卡哇 · 设置')
        self.setStyleSheet(DIALOG_STYLE)
        self.resize(650,510)
        self.setMinimumSize(400,320)
        root=QVBoxLayout(self)
        tabs=QTabWidget(); root.addWidget(tabs)
        self.boxes={}; self.times={}
        general=QWidget(); f=QFormLayout(general)
        for key,label in [('care_enabled','自动关怀（持续使用30分钟）'),('walking_enabled','小步散步（左右各30像素）'),('greetings_enabled','自动时间问候'),('appearance_enabled','按时间切换外观'),('nap_enabled','启用午睡外观')]:
            box=QCheckBox(label); box.setChecked(pet._store.data[key]); self.boxes[key]=box; f.addRow(box)
        self.animation_mode=QComboBox()
        for label,value in [('仅整图动画','whole'),('整图＋身体动画','body'),('减少动画','reduced')]:
            self.animation_mode.addItem(label,value)
        self.animation_mode.setCurrentIndex(max(0,self.animation_mode.findData(pet._store.data['animation_mode'])))
        f.addRow('动画效果',self.animation_mode)
        note=QLabel('关怀提醒继续在睡眠外观下运行；问候延至互动或睡醒。\n聊天功能此前已移除；不添加网络服务或语音。')
        note.setWordWrap(True); f.addRow(note)
        tabs.addTab(general,'陪伴')
        appearance=QWidget(); f=QFormLayout(appearance)
        for key,label in [('nap_start','午睡开始'),('nap_end','午睡结束'),('sleep_start','夜间睡眠开始'),('sleep_end','夜间睡眠结束'),('evening_start','晚间清醒开始')]:
            t=QTimeEdit(QTime.fromString(pet._store.data[key],'HH:mm')); t.setDisplayFormat('HH:mm'); self.times[key]=t; f.addRow(label,t)
        note=QLabel('优先级：睡觉 > 晚间 > 普通。深夜素材仅在18:00–次日06:00允许出现；素材缺失时回退普通吉伊卡哇。')
        note.setWordWrap(True); f.addRow(note)
        tabs.addTab(appearance,'外观时间')
        self.variant=QComboBox()
        for label,value in [('按日期选择深夜初始图','rotate'),('1.png · 躺着看手机','late'),('7.png · 夜景背影','late_scene')]:
            self.variant.addItem(label,value)
        self.variant.setCurrentIndex(max(0,self.variant.findData(pet._store.data['late_variant'])))
        f.addRow('深夜初始偏好（轮播含全部合规图片）',self.variant)
        greetings=QWidget(); gl=QVBoxLayout(greetings)
        hint=QLabel('时段包含开始、不包含结束，需覆盖全天且不重叠。\n主文案与辅助文案交替轮播；多条辅助文案用「｜」分隔，原文保留。')
        hint.setWordWrap(True); gl.addWidget(hint)
        controls=QFormLayout();gl.addLayout(controls)
        self.interval=QSpinBox();self.interval.setRange(1,1440);self.interval.setSuffix(' 分钟');self.interval.setValue(pet._store.data['greeting_interval']);controls.addRow('周期问候间隔',self.interval)
        box=QCheckBox('启用问候免打扰');box.setChecked(pet._store.data['dnd_enabled']);self.boxes['dnd_enabled']=box;controls.addRow(box)
        for key,label in [('dnd_start','免打扰开始'),('dnd_end','免打扰结束')]:
            edit=QTimeEdit(QTime.fromString(pet._store.data[key],'HH:mm'));edit.setDisplayFormat('HH:mm');self.times[key]=edit;controls.addRow(label,edit)
        self.table=QTableWidget(len(pet._store.data['greetings']),5)
        self.table.setHorizontalHeaderLabels(['问候名称','开始','结束','辅助文案','主文案'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch)
        for row,g in enumerate(pet._store.data['greetings']):
            for col,val in enumerate([g['label'],g['start'],g['end'],'｜'.join(g['messages']),g['primary']]):
                self.table.setItem(row,col,QTableWidgetItem(val))
        self.table.setColumnWidth(4,240)
        self.table.setColumnWidth(0,75);self.table.setColumnWidth(1,65);self.table.setColumnWidth(2,65)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.horizontalHeader().sectionResized.connect(lambda *_:self.table.resizeRowsToContents())
        self.table.model().dataChanged.connect(lambda *_:self.table.resizeRowsToContents())
        self.table.resizeRowsToContents(); gl.addWidget(self.table)
        tabs.addTab(greetings,'时间问候')
        if pet._dev:
            preview=QWidget(); pf=QFormLayout(preview)
            self.preview_time=QLineEdit(pet._schedule.now().isoformat(timespec='minutes'))
            pf.addRow('开发预览时间（ISO）',self.preview_time)
            preview_button=QPushButton('预览时间（不修改系统）')
            preview_button.clicked.connect(self.preview);pf.addRow(preview_button)
            reset=QPushButton('恢复电脑本地时间'); reset.clicked.connect(self.reset_preview);pf.addRow(reset)
            tabs.addTab(preview,'开发预览')
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText('保存')
        buttons.button(QDialogButtonBox.Cancel).setText('取消')
        buttons.accepted.connect(self.save);buttons.rejected.connect(self.reject);root.addWidget(buttons)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'table'):
            QTimer.singleShot(0,self.table.resizeRowsToContents)

    def preview(self):
        try:self.pet._schedule.preview=datetime.fromisoformat(self.preview_time.text())
        except ValueError:
            QMessageBox.warning(self,'时间格式错误','请输入例如 2026-10-19T23:00。');return
        self.pet._refresh_schedule()

    def reset_preview(self):
        self.pet._schedule.preview=None;self.pet._refresh_schedule()

    def save(self):
        data=copy.deepcopy(self.pet._store.data)
        data['greeting_interval']=self.interval.value()
        data['late_variant']=self.variant.currentData()
        data['animation_mode']=self.animation_mode.currentData()
        for key,box in self.boxes.items():data[key]=box.isChecked()
        for key,t in self.times.items():data[key]=t.time().toString('HH:mm')
        for row,g in enumerate(data['greetings']):
            values=[self.table.item(row,col).text().strip() if self.table.item(row,col) else '' for col in range(5)]
            g.update(label=values[0],start=values[1],end=values[2],messages=[x.strip() for x in values[3].split('｜') if x.strip()],primary=values[4])
        old=self.pet._store.data
        try:
            validate(data);self.pet._store.data=data;self.pet._store.save()
        except (ValueError,KeyError,TypeError,OSError) as e:
            self.pet._store.data=old;QMessageBox.warning(self,'设置未保存',str(e));return
        appearance_keys=('appearance_enabled','nap_enabled','nap_start','nap_end','sleep_start','sleep_end','evening_start','late_variant')
        self.pet._apply_settings(reset_sprite=any(old[k]!=data[k] for k in appearance_keys));self.accept()
