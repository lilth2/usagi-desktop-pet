"""Deterministic crop/matte/normalization; never synthesize pixels or poses."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'assets/chiikawa/originals'
OUT = ROOT / 'assets/chiikawa/processed'
DOC = ROOT / 'docs/chiikawa'
NOTES = {
 '1': '白底；卧姿看手机，完整枕被和手机；清晰；用户确认深夜版。',
 '2': '粉色办公室场景；下半身被桌面遮挡；完整场景小卡片，不补画。',
 '3': '白底三角色；只裁取中间完整吉伊卡哇；清晰，适合普通版。',
 '4': '蓝黄办公室背景；电脑遮挡身体；完整场景小卡片，不再额外裁切。',
 '5': '白底；完整侧卧睡姿与枕头；清晰，午睡和夜间共用。',
 '6': '粉白装饰背景；跳跃姿势；完整场景小卡片，没有生成连续帧。',
 '7': '三人夜景；按用户要求保留整张画面，深夜版，不裁切。',
}


def cutout(image, crop, closing):
    image = image.convert('RGB').crop(crop)
    # Close tiny gaps in ink contours only in the segmentation mask, never
    # modify the artwork. Outside flood-fill preserves enclosed white fur.
    ink = image.convert('L').point(lambda v: 255 if v < 210 else 0)
    ink = ImageOps.expand(ink, closing, fill=0)
    ink = ink.filter(ImageFilter.MaxFilter(closing)).filter(ImageFilter.MinFilter(closing))
    outside = ink.copy()
    ImageDraw.floodfill(outside, (0, 0), 128)
    alpha = outside.point(lambda v: 0 if v == 128 else 255)
    alpha = alpha.crop((closing,closing,closing+image.width,closing+image.height))
    # Remove isolated source-edge noise; no generated limb/expression content.
    result = image.convert('RGBA')
    result.putalpha(alpha)
    return result.crop(alpha.getbbox())


def main():
    if (ROOT/'assets/chiikawa/body_sources/6-cutout.png').exists():
        # New transparent-body sources supersede the earlier scene-card build.
        # Do not silently regenerate opaque cards over the animated assets.
        import subprocess,sys
        subprocess.run([sys.executable,str(ROOT/'tools/author_body_animation.py')],check=True)
        return
    OUT.mkdir(parents=True, exist_ok=True); DOC.mkdir(parents=True, exist_ok=True)
    inventory = []
    for p in sorted(SRC.glob('*.png')):
        im = Image.open(p)
        inventory.append({'file':p.name, 'size':list(im.size), 'mode':im.mode,
                          'sha256':hashlib.sha256(p.read_bytes()).hexdigest(), 'notes':NOTES[p.stem]})
    specs = {
        'normal': ('3.png', (310,245,563,535), 33, 230),
        'late': ('1.png', (145,225,740,655), 17, 375),
        'sleep': ('5.png', (165,165,715,545), 17, 380),
    }
    records = {}
    for name, (file, crop, closing, head_width) in specs.items():
        im = cutout(Image.open(SRC/file), crop, closing)
        # Match head width, NOT whole-photo size: target 180px on 320px canvas.
        # Head widths manually measured from source contours at native scale.
        factor = 180 / head_width
        im = im.resize((round(im.width*factor), round(im.height*factor)), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA',(320,320))
        pos = ((320-im.width)//2, 280-im.height)
        canvas.alpha_composite(im,pos)
        canvas.save(OUT/f'{name}.png')
        records[name]={'source':file,'crop':crop,'head_width_source':head_width,
                       'scale':factor,'canvas':[320,320],'baseline':280,
                       'bbox':list(canvas.getbbox()), 'file':f'{name}.png'}
    # Scene photographs stay whole: fit without cropping or distortion.
    for name, file in [('office','2.png'),('desktop','4.png'),('happy','6.png'),('late_scene','7.png')]:
        scene=Image.open(SRC/file).convert('RGBA')
        source_size=scene.size
        scene.thumbnail((280,240),Image.Resampling.LANCZOS)
        canvas=Image.new('RGBA',(320,320))
        canvas.alpha_composite(scene,((320-scene.width)//2,280-scene.height))
        canvas.save(OUT/(name+'.png'))
        records[name]={'source':file,'source_size':list(source_size),'canvas':[320,320],
                       'baseline':280,'bbox':list(canvas.getbbox()),'file':name+'.png',
                       'notes':'完整场景等比缩放，不裁切、不抠图、不补画。'}
    Image.open(OUT/'normal.png').save(OUT/'icon.ico',sizes=[(16,16),(32,32),(48,48),(128,128),(256,256)])
    (DOC/'asset-inventory.json').write_text(json.dumps({'originals':inventory,'processed':records},ensure_ascii=False,indent=2),encoding='utf-8')
    font_path='C:/Windows/Fonts/msyh.ttc'
    font=ImageFont.truetype(font_path,16)
    sheet=Image.new('RGB',(1120,1040),'#fff9f6'); d=ImageDraw.Draw(sheet)
    for index,name in enumerate(records):
        x=(index%4)*280
        y=(index//4)*520
        d.text((x+16,y+10),name,fill='#644d51',font=font)
        im=Image.open(OUT/f'{name}.png')
        for yy in range(y+50,y+330,10):
            for xx in range(x,x+280,10):
                d.rectangle((xx,yy,xx+9,yy+9),fill=('#f1e8e8' if ((xx-x)//10+(yy-y)//10)%2 else '#ffffff'))
        preview=im.resize((280,280),Image.Resampling.LANCZOS)
        sheet.paste(preview,(x,y+50),preview)
        d.line((x,y+295,x+279,y+295),fill='#dba5b5')
        actual=im.resize((110,110),Image.Resampling.LANCZOS)
        sheet.paste(actual,(x+85,y+365),actual)
        d.text((x+40,y+485),'下方为桌面实际尺寸',fill='#644d51',font=font)
    sheet.save(DOC/'asset-preview.png')

if __name__=='__main__': main()
