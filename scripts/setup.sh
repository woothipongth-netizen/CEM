#!/usr/bin/env bash
# ติดตั้งทุกอย่างที่งานตัดต่อต้องใช้ในเครื่อง cloud ใหม่ รันครั้งแรกของทุกแชท
# ต้องเปิด network ตาม docs/03-cloud-environment.md ก่อน
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="$ROOT/templates/vendor"

echo "== Chrome headless สำหรับ render HyperFrames"
npx -y hyperframes browser ensure

# ฟอนต์อ่านจาก brand.json ("font": ชื่อแพ็กเกจ @fontsource เช่น kanit, prompt, mitr, sarabun)
FONT="$(python3 -c "import json;print(json.load(open('$ROOT/brand.json'))['font'])")"
echo "== GSAP + ฟอนต์ $FONT (cdn.jsdelivr.net ถูกบล็อก จึงเก็บไว้ในเครื่อง)"
rm -rf "$VENDOR/fonts" && mkdir -p "$VENDOR/fonts"
tmp="$(mktemp -d)"
(cd "$tmp" && npm i -s gsap@3.14.2 "@fontsource/$FONT" >/dev/null 2>&1)
cp "$tmp/node_modules/gsap/dist/gsap.min.js" "$VENDOR/"
files="$tmp/node_modules/@fontsource/$FONT/files"
for w in 500 700 800; do
  # ฟอนต์บางตัวไม่มีน้ำหนักนี้ ใช้น้ำหนักที่ใกล้ที่สุดที่มี
  for sub in thai latin; do
    src="$(ls "$files"/"$FONT"-$sub-{$w,700,600,500,400}-normal.woff2 2>/dev/null | head -1 || true)"
    [ -n "$src" ] && cp "$src" "$VENDOR/fonts/brand-$sub-$w-normal.woff2"
  done
done
# ฟอนต์ลายมือ (ไม่บังคับ): brand.json "font_hand"
HAND="$(python3 -c "import json;print(json.load(open('$ROOT/brand.json')).get('font_hand',''))")"
if [ -n "$HAND" ]; then
  echo "== ฟอนต์ลายมือ $HAND"
  (cd "$tmp" && npm i -s "@fontsource/$HAND" >/dev/null 2>&1)
  for sub in thai latin; do
    src="$(ls "$tmp/node_modules/@fontsource/$HAND/files"/"$HAND"-$sub-{400,500,700}-normal.woff2 2>/dev/null | head -1 || true)"
    [ -n "$src" ] && cp "$src" "$VENDOR/fonts/hand-$sub-400-normal.woff2"
  done
fi
rm -rf "$tmp"

echo "== Whisper สำหรับถอดเสียงภาษาไทย"
pip install -q faster-whisper numpy pillow 2>&1 | grep -v "running pip as the 'root'" || true

echo "== เช็กความพร้อม"
npx -y hyperframes doctor 2>&1 | grep -E "FFmpeg|Chrome" || true
python3 -c "import faster_whisper; print('faster-whisper: ok')"
echo "พร้อมใช้งาน"
