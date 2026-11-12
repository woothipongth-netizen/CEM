#!/usr/bin/env python3
"""สร้างเสียงพากย์ด้วย ElevenLabs จากสคริปต์ (เสียง/โมเดล/ค่าปรับ จาก brand.json → "tts")

ใช้: python3 -I scripts/tts.py <สคริปต์.txt> <ผลลัพธ์.mp3> [--show]
  - แทนคำที่ AI อ่านเพี้ยนตาม config/pronounce.json ก่อนส่ง (ซับยังใช้สคริปต์เดิม ไม่ใช่ข้อความที่แทนแล้ว)
  - --show: พิมพ์ข้อความที่จะส่งให้ AI แล้วจบ (ไม่เจนเสียง ไม่ใช้เครดิต)
brand.json → "tts": {"voice_id": "...", "model": "eleven_v4", "stability": 0.5, "similarity": 0.75}
  ค่าเหล่านี้ต้องตรงกับที่เจ้าของใช้ในแอป ElevenLabs (ทดสอบแล้ว: v2/v3 สำเนียงไทยเพี้ยน, v4 ตรงกับแอป)
คีย์มาจาก network secret ของ environment (api.elevenlabs.io) ไม่มีคีย์ในโค้ด
ข้อจำกัดที่เจอ: ประโยคยาว AI ผันวรรณยุกต์เพี้ยน (เช่น "สัก" → "ซัก") ทั้งที่คำเดี่ยวอ่านถูก
  → เพิ่มคำใน config/pronounce.json ทีละคำ หลังเจ้าของฟังยืนยัน (ระบบถอดเสียงจับวรรณยุกต์เพี้ยนไม่ได้)
"""
import json, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
show = "--show" in sys.argv
if len(args) != 2:
    sys.exit(__doc__)
text = Path(args[0]).read_text().strip()
pron = {k: v for k, v in json.loads((ROOT / "config" / "pronounce.json").read_text()).items() if not k.startswith("_")}
for k in sorted(pron, key=len, reverse=True):
    text = text.replace(k, pron[k])
if show:
    print(text); raise SystemExit(0)
cfg = json.loads((ROOT / "brand.json").read_text()).get("tts", {})
if not cfg.get("voice_id"):
    sys.exit('ยังไม่ได้ตั้งเสียง: ใส่ brand.json → "tts": {"voice_id": ...}')
body = {"text": text, "model_id": cfg.get("model", "eleven_v4"),
        "voice_settings": {"stability": cfg.get("stability", 0.5), "similarity_boost": cfg.get("similarity", 0.75)}}
req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{cfg['voice_id']}",
                             data=json.dumps(body, ensure_ascii=False).encode(), method="POST",
                             headers={"xi-api-key": "set-by-environment", "Content-Type": "application/json"})
Path(args[1]).write_bytes(urllib.request.urlopen(req, timeout=300).read())
print(f"เสียงพากย์: {args[1]}")
