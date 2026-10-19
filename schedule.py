"""Pure local-time scheduling. Greetings and appearances are independent."""
import copy
import json
import os
import shutil
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
from companion_config import CORE_MESSAGES, AUXILIARY_MESSAGES, CHARACTER_ASSETS, TEXT_ROTATION

DEFAULTS = {
 'walking_enabled': True, 'care_enabled': True,
 'greetings_enabled': True, 'appearance_enabled': True, 'nap_enabled': True,
 'nap_start':'12:30','nap_end':'14:00', 'sleep_start':'23:00','sleep_end':'06:00',
 'evening_start':'18:00',
 'late_variant':'rotate',
 'animation_mode':'body',
 'greetings':[
  {'id':'morning','start':'06:00','end':'11:00','label':'早上好','messages':['早上好。新的一天，慢慢来，我陪着你。','早上好。记得喝点水，今天也慢慢来。']},
  {'id':'noon','start':'11:00','end':'14:00','label':'中午好','messages':['中午好。忙完这一会儿，也记得好好吃饭。','中午好。让眼睛歇一会儿吧。']},
  {'id':'afternoon','start':'14:00','end':'18:00','label':'下午好','messages':['下午好。愿接下来的时间轻松一点。','下午好。伸伸肩膀，我陪你继续。']},
  {'id':'evening','start':'18:00','end':'06:00','label':'晚上好','messages':['晚上好。今天辛苦了，我在这里陪你。','晚上好。放松一下，照顾好自己。']},
 ],
 'greeting_interval':5, 'dnd_enabled':False, 'dnd_start':'23:00', 'dnd_end':'06:00',
 'greeted':{},
}


def migrate_greetings(data):
    """Idempotent copy-only migration; no custom text/history is removed."""
    if not isinstance(data['greetings'],list): raise ValueError('问候配置格式不正确。')
    for greeting in data['greetings']:
        if not isinstance(greeting,dict) or not isinstance(greeting.get('messages'),list):
            raise ValueError('问候文案格式不正确。')
        fallback=greeting['messages'][0] if greeting.get('messages') else greeting.get('label','问候')
        greeting.setdefault('primary', CORE_MESSAGES.get(greeting['id'], fallback))
        if data.get('greeting_copy_version', 0) < 2:
            for text in AUXILIARY_MESSAGES.get(greeting['id'], []):
                if text not in greeting['messages']:
                    greeting['messages'].append(text)
    data['greeting_copy_version'] = 2


migrate_greetings(DEFAULTS)



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
    if not isinstance(data['greeting_interval'],int) or not 1<=data['greeting_interval']<=1440:
        raise ValueError('问候间隔应为1–1440分钟。')
    if not isinstance(data['dnd_enabled'],bool): raise ValueError('免打扰开关格式错误。')
    minute(data['dnd_start']);minute(data['dnd_end'])
    if data['dnd_start']==data['dnd_end']: raise ValueError('免打扰开始和结束不能相同。')
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
        if not g['label'].strip() or not isinstance(g['messages'],list): raise ValueError('问候名称和辅助文案格式不正确。')
        if not isinstance(g['primary'], str) or not g['primary'].strip():
            raise ValueError('主文案不能为空。')
        if any(not isinstance(m,str) or not m.strip() for m in g['messages']):
            raise ValueError('辅助文案不能为空。')
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
        if path:
            self.path=Path(path)
        elif sys.platform=='darwin':
            legacy=Path.home()/'UsagiPet'/'settings.json'
            self.path=legacy if legacy.exists() else Path.home()/'Library'/'Application Support'/'ChiikawaPet'/'settings.json'
        else:
            self.path=Path(os.environ.get('APPDATA',str(Path.home()))) / 'UsagiPet' / 'settings.json'
        self.data=copy.deepcopy(DEFAULTS)
        self.warning=''
        self.writable=True
        if self.path.exists():
            try:
                raw=json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(raw,dict): raise ValueError('配置根节点必须为对象')
                self.data.update(raw)
                if 'greeting_copy_version' not in raw:
                    self.data.pop('greeting_copy_version',None)
                migrate_greetings(self.data)
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
        self.next_due=None
        self.last_delivery=None
        self.candidate=None
        self.period_key=None
        self.text_step=0
        self.auxiliary_index=0
        self.last_auxiliary=None
        self.interaction_steps={}

    def now(self):
        return self.preview if self.preview is not None else datetime.now().astimezone()

    def appearance(self,now=None):
        d=self.store.data; now=now or self.now(); m=now.hour*60+now.minute
        if not d['appearance_enabled']: return 'normal'
        if contains(m,d['sleep_start'],d['sleep_end']): return 'sleep'
        if d['nap_enabled'] and contains(m,d['nap_start'],d['nap_end']): return 'sleep'
        if m<6*60 or m>=minute(d['evening_start']): return 'late'
        return 'normal'

    def allowed_assets(self,now=None):
        appearance=self.appearance(now)
        rules={'sleep'} if appearance=='sleep' else {'ordinary','late'} if appearance=='late' else {'ordinary'}
        return tuple(asset['id'] for asset in CHARACTER_ASSETS if asset['rule'] in rules)

    def initial_asset(self):
        if self.appearance()=='late':
            variant=self.store.data['late_variant']
            if variant=='rotate':
                return 'late' if self.now().date().toordinal()%2 else 'late_scene'
            return variant
        return self.allowed_assets()[0]

    def poll(self,clock=None):
        """Consume at most ONE cycle. No backlog after resume or clock changes."""
        clock=time.monotonic() if clock is None else clock
        if self.next_due is not None and clock < self.next_due:
            return None
        startup=self.next_due is None
        self.next_due=clock+self.store.data['greeting_interval']*60
        return 'startup' if startup else 'periodic'

    def greeting(self,now=None,force=False):
        d=self.store.data; now=now or self.now()
        m=now.hour*60+now.minute
        g=next(g for g in d['greetings'] if contains(m,g['start'],g['end']))
        period_date=now.date()
        if minute(g['start'])>minute(g['end']) and m<minute(g['end']):
            period_date-=timedelta(days=1)
        key=f"{period_date.isoformat()}:{g['id']}"
        if key!=self.period_key:
            self.period_key=key;self.text_step=0;self.auxiliary_index=0
            self.last_auxiliary=None;self.candidate=None
        if not force and not d['greetings_enabled']: return None
        if not force and d['dnd_enabled'] and contains(m,d['dnd_start'],d['dnd_end']): return None
        auxiliary=list(dict.fromkeys(text for text in g['messages'] if text!=g['primary']))
        if TEXT_ROTATION[self.text_step % len(TEXT_ROTATION)]=='primary' or not auxiliary:
            text=g['primary']
        else:
            # Preserve order, skip the last auxiliary if a list was edited.
            index=self.auxiliary_index % len(auxiliary)
            if len(auxiliary)>1 and auxiliary[index]==self.last_auxiliary:
                index=(index+1)%len(auxiliary)
            text=auxiliary[index]
        self.candidate=(key,text)
        return self.candidate

    def interaction_greeting(self):
        key,_=self.greeting(force=True)
        g=next(g for g in self.store.data['greetings'] if g['id']==key.rsplit(':',1)[-1])
        step=self.interaction_steps.get(key,0)
        auxiliary=list(dict.fromkeys(text for text in g['messages'] if text!=g['primary']))
        text=g['primary'] if step%2==0 or not auxiliary else auxiliary[(step//2)%len(auxiliary)]
        self.interaction_steps={key:step+1}
        return text

    def delivered(self,key):
        if not self.candidate or key!=self.candidate[0]: return
        g=next(g for g in self.store.data['greetings'] if g['id']==key.rsplit(':',1)[-1])
        if self.candidate[1]!=g['primary']:
            auxiliary=list(dict.fromkeys(text for text in g['messages'] if text!=g['primary']))
            self.last_auxiliary=self.candidate[1]
            self.auxiliary_index=auxiliary.index(self.last_auxiliary)+1
        self.text_step+=1
        self.last_delivery=time.monotonic()
        self.candidate=None
