"""Pure local-time scheduling. Greetings and appearances are independent."""
import copy
import json
import os
import random
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULTS = {
 'walking_enabled': True, 'care_enabled': True,
 'greetings_enabled': True, 'appearance_enabled': True, 'nap_enabled': True,
 'nap_start':'12:30','nap_end':'14:00', 'sleep_start':'23:00','sleep_end':'06:00',
 'evening_start':'18:00',
 'late_variant':'rotate',
 'animation_mode':'body',
 'greetings':[
  {'id':'morning','start':'06:00','end':'11:00','label':'早上好','messages':['早上好。新的一天，慢慢来，我陪着你。']},
  {'id':'noon','start':'11:00','end':'14:00','label':'中午好','messages':['中午好。忙完这一会儿，也记得好好吃饭。']},
  {'id':'afternoon','start':'14:00','end':'18:00','label':'下午好','messages':['下午好。愿接下来的时间轻松一点。']},
  {'id':'evening','start':'18:00','end':'06:00','label':'晚上好','messages':['晚上好。今天辛苦了，我在这里陪你。']},
 ],
 'greeted':{},
}


def minute(value):
    parts = value.split(':')
    if len(parts)!=2 or any(not p.isdigit() or len(p)!=2 for p in parts):
        raise ValueError('时间必须使用 HH:mm 格式。')
    h,m=map(int,parts)
    if not 0<=h<24 or not 0<=m<60: raise ValueError('时间超出有效范围。')
    return h*60+m


def contains(current,start,end):
    start,end=minute(start),minute(end)
    return start<=current<end if start<end else (current>=start or current<end)


def validate(data):
    if data['animation_mode'] not in ('whole','body','reduced'):
        raise ValueError('动画模式必须为仅整图、整图＋身体或减少动画。')
    for key in ('walking_enabled','care_enabled','greetings_enabled','appearance_enabled','nap_enabled'):
        if not isinstance(data[key],bool): raise ValueError('开关配置必须为布尔值：'+key)
    if not isinstance(data['greeted'],dict): raise ValueError('问候记录格式不正确。')
    if data['late_variant'] not in ('rotate','late','late_scene'): raise ValueError('深夜素材配置不正确。')
    greetings=data['greetings']
    if not greetings: raise ValueError('至少需要一个问候时段。')
    ids=set()
    for g in greetings:
        if not g['id'] or g['id'] in ids: raise ValueError('问候时段 ID 不能重复。')
        ids.add(g['id'])
        if minute(g['start'])==minute(g['end']): raise ValueError('问候开始和结束不能相同。')
        if not g['label'].strip() or not g['messages']: raise ValueError('问候名称和文案不能为空。')
        if any(g['label'] not in m or not m.strip() for m in g['messages']):
            raise ValueError('每条问候文案必须包含该时段的问候名称。')
    for m in range(1440):
        if sum(contains(m,g['start'],g['end']) for g in greetings)!=1:
            raise ValueError('问候时段必须覆盖全天，且不能重叠。')
    for prefix in ('nap','sleep'):
        if minute(data[prefix+'_start'])==minute(data[prefix+'_end']):
            raise ValueError('睡眠开始和结束不能相同。')
    if not 18*60<=minute(data['evening_start'])<24*60:
        raise ValueError('晚间开始时间应在 18:00–23:59。')
    for m in range(6*60,18*60):
        if contains(m,data['sleep_start'],data['sleep_end']):
            raise ValueError('夜间睡眠需限制在 18:00–次日06:00 以内。')
    minute(data['nap_start']); minute(data['nap_end'])
    return data


class SettingsStore:
    def __init__(self,path=None):
        # Keep stable internal identity so legacy launchers/paths remain valid.
        self.path=Path(path) if path else Path(os.environ.get('APPDATA',str(Path.home()))) / 'UsagiPet' / 'settings.json'
        self.data=copy.deepcopy(DEFAULTS)
        self.warning=''
        self.writable=True
        if self.path.exists():
            try:
                raw=json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(raw,dict): raise ValueError('配置根节点必须为对象')
                self.data.update(raw)
                validate(self.data)
            except (ValueError,KeyError,TypeError,OSError) as e:
                self.warning=f'配置读取失败，原文件已保留：{e}'
                self.data=copy.deepcopy(DEFAULTS)
                self.writable=False

    def save(self):
        if not self.writable:
            raise OSError(self.warning+'；请先修复配置文件，避免覆盖原有数据。')
        validate(self.data)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists():
            backup=self.path.with_suffix('.json.bak')
            shutil.copy2(self.path,backup)
        temp=self.path.with_suffix('.json.tmp')
        temp.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8')
        temp.replace(self.path)


class Schedule:
    def __init__(self,store,preview=None):
        self.store=store
        self.preview=preview
        self.preview_greeted=set()

    def now(self):
        return self.preview if self.preview is not None else datetime.now().astimezone()

    def appearance(self,now=None):
        d=self.store.data; now=now or self.now(); m=now.hour*60+now.minute
        if not d['appearance_enabled']: return 'normal'
        if contains(m,d['sleep_start'],d['sleep_end']): return 'sleep'
        if d['nap_enabled'] and contains(m,d['nap_start'],d['nap_end']): return 'sleep'
        if m<6*60 or m>=minute(d['evening_start']): return 'late'
        return 'normal'

    def greeting(self,now=None):
        d=self.store.data; now=now or self.now()
        if not d['greetings_enabled']: return None
        m=now.hour*60+now.minute
        g=next(g for g in d['greetings'] if contains(m,g['start'],g['end']))
        # Calendar date + stable period ID, including across midnight/DST.
        key=f"{now.date().isoformat()}:{g['id']}"
        if key in d['greeted'] or (self.preview is not None and key in self.preview_greeted): return None
        return key, random.choice(g['messages'])

    def delivered(self,key):
        if self.preview is not None:
            self.preview_greeted.add(key)
            return
        self.store.data['greeted'][key]=True
        self.store.save()
