"""ภาพรวมฟุตเทจทุกคลิป ติด "ชื่อไฟล์" บนทุกช่อง (ไม่ใช่เลขอันดับ) เพื่อจดชื่อคลิปลงแผนได้ไม่ผิด

ใช้: python3 -I scripts/contact_sheet.py <โฟลเดอร์งาน>
ต้องรันหลัง fetch_footage.sh เสร็จ อ่านจาก <งาน>/kf/*.mp4
ผลลัพธ์: <งาน>/sheets/sheet_00.png ... (แผ่นละ 20 ช่อง) + <งาน>/sheets/kf.json (ค่าความคมของทุกคลิป)

แต่ละช่องแสดงภาพที่คมที่สุดของคลิป + ชื่อ + ความยาว + ป้าย "นุ่ม" ถ้าเบลอกว่าคลิปส่วนใหญ่ในชุด
(เทียบภายในชุดเดียวกัน เพราะแต่ละชุดฟุตเทจคมไม่เท่ากัน ห้ามใช้ตัวเลขตายตัว)
ป้ายกล้องสั่นไม่มีในภาพนี้ เพราะเฟรมหลักวัดการสั่นไม่ได้ ให้ใช้ check_shots.py
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agents/skills/video-understand/scripts"))
import index as ix  # noqa: E402

CELL_W, CELL_H, COLS, PER = 300, 534, 5, 20
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def measure(video, tmp):
    meta = ix.probe(str(video))
    _, stats, _, _ = ix.run_passes(str(video), None, None, False, tmp)
    rows = [r for r in stats if "blur" in r and "signalstats.YAVG" in r]
    lit = [r for r in rows if 25 <= r["signalstats.YAVG"] <= 235] or rows
    best = min(lit, key=lambda r: r["blur"]) if lit else {"t": meta["duration_s"] / 2, "blur": 99}
    return {"clip": video.stem, "len": round(meta["duration_s"], 1),
            "blur": round(sum(r["blur"] for r in lit) / max(1, len(lit)), 3), "sharpest_s": best["t"]}


def main():
    w = Path(sys.argv[1])
    out = w / "sheets"
    out.mkdir(exist_ok=True)
    vids = sorted((w / "kf").glob("*.mp4"))
    res = []
    for v in vids:
        tmp = out / "tmp" / v.stem
        tmp.mkdir(parents=True, exist_ok=True)
        res.append(measure(v, tmp))
    blurs = sorted(r["blur"] for r in res)
    soft_at = blurs[int(len(blurs) * 0.8)] if blurs else 99
    for r in res:
        r["soft"] = r["blur"] > soft_at
    (out / "kf.json").write_text(json.dumps({"soft_threshold": soft_at, "clips": res}, ensure_ascii=False, indent=1))
    font = ImageFont.truetype(FONT, 26)
    for s in range(0, len(res), PER):
        chunk = res[s:s + PER]
        rows = (len(chunk) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * CELL_W, rows * CELL_H), "black")
        for i, r in enumerate(chunk):
            frame = out / "tmp" / r["clip"] / "cell.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{r['sharpest_s']:.2f}", "-i", str(w / "kf" / f"{r['clip']}.mp4"),
                            "-frames:v", "1", "-vf", f"scale={CELL_W}:{CELL_H}:force_original_aspect_ratio=decrease", str(frame)], check=True)
            img = Image.open(frame)
            x, y = (i % COLS) * CELL_W, (i // COLS) * CELL_H
            sheet.paste(img, (x + (CELL_W - img.width) // 2, y))
            d = ImageDraw.Draw(sheet)
            label = f"{r['clip']} {r['len']:.0f}s" + (" SOFT" if r["soft"] else "")
            d.rectangle([x, y, x + CELL_W - 1, y + 36], fill="black")
            d.text((x + 6, y + 4), label, font=font, fill="#ffcc66" if r["soft"] else "white")
        sheet.save(out / f"sheet_{s // PER:02d}.png")
    print(f"ภาพรวม {len(res)} คลิป → {out}/sheet_*.png (ป้าย SOFT = เบลอกว่า 80% ของชุด, เกณฑ์ {soft_at})")


if __name__ == "__main__":
    main()
