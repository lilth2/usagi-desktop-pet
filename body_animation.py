"""Local PNG atlas playback, layered underneath existing whole-pet motion."""
import json
import logging
from collections import OrderedDict
from PyQt5.QtGui import QPixmap
from theme import ASSETS


class BodyAnimations:
    def __init__(self,folder=None):
        self.folder=folder or ASSETS/'animations'
        self.cache=OrderedDict()
        self.manifest={}
        try:
            self.manifest=json.loads((self.folder/'manifest.json').read_text(encoding='utf-8'))
        except (OSError,ValueError) as e:
            logging.warning('Body animation unavailable; static character remains usable: %s',e)

    def metadata(self,kind,clip):
        return self.manifest.get(kind,{}).get(clip)

    def frame(self,kind,clip,elapsed):
        meta=self.metadata(kind,clip)
        if not meta:return None
        file=meta['file']
        if file not in self.cache:
            atlas=QPixmap(str(self.folder/file))
            if atlas.isNull():return None
            self.cache[file]=atlas
            while len(self.cache)>2:self.cache.popitem(last=False)
        self.cache.move_to_end(file)
        count=meta['count'];duration=meta['duration']
        progress=max(0,elapsed)/duration
        index=int(progress*count)%count if meta['loop'] else min(count-1,int(progress*count))
        size=meta['size'];columns=meta['columns']
        return self.cache[file].copy((index%columns)*size,(index//columns)*size,size,size)
