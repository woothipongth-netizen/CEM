#!/usr/bin/env python3
"""วิเคราะห์คลังเพลง แล้วช่วยเลือกเพลงให้เข้ากับคลิป

ใช้:
  python3 scripts/music_index.py scan <โฟลเดอร์เพลง> [--out music_index.json]
      วัดทุกเพลง: ความยาว, ความเร็ว (BPM), ความดัง/พลัง (energy), ความสว่างของเสียง → จัดกลุ่ม ช้า/กลาง/เร็ว
      เพลงที่วัดแล้วจะไม่วัดซ้ำ (ดูจากชื่อไฟล์ + ขนาด)
  python3 scripts/music_index.py pick <music_index.json> --length 45 --pace fast|medium|slow [--mood soft|bright] [-n 5]
      เรียงเพลงที่เข้ากับคลิป: ยาวพอ (หรือวนได้), จังหวะตรงกับ pace, อารมณ์ตรง mood

pace มาจากโปรไฟล์: จังหวะ "เร็ว กระชับ" = fast, "ช้า นุ่มนวล" = slow, ไม่ระบุ = medium
mood: soft = นุ่ม หรู อบอุ่น (energy ต่ำ เสียงไม่แหลม) · bright = สนุก สดใส (energy สูง)
  python3 scripts/music_index.py moments <เพลงหรือโฟลเดอร์> --style front|drop [-n 5]
      หาช่วงในเพลงตามบทบาท (เรียงเพลงที่เข้าที่สุดก่อน):
      front = เพลงเปิดคลิป: จุดที่เพลงเข้าแรงที่สุด → เริ่มเพลง (BGM_START) ตรงจุดนั้น
      drop  = ก่อน-หลัง: ช่วงดนตรีเบาแต่จังหวะไต่ขึ้น แล้วปะทะ → ให้จุดปะทะตรงวินาทีที่ภาพหลังขึ้น
              BGM_START = จุดปะทะ − เวลาที่ภาพหลังขึ้นในคลิป
  python3 scripts/music_index.py preview <ผล moments.json> <out.mp4> [--before 6 --after 4]
      ทำคลิปฟังตัวอย่างต่อกันทุกเพลง (ป้ายชื่อเพลง, ก่อน/หลัง) ส่งให้เจ้าของเลือก

ต้องมี librosa (scripts/setup.sh ติดตั้งให้)
"""
import argparse, json, re, sys
from pathlib import Path

EXT = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}


def load(path, sr=22050, offset=0.0, duration=None):
    """ถอดเสียงด้วย ffmpeg (รองรับไฟล์นามสกุลไม่ตรงชนิดจริง เช่น m4a ที่ตั้งชื่อ .mp3 และชื่อไฟล์ภาษาไทย)"""
    import subprocess, numpy as np
    cmd = ["ffmpeg", "-v", "error", "-ss", str(offset), "-i", str(path)]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += ["-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy(), sr


def analyze(path):
    import librosa, numpy as np
    y, sr = load(path, duration=150)  # 2.5 นาทีแรกพอ
    import subprocess
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                               capture_output=True, text=True).stdout.strip() or 0)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])
    rms = librosa.feature.rms(y=y)[0]
    cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    return {
        "duration": round(dur, 1),
        "bpm": fold(tempo),
        "energy": round(float(np.mean(rms)), 4),
        "brightness": round(float(np.mean(cent)), 0),
        "punch": round(float(np.mean(onset)), 3),
        "beat_regularity": round(float(1 / (1 + np.std(np.diff(librosa.frames_to_time(beats, sr=sr))))) if len(beats) > 4 else 0, 3),
    }


def fold(bpm):
    """ตัวตรวจจังหวะมักนับเป็นสองเท่าหรือครึ่ง: พับให้อยู่ช่วง 75–150 ที่หูคนรับรู้"""
    while bpm > 150:
        bpm /= 2
    while bpm and bpm < 75:
        bpm *= 2
    return round(bpm, 1)


def pace_of(bpm):
    bpm = fold(bpm)
    if bpm < 95:
        return "slow"
    if bpm < 125:
        return "medium"
    return "fast"


def scan(a):
    folder = Path(a.folder)
    out = Path(a.out or folder / "music_index.json")
    idx = json.loads(out.read_text()) if out.exists() else {}
    files = sorted(p for p in folder.rglob("*") if p.suffix.lower() in EXT)
    for p in files:
        key = p.name
        if key in idx and idx[key].get("size") == p.stat().st_size:
            continue
        try:
            r = analyze(p)
        except Exception as e:
            print(f"ข้าม {p.name}: {e}", file=sys.stderr)
            continue
        import re
        hint = re.search(r"(\d{2,3})\s*bpm", p.name, re.I)  # ชื่อไฟล์บอก BPM ไว้ เชื่อชื่อไฟล์ก่อน
        if hint:
            r["bpm"] = float(hint.group(1))
        r.update({"size": p.stat().st_size, "path": str(p), "pace": pace_of(r["bpm"])})
        idx[key] = r
        print(f"{r['pace']:6} {r['bpm']:6.1f} BPM {r['duration']:6.1f}s  energy {r['energy']:.3f}  {p.name}")
        out.write_text(json.dumps(idx, ensure_ascii=False, indent=1))
    # ค่าอ้างอิงสำหรับ mood: เทียบกับค่ากลางของคลังนี้
    vals = sorted(v["energy"] for v in idx.values())
    if vals:
        mid = vals[len(vals) // 2]
        for v in idx.values():
            v["mood"] = "bright" if v["energy"] >= mid else "soft"
    out.write_text(json.dumps(idx, ensure_ascii=False, indent=1))
    print(f"บันทึก {len(idx)} เพลง → {out}")


def pick(a):
    idx = json.loads(Path(a.index).read_text())
    target = {"slow": 85, "medium": 112, "fast": 135}[a.pace]
    rows = []
    for name, v in idx.items():
        bpm = v["bpm"]
        # นับครึ่ง/สองเท่าได้ (เพลง 70 BPM ฟังเป็น 140 ได้)
        d = abs(fold(bpm) - target)
        score = d / 10
        if v["duration"] < a.length:
            score += 2 if v["duration"] >= a.length * 0.6 else 5  # สั้นไปต้องวน
        if a.mood and v.get("mood") != a.mood:
            score += 1.5
        score -= v.get("beat_regularity", 0)  # จังหวะสม่ำเสมอ ตัดตามจังหวะง่าย
        rows.append((score, name, v))
    rows.sort(key=lambda r: r[0])
    for score, name, v in rows[: a.n]:
        print(f"{score:5.2f}  {v['pace']:6} {v['bpm']:6.1f} BPM  {v['duration']:6.1f}s  {v.get('mood', '?'):6}  {name}")


def moments_of(path, style):
    import librosa, numpy as np
    y, sr = load(path, duration=120)
    hop = 512; fps = sr / hop
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    best = None
    for b in librosa.frames_to_time(beats, sr=sr):
        lo = 7 if style == "drop" else 2
        if b < lo or b > 100:
            continue
        k = int(b * fps)
        pre = rms[k - int((6 if style == "drop" else 1.5) * fps):k]
        post = rms[k:k + int((4 if style == "drop" else 2) * fps)]
        if len(post) < int(1.5 * fps) or len(pre) < 4:
            continue
        ratio = float(post.mean() / (pre.mean() + 1e-4))
        if style == "drop":  # ก่อนปะทะต้องเบาและค่อยๆ ไต่ขึ้น
            rise = float(np.polyfit(np.arange(len(pre)), pre, 1)[0] * len(pre) / (pre.mean() + 1e-4))
            quiet = 1 - min(float(pre.mean() / (rms.max() + 1e-4)), 1)
            score = ratio * (1 + max(rise, 0)) * (0.5 + quiet)
        else:  # เปิดคลิป: ปะทะแรงและดังต่อเนื่อง
            score = ratio * float(post.mean())
        if best is None or score > best["score"]:
            best = {"score": round(score, 2), "at": round(float(b), 2), "ratio": round(ratio, 2)}
    if best:
        best["bpm"] = fold(float(np.atleast_1d(tempo)[0]))
    return best


def moments(a):
    src = Path(a.src)
    files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.suffix.lower() in EXT)
    rows = []
    for p in files:
        try:
            m = moments_of(p, a.style)
        except Exception as e:
            print(f"ข้าม {p.name}: {e}", file=sys.stderr); continue
        if m:
            m["path"] = str(p); m["name"] = p.stem; rows.append(m)
    rows.sort(key=lambda r: -r["score"])
    rows = rows[: a.n]
    word = "จุดปะทะ" if a.style == "drop" else "จุดเพลงเข้าแรง"
    for r in rows:
        print(f"{r['score']:7.2f}  {r['bpm']:6.1f} BPM  {word} {r['at']:6.2f}s  ดังขึ้น {r['ratio']:.1f} เท่า  {r['name']}")
    out = Path(a.json or "moments.json")
    out.write_text(json.dumps({"style": a.style, "rows": rows}, ensure_ascii=False, indent=1))
    print(f"บันทึก → {out}")


def preview(a):
    import subprocess
    d = json.loads(Path(a.moments).read_text())
    drop = d["style"] == "drop"
    before = a.before if drop else 0
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    tmp = Path(a.out).with_suffix("")
    tmp.mkdir(parents=True, exist_ok=True)
    parts = []
    for k, r in enumerate(d["rows"], 1):
        L = before + a.after
        name = re.sub(r"[^A-Za-z0-9 .!-]", "", r["name"])[:28] or f"song {k}"
        vf = f"[0:v]drawtext=fontfile={font}:text='{k}. {name} ({r['bpm']:.0f} BPM)':fontsize=48:fontcolor=white:x=(w-tw)/2:y=300"
        if drop:
            vf += (f",drawtext=fontfile={font}:text='BEFORE':fontsize=120:fontcolor=0x888888:x=(w-tw)/2:y=(h-th)/2:enable='lt(t,{before})'"
                   f",drawtext=fontfile={font}:text='AFTER':fontsize=150:fontcolor=0xe8c879:x=(w-tw)/2:y=(h-th)/2:enable='gte(t,{before})'")
        o = tmp / f"p{k}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x222222:s=1080x1920:d={L + 0.6}",
                        "-ss", str(max(r["at"] - before, 0)), "-t", str(L), "-i", r["path"],
                        "-filter_complex", vf + f"[v];[1:a]afade=t=in:d=0.3,afade=t=out:st={L - 0.6}:d=0.6,apad=pad_dur=0.6,atrim=0:{L + 0.6}[a]",
                        "-map", "[v]", "-map", "[a]", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(o)], check=True)
        parts.append(o)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", a.out], check=True)
    print(a.out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("scan"); s.add_argument("folder"); s.add_argument("--out"); s.set_defaults(fn=scan)
    p = sp.add_parser("pick"); p.add_argument("index"); p.add_argument("--length", type=float, required=True)
    p.add_argument("--pace", choices=["slow", "medium", "fast"], default="medium")
    p.add_argument("--mood", choices=["soft", "bright"]); p.add_argument("-n", type=int, default=5); p.set_defaults(fn=pick)
    m = sp.add_parser("moments"); m.add_argument("src"); m.add_argument("--style", choices=["front", "drop"], required=True)
    m.add_argument("-n", type=int, default=5); m.add_argument("--json"); m.set_defaults(fn=moments)
    v = sp.add_parser("preview"); v.add_argument("moments"); v.add_argument("out")
    v.add_argument("--before", type=float, default=6); v.add_argument("--after", type=float, default=4); v.set_defaults(fn=preview)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
