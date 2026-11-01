"""ถอดเสียงภาษาไทยเป็นข้อความพร้อมเวลา (Whisper small)

ใช้: python3 -I scripts/transcribe.py <ไฟล์เสียงหรือวิดีโอ> <โฟลเดอร์ผลลัพธ์> [--model small] [--prompt "คำเฉพาะ ชื่อคน ศัพท์อาชีพ"]

เขียน transcript.json (มีเวลาของแต่ละประโยค) และ transcript.txt

ตัดเสียงเป็นท่อน ~6 วินาทีขึ้นไปตรงจังหวะหยุดหายใจ แล้วถอดทีละท่อน (beam 5, ปิด VAD, ไม่ต่อบริบทข้ามท่อน)
ทำไม: ถอดทั้งไฟล์รวดเดียว (VAD + ต่อบริบท) ทำให้ small เพี้ยนเป็นภาษาอังกฤษกลางประโยค
และตกท้ายไฟล์ไปทั้งช่วง (61 วินาที ได้แค่ 43) แบบทีละท่อนได้ครบทุกคำ ใช้ ~1.5 นาทีต่อเสียง 40-60 วินาที
--prompt: ใส่ชื่อช่าง ชื่อบริการ คำเฉพาะของร้าน ช่วยให้สะกดถูกขึ้น (ค่าเริ่มต้นดึง staff_name จาก brand.json)
ผลลัพธ์จากโมเดลเล็กต้องให้คนตรวจทุกครั้ง โดยเฉพาะชื่อเฉพาะและศัพท์อาชีพ
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

ap = argparse.ArgumentParser()
ap.add_argument("audio")
ap.add_argument("out_dir")
ap.add_argument("--model", default="small")
ap.add_argument("--language", default="th")
ap.add_argument("--prompt", default=None)
ap.add_argument("--min-chunk", type=float, default=6.0)
args = ap.parse_args()

out = Path(args.out_dir)
out.mkdir(parents=True, exist_ok=True)
if args.prompt is None:
    brand = json.loads((Path(__file__).resolve().parents[1] / "brand.json").read_text())
    name = brand.get("staff_name", "")
    args.prompt = f"{name} ครับ" if name and name != "xxxx" else ""

# faster-whisper เปิดไฟล์เองแล้วพังกับ PyAV บางเวอร์ชัน จึงแปลงเป็น PCM 16 kHz ด้วย ffmpeg ก่อน
pcm = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", args.audio, "-ar", "16000", "-ac", "1", "-f", "f32le", "-"],
    capture_output=True, check=True,
).stdout
audio = np.frombuffer(pcm, dtype=np.float32)
dur = len(audio) / 16000

# จุดตัดท่อน = กลางช่วงเงียบ ห่างกันอย่างน้อย min-chunk วินาที
err = subprocess.run(["ffmpeg", "-i", args.audio, "-af", "silencedetect=n=-35dB:d=0.25", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
cuts = [0.0]
for a, b in zip(starts, ends):
    m = (a + b) / 2
    if m - cuts[-1] >= args.min_chunk and dur - m >= 1.0:
        cuts.append(m)
cuts.append(dur)

model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=4)
rows = []
for s, e in zip(cuts, cuts[1:]):
    segs, _ = model.transcribe(audio[int(s * 16000):int(e * 16000)], language=args.language, beam_size=5,
                               vad_filter=False, condition_on_previous_text=False,
                               initial_prompt=args.prompt or None)
    for x in segs:
        r = {"start": round(s + x.start, 2), "end": round(s + x.end, 2), "text": x.text.strip()}
        print(f"{r['start']:6.2f}-{r['end']:6.2f} {r['text']}", flush=True)
        rows.append(r)

(out / "transcript.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
(out / "transcript.txt").write_text(
    "\n".join(f"{r['start']:6.2f}-{r['end']:6.2f} {r['text']}" for r in rows) + "\n"
)
print(f"TRANSCRIPT: {out / 'transcript.json'}")
