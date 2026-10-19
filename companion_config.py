"""Single source of character eligibility and default companion copy."""

CORE_MESSAGES = {
    'morning': '早上好呀 新的一天，我陪着你。',
    'noon': '中午好～ 睡醒也要记得好好吃饭。',
    'afternoon': '下午好呀～ 除了上课健身也要注意安全。',
    'evening': "晚上好哦～今天辛苦咯，I'm here 随时都在。",
}

CARE_MESSAGES = (
    '忙了好一会儿，看看远处，让眼睛歇一歇吧。',
    '起来走两步，伸伸肩膀，我在这里等你。',
    '喝口水吧～照顾好自己也是今天很重要的事。',
    '辛苦啦，不必一直绷着。慢慢呼吸，给自己一点空隙。',
    '如果今天有点难，也没关系。你可以按自己的节奏来。',
    '手腕和脖子还舒服吗？换个姿势，放松一下吧。',
    '事情做不完也可以先休息，你的感受同样值得被照顾。',
    '送你一个小小的抱抱。愿你这一刻能轻松一点。',
    '专注了这么久，已经很努力啦。给自己几分钟休息吧。',
    '别忘了按时吃饭。忙碌的时候，也要对自己温柔一点。',
)

AUXILIARY_MESSAGES = {
    'morning': [CARE_MESSAGES[i] for i in (2, 4)],
    'noon': [CARE_MESSAGES[i] for i in (0, 9)],
    'afternoon': [CARE_MESSAGES[i] for i in (1, 5, 8)],
    'evening': [CARE_MESSAGES[i] for i in (3, 6, 7)] + ['轻轻碰到你啦，我在好好休息，也陪着你。'],
}

# The rule key is evaluated by Schedule; IDs also drive loading and round order.
CHARACTER_ASSETS = (
    {'id': 'normal', 'rule': 'ordinary'},
    {'id': 'office', 'rule': 'ordinary'},
    {'id': 'desktop', 'rule': 'ordinary'},
    {'id': 'happy', 'rule': 'ordinary'},
    {'id': 'late', 'rule': 'late'},
    {'id': 'late_scene', 'rule': 'late'},
    {'id': 'sleep', 'rule': 'sleep'},
)

TEXT_ROTATION = ('primary', 'auxiliary')


class ImageRotation:
    """A complete round, with no repeat across the round boundary."""
    def __init__(self):
        self.allowed = ()
        self.remaining = []

    def next(self, allowed, current):
        allowed = tuple(allowed)
        if not allowed:
            raise ValueError('没有可用角色素材')
        if allowed != self.allowed or not self.remaining:
            self.allowed = allowed
            self.remaining = list(allowed)
            if len(allowed)>1 and current in allowed:
                start=allowed.index(current)+1
                self.remaining=list(allowed[start:]+allowed[:start])
        return self.remaining.pop(0)
