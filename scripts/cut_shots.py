"""ตัดช็อตจากฟุตเทจดิบตามแผน แล้วต่อเป็นวิดีโอเดียว (ไม่มีเสียง) สำหรับใส่ใน HyperFrames

ใช้: python3 -I scripts/cut_shots.py <plan.json> <โฟลเดอร์ฟุตเทจ> <โฟลเดอร์ผลลัพธ์> [--head-pad 0.4] [--curves check.json]

--curves: ค่าการเคลื่อนไหวรายเฟรมจาก check_shots.py ถ้าใส่ จะไม่อ่านไฟล์ 4K ซ้ำเพื่อหาช่วงกล้องนิ่ง
(เร็วขึ้น ~3 เท่า: 19 ช็อต 6.4 → 2.2 นาที) คลิปที่ไม่มีใน check.json จะวัดเองตามเดิม
ช็อตทำพร้อมกัน 4 ช็อต

--head-pad: ตัดเผื่อหัวช็อตไว้อีก N วินาที ให้ช็อตถัดไปเริ่มซ้อนก่อนจุดตัด ใช้กับทรานสิชันแบบ
crossfade ในเทมเพลต review-motion (ถ้าใส่ จะไม่สร้าง base.mp4 เพราะช็อตซ้อนกัน)

plan.json เป็นรายการช็อตเรียงตามลำดับในคลิป:
  [
    {"clip": "C0001.mov", "dur": 3.0, "note": "ก่อนทำ หน้าตรง"},
    {"clip": "C0002.mov", "dur": 3.5, "start": 8.0}
  ]
  - start (ไม่บังคับ): วินาทีที่จะเริ่มตัด ถ้าไม่ใส่ สคริปต์เลือกช่วงที่กล้องนิ่งที่สุดให้

กฎที่มาจากผลทดสอบ (docs/06-lessons.md):
  - ห้ามใช้ MARGIN วินาทีแรกและท้ายของคลิป ตากล้องกำลังกดอัดหรือหันกล้องจะกดหยุด
  - เลือกช่วงที่ภาพเปลี่ยนน้อยที่สุด แทนการตัดรอบจุดที่คมที่สุด (มักอยู่ท้ายคลิป)
  - ทุกช็อตได้ภาพตรวจ <ลำดับ>_check.jpg (ต้น / กลาง / ท้าย) ให้ดูก่อน render

ผลลัพธ์: base.mp4 (1080x1920, 30fps), shots.json (เวลาจริงที่ใช้), ภาพตรวจทุกช็อต, check_all.jpg
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

MARGIN = 2.0          # วินาทีที่ห้ามใช้ ต้นและท้ายคลิป
PAD = 0.0             # --head-pad (กันไม่ให้ส่วนที่ตัดเผื่อหัวช็อตล้ำเข้าไปใน MARGIN)
SAMPLE_FPS = 4        # ความถี่ภาพที่ใช้วัดการเคลื่อนไหว
W, H = 72, 128        # ขนาดภาพเล็กที่ใช้วัด


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out)


def motion_curve(path):
    """ค่าความต่างของภาพระหว่างเฟรมติดกัน (ยิ่งสูง กล้องหรือภาพยิ่งขยับ) ทีละ 1/SAMPLE_FPS วินาที"""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={SAMPLE_FPS},scale={W}:{H},format=gray",
         "-f", "rawvideo", "-"],
        capture_output=True, check=True,
    ).stdout
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, H, W).astype(np.float32)
    return np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))


CURVES = {}


def load_curves(path):
    for r in json.loads(Path(path).read_text()):
        CURVES[r["clip"]] = r["curve"]


def curve_for(path):
    """ใช้ค่าจาก check_shots.py ถ้ามี (YDIF ที่เวลา t = ความต่างจากเฟรมก่อนหน้า จึงเลื่อน 1 ช่องให้ตรงกับ np.diff)"""
    pts = CURVES.get(Path(path).name)
    if not pts:
        return motion_curve(path)
    n = int(round(pts[-1][0] * SAMPLE_FPS)) + 1
    out = np.full(n, np.inf)
    for t, v in pts:
        i = int(round(t * SAMPLE_FPS))
        if i < n:
            out[i] = v
    return out[1:]


def calmest_start(path, dur):
    total = duration(path)
    lo, hi = MARGIN + PAD, total - MARGIN - dur
    if hi < lo:  # คลิปสั้นเกินกว่าจะเว้นขอบได้ครบ ใช้ช่วงกลางคลิป
        return max(0.0, (total - dur) / 2), total
    curve = curve_for(path)
    win = max(1, int(dur * SAMPLE_FPS))
    best, best_t = None, lo
    t = lo
    while t <= hi:
        i = int(t * SAMPLE_FPS)
        score = curve[i:i + win].mean() if i + win <= len(curve) else float("inf")
        if best is None or score < best:
            best, best_t = score, t
        t += 0.25
    return best_t, total


def main():
    # ffmpeg concat อ่าน path ใน list.txt เทียบกับที่อยู่ของ list.txt จึงต้องใช้ path เต็ม
    plan_path, raw_dir, out_dir = (Path(a).resolve() for a in sys.argv[1:4])
    global PAD
    pad = float(sys.argv[sys.argv.index("--head-pad") + 1]) if "--head-pad" in sys.argv else 0.0
    PAD = pad
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = json.loads(plan_path.read_text())
    if "--curves" in sys.argv:
        load_curves(sys.argv[sys.argv.index("--curves") + 1])
    used, lst, checks = [], [], []
    clock = 0.0
    from concurrent.futures import ThreadPoolExecutor

    def work(args):
        i, shot = args
        src = raw_dir / shot["clip"]
        dur = float(shot["dur"])
        if "start" in shot:
            start, total = float(shot["start"]), duration(src)
            if start - min(pad, start) < MARGIN or start + dur > total - MARGIN:
                print(f"เตือน: ช็อต {i} ({shot['clip']}) start={start} ล้ำเข้า {MARGIN} วินาทีแรก/ท้ายของคลิป")
        else:
            start, total = calmest_start(src, dur)
        pad_used = min(pad, start)
        start -= pad_used
        dur_cut = dur + pad_used
        out = out_dir / f"{i:02d}_{src.stem}.mp4"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{dur_cut}", "-i", str(src),
             "-vf", "scale=1080:1920,fps=30,format=yuv420p", "-an", "-c:v", "libx264", "-crf", "18",
             "-preset", "fast", str(out)],
            check=True,
        )
        check = out_dir / f"{i:02d}_check.jpg"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vf",
             f"select='eq(n\\,2)+eq(n\\,{int(dur_cut * 15)})+eq(n\\,{int(dur_cut * 30) - 3})',scale=180:-1,tile=3x1",
             "-vsync", "0", "-frames:v", "1", str(check)],
            check=True,
        )
        return i, shot, src, start, dur, pad_used, total, out, check

    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(work, enumerate(plan)))
    for i, shot, src, start, dur, pad_used, total, out, check in results:
        checks.append(str(check))
        lst.append(f"file '{out}'")
        used.append({"i": i, "clip": shot["clip"], "file": out.name, "src_start": round(start, 2), "dur": dur,
                     "head_pad": round(pad_used, 2),
                     "clip_len": round(total, 2), "at": round(clock, 2), "note": shot.get("note", "")})
        print(f"{i:02d} {shot['clip']:<14} {start:6.2f}s +{dur}s  (คลิปยาว {total:.1f}s)  เริ่มที่ {clock:.2f}s ในคลิปรวม")
        clock += dur

    (out_dir / "list.txt").write_text("\n".join(lst) + "\n")
    if pad == 0:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                        str(out_dir / "list.txt"), "-c", "copy", str(out_dir / "base.mp4")], check=True)
    (out_dir / "shots.json").write_text(json.dumps(used, ensure_ascii=False, indent=1))

    # รวมภาพตรวจทุกช็อตไว้ในภาพเดียว อ่านจากบนลงล่าง ช็อตละแถว
    inputs = sum((["-i", c] for c in checks), [])
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex",
                    f"vstack=inputs={len(checks)}" if len(checks) > 1 else "null",
                    str(out_dir / "check_all.jpg")], check=True)
    print(f"รวม {clock:.2f} วินาที → {out_dir / 'base.mp4'}")
    print(f"ภาพตรวจ: {out_dir / 'check_all.jpg'}")


if __name__ == "__main__":
    main()
