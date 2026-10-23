"""Assemble local platform installers + guide, retaining older releases."""
import hashlib
import json
import plistlib
import shutil
import struct
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
version=sys.argv[1] if len(sys.argv)>1 else '1.01'
ci=ROOT/'deliverables'/(sys.argv[2] if len(sys.argv)>2 else f'{version}-ci')
release=ROOT/'deliverables'/f'ChiikawaPet-{version}'
release.mkdir(exist_ok=True)
metadata=[]

for arch,cpu,platform_name in [('arm64',0x100000c,'Mac-AppleSilicon'),('x86_64',0x1000007,'Mac-Intel')]:
    source=ci/f'ChiikawaPet-macOS-{arch}'
    report=json.loads((source/f'macos-{arch}-check.json').read_text())
    assert report['success'] and report['pat_response']
    for line in (source/f'macOS-{arch}-SHA256.txt').read_text().splitlines():
        digest,name=line.split(None,1)
        assert hashlib.sha256((source/Path(name.strip()).name).read_bytes()).hexdigest()==digest
    dmg=source/f'ChiikawaPet-macOS-{arch}.dmg'
    with dmg.open('rb') as file:
        file.seek(-512,2);assert file.read(4)==b'koly'
    with zipfile.ZipFile(source/f'ChiikawaPet-macOS-{arch}.zip') as zipped:
        names={(i.filename if i.flag_bits&0x800 else i.filename.encode('cp437').decode('utf-8')):i for i in zipped.infolist()}
        executable=next(n for n in names if n.endswith('.app/Contents/MacOS/ChiikawaPet'))
        with zipped.open(names[executable]) as file:
            assert struct.unpack('<II',file.read(8))==(0xfeedfacf,cpu)
        info=next(n for n in names if n.endswith('.app/Contents/Info.plist'))
        assert plistlib.loads(zipped.read(names[info]))['CFBundleShortVersionString']=='1.0.1'
        for extension in ('html','txt'):
            guide=next(n for n in names if n.endswith('.app/Contents/Resources/使用说明.'+extension))
            assert zipped.read(names[guide]).replace(b'\r\n',b'\n')==(ROOT/'packaging'/('使用说明.'+extension)).read_bytes().replace(b'\r\n',b'\n')
    target=release/platform_name;target.mkdir(exist_ok=True)
    for file in (dmg,source/f'macos-{arch}-check.json'):
        shutil.copy2(file,target/file.name)
    metadata.append({'platform':platform_name,'native_architecture_verified':True,'app_version':'1.0.1','check':report})

windows=release/'Windows';windows.mkdir(exist_ok=True)
for name in ('ChiikawaPet-Windows-Setup.exe',f'windows-{version}-installed-check.json',f'windows-{version}-installer-test.json'):
    shutil.copy2(ROOT/'deliverables'/name,windows/name)
installed=json.loads((windows/f'windows-{version}-installed-check.json').read_text())
assert installed['success'] and installed['pat_response']
installer=json.loads((windows/f'windows-{version}-installer-test.json').read_text(encoding='utf-8-sig'))
assert installer['InstallExitCode']==0 and installer['UninstallExitCode']==0
assert installer['PersonalConfigurationUnchanged']
metadata.append({'platform':'Windows','check':installed,'installer':installer})

files=[]
for folder in release.iterdir():
    if not folder.is_dir():continue
    for extension in ('html','txt'):
        shutil.copy2(ROOT/'packaging'/('使用说明.'+extension),folder/('使用说明.'+extension))
    lines=[hashlib.sha256(file.read_bytes()).hexdigest()+'  '+file.name for file in sorted(folder.iterdir()) if file.is_file() and file.name!='SHA256SUMS.txt']
    (folder/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    output=ROOT/'deliverables'/f'ChiikawaPet-{folder.name}-{version}.zip'
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as zipped:
        for file in folder.iterdir():zipped.write(file,folder.name+'/'+file.name)
    with zipfile.ZipFile(output) as zipped:assert zipped.testzip() is None
    files.append({'name':output.name,'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()})
    print(output.name,output.stat().st_size)

(ROOT/'docs/v1.01/builds.json').write_text(json.dumps({'version':version,'files':files,'checks':metadata},ensure_ascii=False,indent=2),encoding='utf-8')
