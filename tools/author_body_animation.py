"""Bake continuous local mesh warps into true-alpha PNG atlases.

Authored control regions/pivots are saved separately from extracted artwork.
The runtime needs only PyQt5, not NumPy/Pillow or a network connection.
"""
import argparse
import json
import math
import copy
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/chiikawa/body_sources'
AUTHOR=ROOT/'assets/chiikawa/animation_sources'
OUT=ROOT/'assets/chiikawa/processed'
DOC=ROOT/'docs/body-animation'
SIZE=320
COUNT=32
COLS=8
REGISTRATION_SCALE=.78  # 180px source head -> about 140px, with props intact.
HEAD_X={'normal':160,'office':207,'desktop':162,'happy':160,'late':184,'late_scene':160,'sleep':178}


def clean_alpha(image):
    image=image.convert('RGBA')
    alpha=image.getchannel('A')
    component=alpha.point(lambda v:255 if v>8 else 0)
    # Start from an actual opaque body pixel, retain its connected silhouette.
    points=np.argwhere(np.asarray(component)>0)
    center=points[np.argmin(np.sum((points-np.array([image.height/2,image.width/2]))**2,axis=1))]
    ImageDraw.floodfill(component,(int(center[1]),int(center[0])),128)
    keep=component.point(lambda v:255 if v==128 else 0)
    cleaned=ImageChops.multiply(alpha,keep)
    # The extraction tool can leave near-opaque fur at alpha 250–254. Restore
    # solid interiors while retaining the genuinely soft boundary pixels.
    image.putalpha(cleaned.point(lambda v:255 if v>=240 else v))
    return image.crop(image.getbbox())


def normalize(image,head_fraction=0.94):
    image=clean_alpha(image)
    scale=min(180/(image.width*head_fraction),280/image.width,246/image.height)
    image=image.resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.LANCZOS)
    result=Image.new('RGBA',(SIZE,SIZE))
    result.alpha_composite(image,((SIZE-image.width)//2,280-image.height))
    return result


def gaussian(x,y,cx,cy,sx,sy):
    return np.exp(-.5*(((x-cx)/sx)**2+((y-cy)/sy)**2))


def field(rig,phase,clip):
    y,x=np.mgrid[:SIZE,:SIZE].astype(np.float32)
    dx=np.zeros_like(x);dy=np.zeros_like(y)
    wave=math.sin(phase)
    if clip in ('interact','happy'):
        # One closed gesture; zero displacement at both ends.
        wave=(1-math.cos(phase))/2
    face=rig.get('face',[160,140,55,35])
    protected=gaussian(x,y,*face)**.3
    fx,fy,fw,fh=face
    protected=np.maximum(protected,(((x-fx)/fw)**4+((y-fy)/fh)**4<1).astype(np.float32))
    for region in rig['regions']:
        name=region['name'];cx,cy=region['center'];sx,sy=region['radius']
        weight=gaussian(x,y,cx,cy,sx,sy)
        weight*=1-protected
        amplitude=region.get('idle',.3)
        if clip=='interact':amplitude=region.get('interact',amplitude)
        if clip=='happy':amplitude=region.get('happy',amplitude)
        if clip=='walk':amplitude=region.get('walk',amplitude)
        local=wave
        if name.endswith('right') and clip=='walk':local=-wave
        if name.startswith('ear'):
            dx+=weight*amplitude*local
            dy-=weight*amplitude*.45*local
        elif name.startswith('arm'):
            # Rigid rotation around the real shoulder, smoothly blended into
            # the continuous mesh. Adjacent pixels share one displacement field.
            px,py=region['pivot'];angle=amplitude*.035*local
            if name.endswith('left'):angle=-angle
            dx+=weight*((x-px)*(math.cos(angle)-1)-(y-py)*math.sin(angle))
            dy+=weight*((x-px)*math.sin(angle)+(y-py)*(math.cos(angle)-1))
        elif name.startswith('foot'):
            dy-=weight*amplitude*(1+local)/2 if clip=='walk' else weight*amplitude*local
            dx+=weight*amplitude*.4*local
        else:
            dx+=weight*(x-cx)/max(1,sx)*amplitude*.55*local
            dy-=weight*amplitude*local
    # Keep the baseline and transparent safety boundary stationary.
    gate=np.clip(((296 if clip=='walk' else 280)-y)/12,0,1)
    for rect in rig.get('fixed_props',[]):
        x0,y0,x1,y1=rect
        fixed=np.clip(np.minimum.reduce([x-x0,y-y0,x1-x,y1-y])/5,0,1)
        gate*=1-fixed
    return dx*gate,dy*gate


def warp(image,dx,dy):
    a=np.asarray(image,dtype=np.float32)/255
    a[:,:,:3]*=a[:,:,3:4]
    y,x=np.mgrid[:SIZE,:SIZE].astype(np.float32)
    xx=np.clip(x-dx,0,SIZE-1.001);yy=np.clip(y-dy,0,SIZE-1.001)
    x0=xx.astype(np.int32);y0=yy.astype(np.int32)
    wx=(xx-x0)[:,:,None];wy=(yy-y0)[:,:,None]
    result=a[y0,x0]*(1-wx)*(1-wy)+a[y0,x0+1]*wx*(1-wy)+a[y0+1,x0]*(1-wx)*wy+a[y0+1,x0+1]*wx*wy
    alpha=result[:,:,3:4]
    result[:,:,:3]=np.divide(result[:,:,:3],alpha,out=np.zeros_like(result[:,:,:3]),where=alpha>1/255)
    result=np.clip(result*255,0,255).astype('uint8')
    stationary=(np.abs(dx)<1e-7)&(np.abs(dy)<1e-7)
    result[stationary]=np.asarray(image)[stationary]
    return Image.fromarray(result)


def backgrounds(image):
    panel=Image.new('RGB',(SIZE*3,SIZE),'#fff9f2')
    checker=Image.new('RGBA',(SIZE,SIZE),'white');d=ImageDraw.Draw(checker)
    for y in range(0,SIZE,16):
        for x in range(0,SIZE,16):
            if (x//16+y//16)%2:d.rectangle((x,y,x+15,y+15),fill='#dcd4d9')
    for index,bg in enumerate([checker,Image.new('RGBA',(SIZE,SIZE),'#292a37'),Image.new('RGBA',(SIZE,SIZE),'#fff9f2')]):
        bg.alpha_composite(image);panel.paste(bg.convert('RGB'),(index*SIZE,0))
    return panel


def bake(kind,image,rig,clips=('idle','interact','happy')):
    folder=AUTHOR/kind;folder.mkdir(parents=True,exist_ok=True)
    author_file=folder/'rig-author.json'
    if author_file.exists():
        rig=json.loads(author_file.read_text(encoding='utf-8'))
    elif (folder/'rig.json').exists():
        rig=json.loads((folder/'rig.json').read_text(encoding='utf-8'))
    author_file.write_text(json.dumps(rig,ensure_ascii=False,indent=2),encoding='utf-8')
    image.save(folder/'input-before-registration.png')
    rig=copy.deepcopy(rig)
    scale=REGISTRATION_SCALE;head=HEAD_X[kind]
    def point(p):return [160+(p[0]-head)*scale,280+(p[1]-280)*scale]
    image=image.convert('RGBa').transform((SIZE,SIZE),Image.Transform.AFFINE,
       (1/scale,0,head-160/scale,0,1/scale,280-280/scale),Image.Resampling.BICUBIC).convert('RGBA')
    alpha=image.getchannel('A');ImageDraw.Draw(alpha).rectangle((0,280,SIZE,SIZE),fill=0);image.putalpha(alpha)
    fx,fy,fw,fh=rig['face'];rig['face']=point([fx,fy])+[fw*scale,fh*scale]
    for item in rig['regions']:
        item['center']=point(item['center']);item['radius']=[v*scale for v in item['radius']]
        if 'pivot' in item:item['pivot']=point(item['pivot'])
        for key in ('idle','interact','happy','walk'):
            if key in item:item[key]*=scale
    rig['fixed_props']=[point(rect[:2])+point(rect[2:]) for rect in rig.get('fixed_props',[])]
    rig['registration']={'scale':scale,'input_head_x':head,'output_head_x':160,'baseline':280,'target_head_width':140}
    (folder/'masks').mkdir(exist_ok=True)
    (OUT/'animations').mkdir(exist_ok=True);DOC.mkdir(parents=True,exist_ok=True)
    image.save(OUT/(kind+'.png'));image.save(folder/'source.png')
    (folder/'rig.json').write_text(json.dumps(rig,ensure_ascii=False,indent=2),encoding='utf-8')
    y,x=np.mgrid[:SIZE,:SIZE].astype(np.float32)
    for region in rig['regions']:
        mask=(gaussian(x,y,*region['center'],*region['radius'])*255).astype('uint8')
        Image.fromarray(mask).save(folder/'masks'/(region['name']+'.png'))
    metadata={}
    for clip in clips:
        frames=[]
        # Sample N+1 points including identical neutral endpoints for gestures.
        for i in range(COUNT):
            phase=2*math.pi*i/(COUNT-1 if clip in ('interact','happy') else COUNT)
            dx,dy=field(rig,phase,clip)
            frames.append(warp(image,dx,dy))
        atlas=Image.new('RGBA',(SIZE*COLS,SIZE*math.ceil(COUNT/COLS)))
        for i,frame in enumerate(frames):atlas.paste(frame,((i%COLS)*SIZE,(i//COLS)*SIZE))
        file=f'{kind}-{clip}.png';atlas.save(OUT/'animations'/file)
        metadata[clip]={'file':file,'count':COUNT,'columns':COLS,'size':SIZE,'duration':6.0 if kind=='sleep' else 4.0 if clip=='idle' else 1.6 if clip in ('happy','interact') else 1.6,'loop':clip not in ('happy','interact')}
        if clip=='happy' or kind=='sleep' and clip=='idle':
            previews=[backgrounds(frame) for frame in frames]
            previews[0].save(DOC/f'{kind}-{clip}.gif',save_all=True,append_images=previews[1:],duration=80,loop=0,disposal=2)
        if kind=='happy' and clip=='happy':
            # Body-only example: no whole-image transforms are applied here.
            frames[0].save(DOC/'sample6-neutral.png');frames[COUNT//2].save(DOC/'sample6-action.png')
            mask=(np.max(np.abs(np.asarray(frames[0],dtype=float)-np.asarray(frames[COUNT//2],dtype=float)),axis=2)>4).astype('uint8')*255
            Image.fromarray(mask).save(DOC/'sample6-local-motion-mask.png')
    backgrounds(image).save(DOC/f'{kind}-edges.png')
    return metadata


SAMPLE_RIG={
 'method':'continuous local mesh; premultiplied-alpha bilinear sampling',
 'source':'6.png / background-extracted source', 'supplemented_body':False,
 'face':[160,143,48,30],
 'regions':[
  {'name':'ear-left','center':[117,82],'radius':[10,14],'idle':.65,'interact':1.7,'happy':1.2},
  {'name':'ear-right','center':[203,84],'radius':[10,14],'idle':.65,'interact':1.7,'happy':1.2},
  {'name':'arm-left','center':[81,199],'pivot':[101,209],'radius':[18,14],'idle':.12,'interact':1.2,'happy':3.0},
  {'name':'arm-right','center':[242,199],'pivot':[220,209],'radius':[18,14],'idle':.12,'interact':3.0,'happy':3.0},
  {'name':'torso','center':[163,230],'radius':[45,27],'idle':1.0,'interact':1.4,'happy':2.4},
 ]}


def region(name,center,radius,idle=.5,interact=1,happy=1,pivot=None,walk=None):
    item={'name':name,'center':center,'radius':radius,'idle':idle,'interact':interact,'happy':happy}
    if pivot is not None:item['pivot']=pivot
    if walk is not None:item['walk']=walk
    return item


RIGS={
 'office':{'source':'2.png; original visible character, monitor and keyboard',
  'face':[192,169,46,26],'fixed_props':[[0,154,134,320],[137,246,220,284]],
  'regions':[
   region('ear-left',[167,99],[9,12],.6,1.5,1.5),region('ear-right',[247,110],[9,12],.6,1.5,1.5),
   region('torso',[275,224],[18,20],.8,1.0,1.2),
   region('arm-right',[234,242],[10,8],.05,.8,1.0,pivot=[247,237])]},
 'desktop':{'source':'4.png; original visible character and laptop',
  'face':[162,169,47,25],'fixed_props':[[59,204,201,290],[201,258,258,290]],
  'regions':[
   region('ear-left',[113,110],[10,12],.6,1.8,1.5),region('ear-right',[216,111],[10,12],.6,1.8,1.5),
   region('torso',[235,218],[10,22],.65,1.,1.3),
   region('arm-right',[215,241],[10,8],.05,1.1,1.5,pivot=[230,237])]},
 'late_scene':{'source':'7.png; rear-facing Chiikawa, no landscape or other characters',
  'supplemented_body':True,'supplement':'bottom contour previously covered by grass; conservative repair region saved separately',
  'face':[235,163,19,33],
  'regions':[
   region('ear-left',[112,101],[11,13],.5,1.2,1.2),region('ear-right',[202,101],[11,13],.5,1.2,1.2),
   region('torso',[155,220],[55,32],.9,1.1,1.2),
   region('tail',[131,259],[12,12],.2,.5,.5)]},
 'normal':{'source':'3.png; original middle Chiikawa; two visible feet only',
  'face':[160,161,48,29],
  'regions':[
   region('ear-left',[112,90],[9,12],.6,1.8,1.4),region('ear-right',[201,94],[9,12],.6,1.8,1.4),
   region('arm-left',[108,221],[12,13],.05,1.2,2,pivot=[116,214]),
   region('arm-right',[210,222],[12,13],.05,2.2,2,pivot=[202,214]),
   region('torso',[160,233],[38,22],.8,1.,1.5,walk=.6),
   region('foot-left',[131,266],[9,10],0,0,0,walk=2.5),region('foot-right',[169,273],[9,9],0,0,0,walk=2.5)]},
 'late':{'source':'1.png; lying awake with original phone/pillow/blanket',
  'face':[182,183,45,42],'fixed_props':[[135,191,179,235],[70,257,209,281]],
  'regions':[
   region('ear-left',[162,123],[9,12],.3,1.2,1),region('ear-right',[246,172],[9,12],.3,1.2,1),
   region('torso',[240,230],[24,22],.6,.8,1)]},
 'sleep':{'source':'5.png; confirmed sleeping pose only',
  'face':[158,207,42,29],'fixed_props':[[40,247,177,284]],
  'regions':[region('torso',[215,217],[30,25],1.2,1.2,1.2)]},
}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');args=parser.parse_args()
    raw_sample=clean_alpha(Image.open(SOURCE/'6-cutout.png'))
    raw_sample.save(SOURCE/'6-clean-alpha.png')
    image=normalize(raw_sample)
    metadata={'happy':bake('happy',image,SAMPLE_RIG)}
    if not args.sample:
        for kind,number,fraction in [('office',2,.64),('desktop',4,.94),('late_scene',7,.94)]:
            raw=Image.open(SOURCE/('2-repaired.png' if number==2 else f'{number}-cutout.png')).convert('RGBA')
            if number==7:
                # Remove generated translucent landscape glow, preserving the
                # opaque character and a short antialias transition only.
                raw.putalpha(raw.getchannel('A').point(lambda v:max(0,min(255,round((v-170)*255/75)))))
                raw.save(SOURCE/'7-clean-alpha.png')
                patch=raw.copy()
                patch_alpha=patch.getchannel('A')
                bounds=patch_alpha.getbbox()
                ImageDraw.Draw(patch_alpha).rectangle((0,0,patch.width,bounds[1]+round((bounds[3]-bounds[1])*.82)),fill=0)
                patch.putalpha(patch_alpha);patch.save(SOURCE/'7-bottom-contour-repair.png')
            raw=clean_alpha(raw)
            raw.save(SOURCE/f'{number}-clean-alpha.png')
            normalized=normalize(raw,fraction)
            metadata[kind]=bake(kind,normalized,RIGS[kind])
        for kind in ('normal','late','sleep'):
            # Reuse existing transparent source art for 1/3/5, without new synthesis.
            original=AUTHOR/kind/'input-before-registration.png'
            if not original.exists():original=AUTHOR/kind/'source.png'
            if not original.exists():original=ROOT/'backups/before-body-animation'/f'{kind}.png'
            normalized=Image.open(original).convert('RGBA')
            clips=('idle',) if kind=='sleep' else ('idle','interact','happy','walk') if kind=='normal' else ('idle','interact','happy')
            metadata[kind]=bake(kind,normalized,RIGS[kind],clips)
    (OUT/'animations/manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    if not args.sample:
        import subprocess,sys
        subprocess.run([sys.executable,str(ROOT/'tools/render_body_previews.py')],check=True)
    print('Sample ready:',DOC/'happy-happy.gif')

if __name__=='__main__':main()
