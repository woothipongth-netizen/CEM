#!/usr/bin/env python3
"""สร้างเสียงพากย์ด้วย ElevenLabs จากสคริปต์ (เสียง/โมเดล/ค่าปรับ จาก brand.json → "tts")

ใช้: python3 -I scripts/tts.py <สคริปต์.txt> <ผลลัพธ์.mp3> [--show] [--whole]
  ค่าเริ่ม: เจนทีละประโยค (บรรทัดละประโยค · ถ้าทั้งไฟล์มีบรรทัดเดียว แยกตามช่องว่าง) แล้วต่อด้วยช่วงเงียบ 0.35 วินาที
  และเขียน <ผลลัพธ์>.json = เวลาเริ่ม/จบของแต่ละประโยค ใช้วางซับ/หัวข้อได้ทันที (ทดสอบแล้วในร้านทดสอบ)
  --whole: เจนรวดเดียวทั้งสคริปต์ (ไม่มีไฟล์เวลา)
  - แทนคำที่ AI อ่านเพี้ยนตาม config/pronounce.json ก่อนส่ง (ซับยังใช้สคริปต์เดิม ไม่ใช่ข้อความที่แทนแล้ว)
  - --show: พิมพ์ข้อความที่จะส่งให้ AI แล้วจบ (ไม่เจนเสียง ไม่ใช้เครดิต)
brand.json → "tts": {"voice_id": "...", "model": "eleven_v4", "stability": 0.5, "similarity": 0.75}
  ภาษาไทยใช้ model "eleven_v4" เท่านั้น (v2/v3 ออกเสียงไทยเพี้ยน เช่น "แพงไหม" → "เพราะมั้ย") ห้ามเดาโมเดลเอง
  คีย์อาจไม่มีสิทธิ์ models_read (ดูรายชื่อโมเดลไม่ได้) → เรียกด้วยชื่อโมเดลตรงๆ · รายชื่อเสียงอ่านได้ (หาเสียงโคลนของเจ้าของจากชื่อ)
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
raw = Path(args[0]).read_text().strip()
pron = {k: v for k, v in json.loads((ROOT / "config" / "pronounce.json").read_text()).items() if not k.startswith("_")}


def fix(t):
    for k in sorted(pron, key=len, reverse=True):
        t = t.replace(k, pron[k])
    return t


whole = "--whole" in sys.argv
lines = [l.strip() for l in raw.splitlines() if l.strip()]
sents = [raw] if whole else (lines if len(lines) > 1 else [x for x in raw.split() if x])
if show:
    print("\n".join(fix(x) for x in sents)); raise SystemExit(0)
cfg = json.loads((ROOT / "brand.json").read_text()).get("tts", {})
if not cfg.get("voice_id"):
    sys.exit('ยังไม่ได้ตั้งเสียง: ใส่ brand.json → "tts": {"voice_id": ...}')


def speak(t, prev="", nxt=""):
    body = {"text": fix(t), "model_id": cfg.get("model", "eleven_v4"),
            "voice_settings": {"stability": cfg.get("stability", 0.5), "similarity_boost": cfg.get("similarity", 0.75)}}
    if prev: body["previous_text"] = fix(prev)[-300:]
    if nxt: body["next_text"] = fix(nxt)[:300]
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{cfg['voice_id']}",
                                 data=json.dumps(body, ensure_ascii=False).encode(), method="POST",
                                 headers={"xi-api-key": "set-by-environment", "Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=300).read()


out = Path(args[1])
if whole:
    out.write_bytes(speak(raw)); print(f"เสียงพากย์: {out}"); raise SystemExit(0)

import subprocess, tempfile
GAP = 0.35
with tempfile.TemporaryDirectory() as td:
    parts, times, t0 = [], [], 0.0
    for i, t in enumerate(sents):
        mp3 = Path(td) / f"{i}.mp3"; wav = Path(td) / f"{i}.wav"
        mp3.write_bytes(speak(t, " ".join(sents[:i]), " ".join(sents[i + 1:])))
        # ตัดเงียบหัวท้าย เพื่อให้ช่วงหยุดระหว่างประโยคเท่ากันทุกจุด
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-af",
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                        "-ar", "44100", "-ac", "1", str(wav)], check=True)
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)],
                                 capture_output=True, text=True).stdout)
        times.append({"start": round(t0, 2), "end": round(t0 + d, 2), "text": t})
        t0 += d + GAP
        parts.append(wav)
    gap = Path(td) / "gap.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono", "-t", str(GAP), str(gap)], check=True)
    lst = Path(td) / "l.txt"
    lst.write_text("".join(f"file '{p}'\nfile '{gap}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-b:a", "128k", str(out)], check=True)
out.with_suffix(".json").write_text(json.dumps(times, ensure_ascii=False, indent=1))
print(f"เสียงพากย์: {out} ({len(sents)} ประโยค) · เวลาแต่ละประโยค: {out.with_suffix('.json')}")
