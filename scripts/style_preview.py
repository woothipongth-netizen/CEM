"""ทำภาพตัวอย่างเทียบตัวเลือกสไตล์ ให้เจ้าของงานเลือกด้วยตา (docs/09-template-design.md)

ใช้: python3 -I scripts/style_preview.py <หัวข้อ> <โฟลเดอร์ผลลัพธ์> [--bg รูป1.jpg,รูป2.jpg]

หัวข้อ: title_style | title_position | caption_style | caption_position | end_card   → ภาพนิ่งเทียบกัน (.png)
        transitions | camera_motion                                               → วิดีโอเทียบกัน (.mp4)
--bg: รูปพื้นหลัง (เช่นเฟรมจากฟุตเทจของร้าน kf/*.mp4) ถ้าไม่ใส่ใช้พื้นไล่สีสมมติ (ไม่มีภาพลูกค้า)

ใช้ style.json ปัจจุบันเป็นฐาน แล้วเปลี่ยนเฉพาะหัวข้อที่เลือก ภาพละ ~20–40 วินาที วิดีโอละ ~1 นาที
ข้อความตัวอย่างใช้ชื่อร้านและสีจาก brand.json
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = {
    "title_style": ["shine", "boxed", "minimal"],
    "title_position": ["top", "upper"],
    "caption_style": ["rail", "outline", "light"],
    "caption_position": ["bottom", "low"],
    "end_card": ["brand", "cta", "none"],
    "transitions": ["soft", "mixed", "punchy", "cut"],
    "camera_motion": ["slow-zoom", "subtle", "none"],
}
LABELS = {
    "shine": "ทองมีแสงวิ่ง", "boxed": "กล่องสีแบรนด์", "minimal": "ขาวเรียบ",
    "top": "บนสุด", "upper": "ลงมาอีกนิด", "rail": "กล่องเข้มขอบสี", "outline": "ตัวหนาขอบดำ",
    "light": "กล่องขาว", "bottom": "ล่าง", "low": "สูงขึ้น", "brand": "ชื่อร้าน + ปุ่ม", "cta": "ปุ่มอย่างเดียว",
    "none": "ไม่มี", "soft": "นุ่มนวล", "mixed": "ผสม", "punchy": "เร้าใจ", "cut": "ตัดตรง",
    "slow-zoom": "ซูมช้า", "subtle": "ซูมน้อย",
}
VIDEO_KEYS = {"transitions", "camera_motion"}
DUR = 7.0


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def make_shots(work, bgs):
    """ช็อตตัวอย่าง 2 ช็อตจากรูป (หรือพื้นไล่สี) พร้อมเผื่อหัวช็อตให้ทรานสิชันทำงาน"""
    shots = work / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    plan = [(0.0, 3.5), (3.5, 3.5)]
    rows = []
    for i, (at, dur) in enumerate(plan):
        pad = 0.4
        out = shots / f"s{i}.mp4"
        src = bgs[i % len(bgs)] if bgs else None
        if src:
            inp = ["-loop", "1", "-i", str(src)]
            vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p"
        else:
            # สองช็อตต่างกันชัดเจน (เข้ม/สว่าง + เลขช็อตใหญ่) ให้เห็นทรานสิชันตอนเปลี่ยนช็อต
            c0, c1 = [("0x2a1d14", "0x8a6a4a"), ("0x6f8fa8", "0xe8dcc8")][i % 2]
            inp = ["-f", "lavfi", "-i", f"gradients=s=1080x1920:c0={c0}:c1={c1}:x0=0:y0=0:x1=1080:y1=1920:d=8"]
            vf = (f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{i + 1}':"
                  "fontsize=520:fontcolor=white@0.35:x=(w-text_w)/2:y=(h-text_h)/2,format=yuv420p")
        run(["ffmpeg", "-v", "error", "-y", *inp, "-t", f"{dur + pad}", "-r", "30", "-vf", vf, "-c:v", "libx264", str(out)])
        rows.append({"i": i, "file": out.name, "at": at, "dur": dur, "head_pad": pad})
    (shots / "shots.json").write_text(json.dumps(rows))
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(DUR), str(work / "silence.wav")])
    return shots


def content(work, shots):
    return {
        "duration": DUR, "shots_dir": str(shots), "audio": str(work / "silence.wav"),
        "titles": [{"start": 0.0, "end": 5.0, "text": "หัวข้อ*ตัวอย่าง*|ของคลิป"}],
        "captions": [{"start": 0.0, "end": 5.0, "text": "ซับตัวอย่าง คำสำคัญเป็น*สีแบรนด์*"}],
        "lower_thirds": [{"start": 0.3, "end": 5.0}],
        "end_card": {"start": 5.0},
    }


def build(work, key, value, base_style, shots, render):
    style = json.loads(json.dumps(base_style))
    style[key] = value
    sp = work / f"style-{value}.json"
    sp.write_text(json.dumps(style, ensure_ascii=False))
    cp = work / f"content-{value}.json"
    cp.write_text(json.dumps(content(work, shots), ensure_ascii=False))
    proj = work / f"comp-{value}"
    env = {**os.environ, "STYLE_JSON": str(sp)}
    run(["python3", "-I", str(ROOT / "templates/review-motion/build.py"), str(cp), str(proj)], env=env, stdout=subprocess.DEVNULL)
    if render:
        out = work / f"{value}.mp4"
        run(["npx", "hyperframes", "render", "-o", str(out), "--quiet"], cwd=proj,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out
    at = "6.2" if key == "end_card" else "2.5"
    snap = work / f"snap-{value}"
    run(["npx", "hyperframes", "snapshot", "--at", at, "--no-end", "-o", str(snap)], cwd=proj,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return next(snap.glob("frame-*.png"))


def thai_font(size):
    path = subprocess.run(["fc-match", "-f", "%{file}", ":lang=th:weight=bold"], capture_output=True, text=True).stdout
    return ImageFont.truetype(path, size)


def label(i, value):
    return f"{i + 1}. {LABELS.get(value, value)}"


def main():
    key, out_dir = sys.argv[1], Path(sys.argv[2]).resolve()
    if key not in OPTIONS:
        sys.exit(f"หัวข้อที่ทำได้: {', '.join(OPTIONS)}")
    bgs = []
    if "--bg" in sys.argv:
        bgs = [Path(p).resolve() for p in sys.argv[sys.argv.index("--bg") + 1].split(",")]
    work = out_dir / f"_work_{key}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    sp = ROOT / "style.json"
    base = json.loads(sp.read_text()) if sp.exists() else {}
    shots = make_shots(work, bgs)
    render = key in VIDEO_KEYS
    results = [build(work, key, v, base, shots, render) for v in OPTIONS[key]]

    if render:
        # วิดีโอเทียบกันซ้าย-ขวา ย่อแต่ละช่องเป็น 360x640 พร้อมป้ายชื่อ
        font = thai_font(34)
        inputs, filters = [], []
        for i, (v, f) in enumerate(zip(OPTIONS[key], results)):
            tag = work / f"tag{i}.png"
            img = Image.new("RGBA", (360, 56), (0, 0, 0, 200))
            ImageDraw.Draw(img).text((12, 8), label(i, v), font=font, fill="white")
            img.save(tag)
            inputs += ["-i", str(f), "-i", str(tag)]
            filters.append(f"[{2 * i}:v]scale=360:640[v{i}];[v{i}][{2 * i + 1}:v]overlay=0:0[l{i}]")
        n = len(results)
        graph = ";".join(filters) + ";" + "".join(f"[l{i}]" for i in range(n)) + f"hstack=inputs={n}[o]"
        out = out_dir / f"preview_{key}.mp4"
        run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[o]", "-c:v", "libx264",
             "-pix_fmt", "yuv420p", str(out)])
    else:
        font = thai_font(40)
        w, h = 432, 768
        sheet = Image.new("RGB", (w * len(results), h + 70), "#111")
        d = ImageDraw.Draw(sheet)
        for i, (v, f) in enumerate(zip(OPTIONS[key], results)):
            img = Image.open(f).convert("RGB").resize((w, h))
            sheet.paste(img, (i * w, 70))
            d.text((i * w + 14, 12), label(i, v), font=font, fill="white")
        out = out_dir / f"preview_{key}.png"
        sheet.save(out)
    if "--keep" not in sys.argv:
        shutil.rmtree(work, ignore_errors=True)
    print(f"ตัวอย่าง: {out}")


if __name__ == "__main__":
    main()
