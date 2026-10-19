"""Generate inspection artifacts from the exact production PNG atlases."""
import base64
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from author_body_animation import backgrounds,field

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/chiikawa/processed'
DOC=ROOT/'docs/body-animation'
MANIFEST=json.loads((OUT/'animations/manifest.json').read_text(encoding='utf-8'))
DETAILS={
 'normal':(3,'普通 · 可见双脚','耳朵/手臂、呼吸、交替抬脚'),
 'office':(2,'普通 · 台式电脑','耳朵、侧身呼吸；仅可见手部小动作'),
 'desktop':(4,'普通 · 笔记本','耳朵、侧身呼吸；可见手部小动作'),
 'happy':(6,'普通 · 开心姿势','手臂抬起、耳朵、局部呼吸'),
 'late':(1,'深夜 · 躺着看手机','耳朵、露出身体的轻微呼吸'),
 'late_scene':(7,'深夜 · 背向角色','耳朵、后背呼吸；不伪造脚步'),
 'sleep':(5,'午睡/夜眠','仅缓慢呼吸，无挥手/步行'),
}
DOC.mkdir(parents=True,exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
sheet=Image.new('RGB',(1280,760),'#fff9f6');draw=ImageDraw.Draw(sheet)
cards=[];qa={}
for index,(kind,(number,label,motion)) in enumerate(DETAILS.items()):
    im=Image.open(OUT/(kind+'.png')).convert('RGBA')
    x=(index%4)*320;y=(index//4)*380
    sheet.paste(backgrounds(im).crop((0,0,320,320)),(x,y+30))
    draw.text((x+10,y+4),f'{number}.png · {kind}',font=font,fill='#59464d')
    draw.text((x+10,y+351),label,font=font,fill='#59464d')
    alpha=np.asarray(im)[:,:,3]
    rig=json.loads((ROOT/'assets/chiikawa/animation_sources'/kind/'rig.json').read_text(encoding='utf-8'))
    qa[kind]={'source_photo':number,'mode':im.mode,'size':list(im.size),'bbox':im.getbbox(),
              'transparent_pixels':int((alpha==0).sum()),'opaque_pixels':int((alpha==255).sum()),
              'clips':list(MANIFEST[kind]),'supplemented_body':rig.get('supplemented_body',False)}
    clip='idle' if kind in ('late','sleep') else 'interact'
    if kind=='happy':clip='happy'
    if kind=='normal':clip='walk'
    meta=MANIFEST[kind][clip];atlas=Image.open(OUT/'animations'/meta['file'])
    frames=[]
    for n in range(meta['count']):
        x0=(n%meta['columns'])*320;y0=(n//meta['columns'])*320
        frames.append(backgrounds(atlas.crop((x0,y0,x0+320,y0+320))))
    frames[0].save(DOC/f'{kind}-{clip}.gif',save_all=True,append_images=frames[1:],duration=round(meta['duration']*1000/meta['count']),loop=0,disposal=2)
    cards.append({'kind':kind,'number':number,'label':label,'motion':motion,'clips':MANIFEST[kind]})
sheet.save(DOC/'seven-transparent-assets.png')
sheet.save(ROOT/'docs/chiikawa/asset-preview.png')
(DOC/'asset-qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')

template='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>吉伊卡哇身体动画验收</title>
<style>body{font:14px/1.7 "Microsoft YaHei",sans-serif;background:#fffaf7;color:#59464d;max-width:1150px;margin:24px auto;padding:0 18px}h1,h2{color:#795165}button,select{padding:7px;background:#fff4f7;border:1px solid #cca2b1;border-radius:7px;color:#59464d}header{position:sticky;top:0;background:#fffaf7;z-index:2;padding:10px;border-bottom:1px solid #e6ccd7}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}.card,section{border:1px solid #e6ccd7;border-radius:14px;background:white;padding:16px;margin:16px 0}.stage{background:repeating-conic-gradient(#ded7db 0% 25%,#fff 0% 50%) 50%/20px 20px;width:100%;display:flex;justify-content:center;border-radius:10px}.stage.dark{background:#292a37}.stage.light{background:#fff9f2}canvas{width:280px;height:280px}a{color:#9b5c79}img{max-width:100%}code{word-break:break-all}</style>
<h1>吉伊卡哇 · 透明素材与身体动画</h1><p>由实际接入项目的PNG图集播放。默认固定整图，单独观察身体部位；可切换为整图与身体叠加。预览循环播放，应用内互动只播放一次。</p>
<header>背景：<button onclick="background('checker')">棋盘格</button> <button onclick="background('dark')">深色</button> <button onclick="background('light')">浅色</button>　预览：<select id="mode"><option value="proof">身体局部验证（固定整图）</option><option value="body">整图＋身体动画</option><option value="whole">仅整图动画</option><option value="reduced">减少动画</option></select></header>
<div class="grid" id="cards"></div><section><h2>七图统一比例和定位</h2><img src="seven-transparent-assets.png"><p>统一320×320透明画布，底部基线y=280。2/4保留电脑、键盘；7仅中间角色。原始照片不覆盖。模型抠图会重绘部分边缘，未声称逐像素复制。</p></section>
<section><h2>补绘与限制</h2><p>2图修复桌面移除后露出的下缘；7图修复草地遮住的最下缘。保守补绘范围和源图分开保存。没有补出隐藏的脚，不将电脑/卧姿素材冒充走路。只有3图加入可见双脚交替抬动；完整步态仍受原图姿势限制。</p><a href="交付报告.md">完整交付与实际验证</a> · <a href="prompts.md">抠图及修复提示词</a> · <a href="asset-qa.json">透明度清单</a></section>
<script>const data=__DATA__;const players=[];const root=document.getElementById('cards');
for(const item of data){const box=document.createElement('section');box.className='card';box.innerHTML=`<b>${item.number}.png · ${item.label}</b><div class="stage"><canvas width="320" height="320"></canvas></div><p>${item.motion}</p><select></select><p><a href="../../assets/chiikawa/processed/${item.kind}.png">透明PNG</a> · <a href="../../assets/chiikawa/animation_sources/${item.kind}/rig.json">控制点源文件</a></p>`;root.append(box);const select=box.querySelector('select');for(const key of Object.keys(item.clips))select.add(new Option(({idle:'待机/呼吸',interact:'点击互动',happy:'开心',walk:'可见双脚交替抬动'})[key],key));select.value=item.clips.interact?'interact':'idle';const staticImage=new Image();staticImage.src=`../../assets/chiikawa/processed/${item.kind}.png`;players.push({item,select,staticImage,atlases:{},ctx:box.querySelector('canvas').getContext('2d')});}
function background(mode){document.querySelectorAll('.stage').forEach(s=>s.className='stage '+(mode==='checker'?'':mode));}
function tick(ms){const mode=document.getElementById('mode').value;for(const p of players){const meta=p.item.clips[p.select.value];let atlas=p.atlases[meta.file];if(!atlas){atlas=new Image();atlas.src='../../assets/chiikawa/processed/animations/'+meta.file;p.atlases[meta.file]=atlas;}const c=p.ctx;c.clearRect(0,0,320,320);c.save();if((mode==='body'||mode==='whole')&&p.item.kind!=='sleep'){c.translate(160,280);c.rotate(Math.sin(ms/1000*Math.PI/2)*.012);const s=1+Math.sin(ms/1000*Math.PI)*.025;c.scale(s,s);c.translate(-160,-280);}if(mode==='whole'||mode==='reduced'){if(p.staticImage.complete)c.drawImage(p.staticImage,0,0);}else if(atlas.complete&&atlas.naturalWidth){const index=Math.floor((ms/1000%meta.duration)/meta.duration*meta.count);c.drawImage(atlas,index%meta.columns*320,Math.floor(index/meta.columns)*320,320,320,0,0,320,320);}c.restore();}requestAnimationFrame(tick);}requestAnimationFrame(tick);</script></html>'''
(DOC/'index.html').write_text(template.replace('__DATA__',json.dumps(cards,ensure_ascii=False)),encoding='utf-8')
print('Transparent asset report and exact-atlas animation previews generated.')
