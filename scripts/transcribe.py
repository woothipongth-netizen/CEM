"""ถอดเสียงภาษาไทยเป็นข้อความพร้อมเวลา: ElevenLabs (Scribe) เป็นหลัก, Whisper small เป็นทางสำรอง

ใช้: python3 -I scripts/transcribe.py <ไฟล์เสียงหรือวิดีโอ> <โฟลเดอร์ผลลัพธ์> [--engine auto|elevenlabs|whisper] [--model small] [--prompt "คำเฉพาะ"]

เขียน transcript.json (มีเวลาของแต่ละวลี) และ transcript.txt · ElevenLabs เขียน words.json (เวลาทีละพยางค์/คำ) เพิ่ม
--engine auto (ค่าเริ่ม): ลอง ElevenLabs ก่อน (ต้องมีคีย์ใน environment: network secret ของ api.elevenlabs.io)
  ไม่มีคีย์ / เครดิตหมด / ต่อไม่ได้ → ใช้ Whisper อัตโนมัติ และพิมพ์บอกว่าใช้ตัวไหน
ElevenLabs: เร็ว (~3 วินาทีต่อเสียง 6 วินาที) สะกดไทยดีกว่า small มาก แต่ยังเดาคำที่ไม่ชัดได้ ต้องให้คนตรวจซับเหมือนเดิม

--- ส่วน Whisper ---

ตัดเสียงเป็นท่อน ~6 วินาทีขึ้นไปตรงจังหวะหยุดหายใจ แล้วถอดทีละท่อน (beam 5, ปิด VAD, ไม่ต่อบริบทข้ามท่อน)
ทำไม: ถอดทั้งไฟล์รวดเดียว (VAD + ต่อบริบท) ทำให้ small เพี้ยนเป็นภาษาอังกฤษกลางประโยค
และตกท้ายไฟล์ไปทั้งช่วง (61 วินาที ได้แค่ 43) แบบทีละท่อนได้ครบทุกคำ ใช้ ~1.5 นาทีต่อเสียง 40-60 วินาที
--prompt: ใส่ชื่อคนพูด ชื่อบริการ คำเฉพาะของร้าน ช่วยให้สะกดถูกขึ้น (ค่าเริ่มต้นดึง staff_name จาก brand.json)
ผลลัพธ์จากโมเดลเล็กต้องให้คนตรวจทุกครั้ง โดยเฉพาะชื่อเฉพาะและศัพท์อาชีพ
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("audio")
ap.add_argument("out_dir")
ap.add_argument("--model", default="small")
ap.add_argument("--language", default="th")
ap.add_argument("--prompt", default=None)
ap.add_argument("--min-chunk", type=float, default=6.0)
ap.add_argument("--engine", choices=["auto", "elevenlabs", "whisper"], default="auto")
args = ap.parse_args()

out = Path(args.out_dir)
out.mkdir(parents=True, exist_ok=True)


def write(rows, engine):
    (out / "transcript.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    (out / "transcript.txt").write_text(
        "\n".join(f"{r['start']:6.2f}-{r['end']:6.2f} {r['text']}" for r in rows) + "\n")
    print(f"ENGINE: {engine}")
    print(f"TRANSCRIPT: {out / 'transcript.json'}")


def elevenlabs():
    """ElevenLabs Scribe: คืนวลี (ตัดตามช่องว่าง/จังหวะหยุด) หรือ None ถ้าใช้ไม่ได้"""
    import tempfile, urllib.request, uuid
    with tempfile.TemporaryDirectory() as td:
        mp3 = Path(td) / "a.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", args.audio, "-vn", "-ac", "1", "-b:a", "96k", str(mp3)], check=True)
        b = uuid.uuid4().hex
        fields = {"model_id": "scribe_v1", "language_code": "tha", "timestamps_granularity": "word",
                  "tag_audio_events": "false"}
        body = b"".join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items())
        body += (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n').encode()
        body += mp3.read_bytes() + f"\r\n--{b}--\r\n".encode()
    # คีย์จริงถูกใส่โดย proxy ของ environment (network secret) ค่านี้เป็นแค่ตัวแทน
    req = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=body, method="POST",
                                 headers={"xi-api-key": "set-by-environment", "Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            d = json.loads(r.read())
    except Exception as e:
        print(f"ElevenLabs ใช้ไม่ได้ ({e}) → ใช้ Whisper แทน")
        return None
    toks = d.get("words", [])
    (out / "words.json").write_text(json.dumps(toks, ensure_ascii=False, indent=1))
    rows, cur = [], None
    for t in toks:
        if t.get("type") == "spacing":
            # ช่องว่างในภาษาไทย = จบวลี · หยุดหายใจนาน = จบวลีแน่นอน
            if cur:
                rows.append(cur); cur = None
            continue
        if t.get("type") != "word":
            continue
        # จบวลีเมื่อหยุดหายใจ หรือวลียาวเกิน 20 ตัวอักษรแล้วเจอช่วงเว้น ≥0.15 วินาที (ไทยมักไม่เว้นวรรค · เว้นสั้นกว่านี้มักตัดกลางคำ)
        # ซับจริงตัดให้สั้นอีกทีด้วย split_captions.py
        if cur and (t["start"] - cur["end"] >= 0.35 or (len(cur["text"]) >= 20 and t["start"] - cur["end"] >= 0.15)):
            rows.append(cur); cur = None
        if cur is None:
            cur = {"start": round(t["start"], 2), "end": round(t["end"], 2), "text": t["text"]}
        else:
            cur["end"] = round(t["end"], 2); cur["text"] += t["text"]
    if cur:
        rows.append(cur)
    for r in rows:
        print(f"{r['start']:6.2f}-{r['end']:6.2f} {r['text']}", flush=True)
    return rows


if args.engine in ("auto", "elevenlabs"):
    rows = elevenlabs()
    if rows is not None:
        write(rows, "elevenlabs")
        raise SystemExit(0)
    if args.engine == "elevenlabs":
        raise SystemExit("ElevenLabs ใช้ไม่ได้ (ตรวจคีย์ใน environment)")

import numpy as np
from faster_whisper import WhisperModel

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

write(rows, "whisper-" + args.model)
