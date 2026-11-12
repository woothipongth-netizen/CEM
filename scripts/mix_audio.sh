#!/usr/bin/env bash
# มิกซ์เสียง: เสียงพากย์ + เพลงพื้นหลัง (ถ้ามี, ลดเสียงลงเองเมื่อมีคนพูด) + เสียง whoosh ตอนเปลี่ยนช่วง + sparkle ตอนจบ
#
# ใช้: scripts/mix_audio.sh <เสียงพากย์> <เพลง หรือ none> <ผลลัพธ์.wav> <ความยาว> "<เวลา whoosh คั่นด้วยช่องว่าง>" [เวลา sparkle]
#   scripts/mix_audio.sh vo.mp3 none     mix.wav 61 "3.6 14.0 31.9 43.3" 55.5
#   scripts/mix_audio.sh vo.mp3 song.mp3 mix.wav 61 "3.6 14.0 31.9 43.3" 55.5
#
# กฎของร้าน: เพลงต้องเป็นไฟล์ที่ผู้ใช้ส่งมาเท่านั้น ห้ามสร้างหรือหาเพลงเอง ถ้าไม่มีให้ใส่ none
#
# เสียงเอฟเฟกต์มาจาก skill media-use (Pixabay license ใช้เชิงพาณิชย์ได้)
# ระดับเพลงตามแนวทาง media-use: ~-18 dB ใต้เสียงพูด (BGM_BED_VOLUME 0.12)
#
# ตัวเลือกเพลง (ตั้งเป็นตัวแปรก่อนคำสั่ง):
#   BGM_LEVEL=low|mid|high  ความดังเพลง (ค่าเริ่ม mid) · low = เพลงเบา ได้ยินเสียงพูดชัดมาก · high = เพลงเด่น (คลิปไม่มีคนพูดเยอะ)
#   BGM_START=12.5          เริ่มเพลงที่วินาทีไหน (ใช้คู่กับ scripts/beats.py เพื่อให้จุดตัดตรงจังหวะ)
#   BGM_GAP_BOOST=1         ให้เพลงดังขึ้นชัดในช่วงที่ไม่มีคนพูด (ค่าเริ่ม 1 = เปิด, 0 = ปิด)
#   TARGET_LUFS=-14         ปรับความดังทั้งคลิปให้ได้ค่านี้ (พีคไม่เกิน -1 dBTP) ใช้กับคลิปไม่มีเสียงพูด / ก่อนส่งงาน
set -euo pipefail
VO="$1"; BGM="$2"; OUT="$3"; DUR="$4"; WHOOSH="$5"; SPARKLE="${6:-}"
SFX="$(cd "$(dirname "$0")/.." && pwd)/.agents/skills/media-use/audio/assets/sfx"
# คลัง SFX ของร้าน (ดึงจาก brand.json sfx_library มาไว้ในเครื่อง): ตั้ง SFX_DIR=<โฟลเดอร์> ไฟล์ที่ชื่อตรงกันจะใช้แทนของในตัว
#   ใช้ชื่อ whoosh-short.mp3 (เปลี่ยนช่วง) และ sparkle.mp3 (ตอนจบ)
pick() { if [ -n "${SFX_DIR:-}" ] && [ -f "$SFX_DIR/$1" ]; then echo "$SFX_DIR/$1"; else echo "$SFX/$1"; fi; }

if [ "$BGM" = "none" ]; then
  inputs=(-i "$VO")
  filters="[0:a]aresample=48000,apad,atrim=0:$DUR[vo];"
  mix="[vo]"; n=1; idx=1
else
  filters="[0:a]aresample=48000,apad,atrim=0:$DUR,asplit=2[vo][key];"
  # เพลงลดลงอัตโนมัติเมื่อเสียงพากย์ดัง (sidechain) แล้วกลับขึ้นช่วงเงียบ ฐานเสียงราว -18 dB ตาม media-use
  case "${BGM_LEVEL:-mid}" in low) BV=0.3;; high) BV=0.8;; *) BV=0.5;; esac
  if [ "${BGM_GAP_BOOST:-1}" = "1" ]; then RATIO=8; else RATIO=3; fi
  inputs=(-i "$VO" -ss "${BGM_START:-0}" -i "$BGM")
  filters+="[1:a]aresample=48000,loudnorm=I=-20,volume=$BV,afade=t=in:d=0.5,afade=t=out:st=$(python3 -c "print($DUR - 3)"):d=3[bgmraw];"
  filters+="[bgmraw][key]sidechaincompress=threshold=0.02:ratio=$RATIO:attack=20:release=400[bgm];"
  mix="[vo][bgm]"; n=2; idx=2
fi
for t in $WHOOSH; do
  inputs+=(-i "$(pick whoosh-short.mp3)")
  ms=$(python3 -c "print(int(max(0, $t - 0.3) * 1000))")
  filters+="[$idx:a]aresample=48000,volume=0.35,adelay=${ms}|${ms}[w$idx];"
  mix+="[w$idx]"; n=$((n + 1)); idx=$((idx + 1))
done
if [ -n "$SPARKLE" ]; then
  inputs+=(-i "$(pick sparkle.mp3)")
  ms=$(python3 -c "print(int($SPARKLE * 1000 + 300))")
  filters+="[$idx:a]aresample=48000,volume=0.4,adelay=${ms}|${ms}[sp];"
  mix+="[sp]"; n=$((n + 1))
fi
if [ -n "${TARGET_LUFS:-}" ]; then
  filters+="${mix}amix=inputs=$n:normalize=0,atrim=0:$DUR,loudnorm=I=${TARGET_LUFS}:TP=-1.5:LRA=11[o]"
else
  filters+="${mix}amix=inputs=$n:normalize=0,atrim=0:$DUR,alimiter=limit=0.95[o]"
fi
ffmpeg -v error -y "${inputs[@]}" -filter_complex "$filters" -map "[o]" -ar 48000 "$OUT"
echo "มิกซ์แล้ว: $OUT"
