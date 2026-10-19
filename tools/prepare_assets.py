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
 '2': '粉色办公室场景；下半身被桌面遮挡；不补画，不用作透明桌宠。',
 '3': '白底三角色；只裁取中间完整吉伊卡哇；清晰，适合普通版。',
 '4': '蓝黄办公室背景；电脑遮挡身体，左边道具被原图裁切；仅保留参考。',
 '5': '白底；完整侧卧睡姿与枕头；清晰，午睡和夜间共用。',
 '6': '粉白装饰背景；完整跳跃姿势但装饰较多；没有连续帧，仅保留参考。',
 '7': '低分辨率三人夜景；用户确认深夜版，只提取中间吉伊卡哇背影；放大清晰度受限。',
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
    scene=Image.open(SRC/'7.png').convert('RGBA')
    mask=Image.new('L',scene.size)
    points=[(181,131),(180,127),(181,121),(184,117),(189,116),(194,118),(198,123),(207,121),(218,120),(232,122),(233,118),(238,116),(243,117),(248,121),(250,126),(249,132),(256,138),(262,146),(266,155),(268,163),(267,175),(262,185),(256,192),(260,200),(263,208),(262,218),(257,225),(247,228),(232,228),(219,229),(207,226),(200,228),(190,224),(180,223),(173,219),(171,212),(170,205),(172,196),(174,192),(166,183),(163,174),(162,165),(163,154),(167,143),(174,135)]
    ImageDraw.Draw(mask).polygon(points,fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(0.45))
    scene.putalpha(mask); scene=scene.crop(mask.getbbox())
    scale=180/110
    scene=scene.resize((round(scene.width*scale),round(scene.height*scale)),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(320,320));canvas.alpha_composite(scene,((320-scene.width)//2,280-scene.height))
    canvas.save(OUT/'late_scene.png')
    records['late_scene']={'source':'7.png','head_width_source':110,'scale':scale,'canvas':[320,320],'baseline':280,'bbox':list(canvas.getbbox()),'file':'late_scene.png','notes':'低分辨率原图；手工轮廓遮罩，不补画。'}
    Image.open(OUT/'normal.png').save(OUT/'icon.ico',sizes=[(16,16),(32,32),(48,48),(128,128),(256,256)])
    (DOC/'asset-inventory.json').write_text(json.dumps({'originals':inventory,'processed':records},ensure_ascii=False,indent=2),encoding='utf-8')
    font_path='C:/Windows/Fonts/msyh.ttc'
    font=ImageFont.truetype(font_path,16)
    sheet=Image.new('RGB',(1120,520),'#fff9f6'); d=ImageDraw.Draw(sheet)
    for index,name in enumerate(records):
        x=index*280
        d.text((x+16,10),name,fill='#644d51',font=font)
        im=Image.open(OUT/f'{name}.png')
        for yy in range(50,330,10):
            for xx in range(x,x+280,10):
                d.rectangle((xx,yy,xx+9,yy+9),fill=('#f1e8e8' if ((xx-x)//10+yy//10)%2 else '#ffffff'))
        preview=im.resize((280,280),Image.Resampling.LANCZOS)
        sheet.paste(preview,(x,50),preview)
        d.line((x,295,x+279,295),fill='#dba5b5')
        actual=im.resize((110,110),Image.Resampling.LANCZOS)
        sheet.paste(actual,(x+85,365),actual)
        d.text((x+40,485),'下方为桌面实际尺寸',fill='#644d51',font=font)
    sheet.save(DOC/'asset-preview.png')

if __name__=='__main__': main()
