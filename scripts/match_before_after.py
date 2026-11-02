"""หาคู่ภาพ "ก่อน" กับ "หลัง" ที่มุมกล้องและระยะใกล้กันที่สุด สำหรับช่วงเทียบก่อน-หลัง (compare)

ใช้: python3 -I scripts/match_before_after.py <โฟลเดอร์งาน> --before <คลิป...> --after <คลิป...> [--top 5]
  ชื่อคลิปตามที่ติดบนภาพรวม (ไม่ต้องมีนามสกุล) เช่น --before C0001 C0002 --after C0050
อ่านจาก <งาน>/kf/*.mp4 (ไฟล์เฟรมหลักจาก fetch_footage.sh) ไม่ต้องอ่านไฟล์ 4K
ข้าม 2 วินาทีแรกและท้ายของทุกคลิป (กฎของร้าน)

วิธีวัด: ย่อภาพเป็นขาวดำ 54x96 ปรับความสว่าง/คอนทราสต์ให้เท่ากัน แล้ววัดความต่างของโครงภาพ (ขอบ + ตำแหน่งหน้า)
สีปาก/คิ้วที่เปลี่ยนหลังทำมีผลน้อย ค่ายิ่งต่ำยิ่งเหมือน (ต่ำกว่า ~0.35 = มุมเดียวกัน)
ผลลัพธ์: ตารางคู่ที่ดีที่สุด + เวลา (วินาทีในคลิปต้นฉบับ) เอาไปใส่ "start" ใน plan.json ของสองช็อตนั้น
และภาพเทียบ <งาน>/match_before_after.jpg (ซ้าย = ก่อน, ขวา = หลัง) ให้ดูด้วยตาก่อนใช้
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

W, H, STEP, EDGE = 54, 96, 0.5, 2.0


def frames(kf):
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(kf)],
                               capture_output=True, text=True).stdout.strip() or 0)
    if dur <= 2 * EDGE + 0.2:
        return []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(EDGE), "-t", str(dur - 2 * EDGE), "-i", str(kf),
                          "-vf", f"fps={1 / STEP},scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    arr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
    out = []
    for k, f in enumerate(arr):
        f = (f - f.mean()) / (f.std() + 1e-6)
        gy, gx = np.gradient(f)
        e = np.hypot(gx, gy)
        e = (e - e.mean()) / (e.std() + 1e-6)
        out.append((round(EDGE + k * STEP, 2), f, e))
    return out


def score(a, b):
    # โครงสว่าง-มืด (ตำแหน่งหน้า ผม พื้นหลัง) + ขอบ (รูปหน้า ตา จมูก)
    return float(0.5 * np.mean(np.abs(a[1] - b[1])) + 0.5 * np.mean(np.abs(a[2] - b[2]))) / 1.6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--before", nargs="+", required=True)
    ap.add_argument("--after", nargs="+", required=True)
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()
    kf = Path(a.work) / "kf"
    fb = {c: frames(kf / f"{c}.mp4") for c in a.before}
    fa = {c: frames(kf / f"{c}.mp4") for c in a.after}
    res = []
    for cb, lb in fb.items():
        for ca, la in fa.items():
            best = min(((score(x, y), x[0], y[0]) for x in lb for y in la), default=None)
            if best:
                res.append({"before": cb, "before_s": best[1], "after": ca, "after_s": best[2], "diff": round(best[0], 3)})
    res.sort(key=lambda r: r["diff"])
    print(f"{'ก่อน':<16}{'วินาที':>7}   {'หลัง':<16}{'วินาที':>7}  ต่าง")
    for r in res[:a.top]:
        print(f"{r['before']:<16}{r['before_s']:>7}   {r['after']:<16}{r['after_s']:>7}  {r['diff']}")
    (Path(a.work) / "match_before_after.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    rows = []
    for r in res[:min(a.top, 3)]:
        ims = []
        for c, t in ((r["before"], r["before_s"]), (r["after"], r["after_s"])):
            png = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(kf / f"{c}.mp4"), "-frames:v", "1",
                                  "-vf", "scale=270:480", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
            from io import BytesIO
            ims.append(Image.open(BytesIO(png)).convert("RGB"))
        row = Image.new("RGB", (540, 480))
        row.paste(ims[0], (0, 0)); row.paste(ims[1], (270, 0))
        rows.append(row)
    if rows:
        sheet = Image.new("RGB", (540 * len(rows) + 10 * (len(rows) - 1), 480), "white")
        for k, r in enumerate(rows):
            sheet.paste(r, (k * 550, 0))
        sheet.save(Path(a.work) / "match_before_after.jpg", quality=85)
        print(f"ภาพเทียบ: {Path(a.work) / 'match_before_after.jpg'}")


if __name__ == "__main__":
    main()
