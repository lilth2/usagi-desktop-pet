#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
arch="${1:-arm64}"
version="1.0.1"
mkdir -p build/mac-icon.iconset deliverables
source_image="assets/chiikawa/processed/normal.png"
for size in 16 32 64 128 256 512; do
  sips -z "$size" "$size" "$source_image" --out "build/mac-icon.iconset/icon_${size}x${size}.png" >/dev/null
  double=$((size*2))
  sips -z "$double" "$double" "$source_image" --out "build/mac-icon.iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns build/mac-icon.iconset -o build/ChiikawaPet.icns
python -m PyInstaller --noconfirm --clean --onedir --windowed \
  --name ChiikawaPet --target-architecture "$arch" \
  --osx-bundle-identifier com.lilth2.chiikawapet \
  --icon build/ChiikawaPet.icns \
  --add-data 'assets/chiikawa/processed:assets/chiikawa/processed' \
  desktop_pet.py
bundle="dist/ChiikawaPet.app"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $version" "$bundle/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :LSMinimumSystemVersion string 11.0' "$bundle/Contents/Info.plist" || \
  /usr/libexec/PlistBuddy -c 'Set :LSMinimumSystemVersion 11.0' "$bundle/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :CFBundleDisplayName string 吉伊卡哇桌宠' "$bundle/Contents/Info.plist" || true
cp packaging/使用说明.html "$bundle/Contents/Resources/使用说明.html"
cp packaging/使用说明.txt "$bundle/Contents/Resources/使用说明.txt"
# Ad-hoc signing satisfies executable integrity on Apple silicon. This is not
# a Developer ID signature/notarization; the user guide explains first launch.
codesign --force --deep --sign - "$bundle"
codesign --verify --deep --strict --verbose=2 "$bundle"
"$bundle/Contents/MacOS/ChiikawaPet" --package-check "deliverables/macos-${arch}-check.json"
python -c "import json; assert json.load(open('deliverables/macos-${arch}-check.json'))['success']"
stage="build/ChiikawaPet-macOS-${arch}"
mkdir -p "$stage"
ditto "$bundle" "$stage/ChiikawaPet.app"
cp packaging/使用说明.html packaging/使用说明.txt "$stage/"
ln -s /Applications "$stage/Applications"
hdiutil create -volname '吉伊卡哇桌宠' -srcfolder "$stage" -ov -format UDZO \
  "deliverables/ChiikawaPet-macOS-${arch}.dmg"
ditto -c -k --sequesterRsrc --keepParent "$stage" "deliverables/ChiikawaPet-macOS-${arch}.zip"
shasum -a 256 deliverables/ChiikawaPet-macOS-* > "deliverables/macOS-${arch}-SHA256.txt"
