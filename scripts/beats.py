#!/usr/bin/env python3
"""หาจังหวะเพลง แล้วขยับจุดตัดให้ตรงจังหวะ (ตัดภาพตามจังหวะเพลง)

ใช้:
  python3 scripts/beats.py <เพลง> --start 12.0 --length 45 [--snap "3.0 9.0 15.0" --tol 0.25] [--json beats.json]
    --start   เริ่มเพลงที่วินาทีไหน (ตรงกับ BGM_START ของ mix_audio.sh)
    --length  ความยาวคลิป
    --snap    จุดตัดเดิม (วินาทีในคลิป) → พิมพ์จุดตัดใหม่ที่ตรงจังหวะ ขยับไม่เกิน --tol วินาที
              จุดที่ห่างจังหวะเกิน tol คงไว้ตามเดิม (ภาพต้องตรงกับเสียงพูดก่อนเสมอ)
    --suggest-start  แนะนำวินาทีเริ่มเพลงที่ทำให้จุดตัดตรงจังหวะมากที่สุด (ลองช่วง 0–30 วินาที)

ผลลัพธ์: เวลาจังหวะ (beat) และจังหวะหนัก (downbeat โดยประมาณ ทุก 4 จังหวะ) ในเวลาของคลิป
นำจุดตัดใหม่ไปใส่ shots (at/dur) และ titles (start/end) ก่อนตัดช็อต
ข้อห้าม: ห้ามขยับจุดตัดจนภาพไม่ตรงกับคำพูด ถ้าจุดไหนสำคัญกับคำพูด ให้คงเดิม
"""
import argparse, json, sys


def load(path, sr=22050, offset=0.0, duration=None):
    """ถอดเสียงด้วย ffmpeg (รองรับไฟล์นามสกุลไม่ตรงชนิดจริง เช่น m4a ที่ตั้งชื่อ .mp3 และชื่อไฟล์ภาษาไทย)"""
    import subprocess, numpy as np
    cmd = ["ffmpeg", "-v", "error", "-ss", str(offset), "-i", str(path)]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += ["-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy(), sr


def beat_times(path, start, length):
    import librosa, numpy as np
    y, sr = load(path, offset=start, duration=length + 1)
    tempo, frames = librosa.beat.beat_track(y=y, sr=sr)
    t = librosa.frames_to_time(frames, sr=sr)
    return float(np.atleast_1d(tempo)[0]), [round(float(x), 3) for x in t if x <= length]


def snap(cuts, beats, tol):
    out = []
    for c in cuts:
        b = min(beats, key=lambda x: abs(x - c)) if beats else c
        out.append((c, b if abs(b - c) <= tol else c, abs(b - c) <= tol))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("song"); ap.add_argument("--start", type=float, default=0.0); ap.add_argument("--length", type=float, required=True)
    ap.add_argument("--snap", default=""); ap.add_argument("--tol", type=float, default=0.25)
    ap.add_argument("--suggest-start", action="store_true"); ap.add_argument("--json")
    a = ap.parse_args()
    cuts = [float(x) for x in a.snap.split()] if a.snap else []

    if a.suggest_start and cuts:
        best = None
        for s10 in range(0, 301, 5):  # 0.0–30.0 ทุก 0.5 วินาที
            s = s10 / 10
            try:
                _, bt = beat_times(a.song, s, a.length)
            except Exception:
                break
            if not bt:
                continue
            err = sum(min(abs(b - c) for b in bt) for c in cuts) / len(cuts)
            if best is None or err < best[0]:
                best = (err, s)
        if best:
            print(f"แนะนำเริ่มเพลงที่ {best[1]:.1f} วินาที (จุดตัดห่างจังหวะเฉลี่ย {best[0]:.2f} วินาที)")
            a.start = best[1]

    tempo, bt = beat_times(a.song, a.start, a.length)
    print(f"ความเร็ว {tempo:.1f} BPM · {len(bt)} จังหวะใน {a.length:.0f} วินาที (เริ่มเพลงที่ {a.start:.1f})")
    down = bt[::4]
    if cuts:
        res = snap(cuts, bt, a.tol)
        print("จุดตัดเดิม → ใหม่")
        for c, n, ok in res:
            print(f"  {c:7.2f} → {n:7.2f}" + ("" if ok else "  (ห่างจังหวะเกิน คงเดิม)"))
        print("SNAPPED " + " ".join(f"{n:.2f}" for _, n, _ in res))
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"start": a.start, "bpm": tempo, "beats": bt, "downbeats": down,
                       "snapped": [n for _, n, _ in snap(cuts, bt, a.tol)] if cuts else []}, f)


if __name__ == "__main__":
    main()
