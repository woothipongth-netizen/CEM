"""สตอรีบอร์ดของแผนช็อต: ภาพเดียวเห็นทุกช็อต มีเลขช็อต เวลา และโน้ต ส่งให้เจ้าของงานดูพร้อมแผน
เจ้าของงานสั่งแก้ได้ด้วยเลข เช่น "เปลี่ยนช็อต 7" "สลับ 3 กับ 4"

ใช้: python3 -I scripts/plan_sheet.py <โฟลเดอร์งาน>
อ่าน <งาน>/plan.json และภาพจาก <งาน>/kf/ (เฟรมหลัก) ถ้ามี <งาน>/sheets/kf.json จะใช้ภาพที่คมที่สุดของคลิป
ผลลัพธ์: <งาน>/plan_sheet.png

เลขช็อตเริ่มที่ 1 ตามลำดับใน plan.json (ภายในสคริปต์อื่นยังนับจาก 0: ช็อต N = plan[N-1])
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CELL_W, CELL_H, COLS, BAR = 270, 480, 4, 92
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def thai_font(size):
    """ฟอนต์ไทยของเครื่อง (โน้ตในแผนเป็นภาษาไทย) PIL อ่าน .woff2 ของเทมเพลตไม่ได้ จึงใช้ fc-match"""
    path = subprocess.run(["fc-match", "-f", "%{file}", ":lang=th:weight=bold"], capture_output=True, text=True).stdout
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.truetype(BOLD, size)


MARKS = set(chr(c) for c in [0x0E31, *range(0x0E34, 0x0E3B), *range(0x0E47, 0x0E4F)])


def wrap(text, font, width, lines=2):
    """ตัดบรรทัดตามความกว้างจริง เลือกตัดที่ช่องว่างก่อน และไม่ให้วรรณยุกต์/สระบนล่างหลุดไปต้นบรรทัด"""
    out = []
    while text and len(out) < lines:
        if font.getlength(text) <= width:
            out.append(text)
            break
        cut = len(text)
        while cut > 1 and font.getlength(text[:cut]) > width:
            cut -= 1
        sp = text.rfind(" ", 0, cut)
        if sp > cut // 2:
            cut = sp + 1
        while cut < len(text) and text[cut] in MARKS:
            cut -= 1
        out.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    return out


def main():
    w = Path(sys.argv[1])
    plan = json.loads((w / "plan.json").read_text())
    kfj = w / "sheets" / "kf.json"
    sharp = {c["clip"]: c["sharpest_s"] for c in json.loads(kfj.read_text())["clips"]} if kfj.exists() else {}
    rows = (len(plan) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * CELL_W, rows * (CELL_H + BAR)), "#111")
    d = ImageDraw.Draw(sheet)
    big, small = ImageFont.truetype(BOLD, 40), ImageFont.truetype(BOLD, 20)
    note_f = thai_font(22)
    tmp = w / "plan_sheet_tmp"
    tmp.mkdir(exist_ok=True)
    t = 0.0
    for i, s in enumerate(plan):
        stem = Path(s["clip"]).stem
        src = w / "kf" / f"{stem}.mp4"
        at = s.get("start", sharp.get(stem, 3.0))
        frame = tmp / f"{i}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", str(src), "-frames:v", "1",
                        "-vf", f"scale={CELL_W}:{CELL_H}:force_original_aspect_ratio=decrease", str(frame)], check=True)
        x, y = (i % COLS) * CELL_W, (i // COLS) * (CELL_H + BAR)
        img = Image.open(frame)
        sheet.paste(img, (x + (CELL_W - img.width) // 2, y))
        d.rounded_rectangle([x + 8, y + 8, x + 78, y + 58], 10, fill="#e8c879")
        d.text((x + 43, y + 33), str(i + 1), font=big, fill="#1c1813", anchor="mm")
        d.text((x + 8, y + CELL_H + 6), f"{t:.1f}-{t + s['dur']:.1f}s  {stem}", font=small, fill="white")
        for k, line in enumerate(wrap(s.get("note", ""), note_f, CELL_W - 16)):
            d.text((x + 8, y + CELL_H + 34 + k * 26), line, font=note_f, fill="#e8c879")
        t += s["dur"]
    sheet.save(w / "plan_sheet.png")
    print(f"สตอรีบอร์ด {len(plan)} ช็อต → {w / 'plan_sheet.png'}")


if __name__ == "__main__":
    main()
