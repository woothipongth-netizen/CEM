"""ตัดซับให้สั้น: บรรทัดเดียว ไม่เกิน N ตัวอักษรต่อท่อน (ซับยาว 2 บรรทัดดูรกจอ)

ใช้: python3 -I scripts/split_captions.py <content.json> [--max 20]
  แก้ "captions" ใน content.json ตรงๆ: ท่อนที่ยาวเกินหรือมี | จะถูกแบ่งเป็นหลายท่อนตามช่องว่าง/|
  เวลาแต่ละท่อนแบ่งตามสัดส่วนจำนวนตัวอักษร (เสียงพูดสม่ำเสมอพอ)
  --max  ความยาวสูงสุดต่อท่อน (ไม่นับ * ที่ใช้เน้นคำ) ค่าเริ่มต้นตามโปรไฟล์: สั้น 1 บรรทัด = 20, สั้นมาก = 12
ท่อนที่ยาวเกินแต่ไม่มีช่องว่างให้ตัด จะพิมพ์เตือน ให้ใส่ช่องว่างตรงจุดที่หยุดหายใจแล้วรันใหม่
นับตัวอักษรแบบไม่นับสระบน-ล่างและวรรณยุกต์ (ใกล้เคียงความกว้างที่เห็นบนจอ)
"""
import argparse
import json
import unicodedata
from pathlib import Path


def width(s):
    return sum(1 for ch in s.replace("*", "") if unicodedata.category(ch) != "Mn")


def chunks(text, mx):
    words = [w for w in text.replace("|", " ").split(" ") if w]
    out, cur = [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if cur and width(cand) > mx:
            out.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        out.append(cur)
    # คำเน้น *...* ที่ถูกตัดกลาง ต้องปิด/เปิดใหม่ในแต่ละท่อน
    fixed, open_ = [], False
    for c in out:
        c2 = ("*" if open_ else "") + c
        open_ = c2.count("*") % 2 == 1
        fixed.append(c2 + ("*" if open_ else ""))
    return fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("content")
    ap.add_argument("--max", type=int, default=20)
    a = ap.parse_args()
    p = Path(a.content)
    c = json.loads(p.read_text())
    new = []
    for cap in c["captions"]:
        t = cap["text"]
        if "|" not in t and width(t) <= a.max:
            new.append(cap)
            continue
        parts = chunks(t, a.max)
        total = sum(width(x) for x in parts) or 1
        s, d = cap["start"], cap["end"] - cap["start"]
        for x in parts:
            e = s + d * width(x) / total
            new.append({**cap, "start": round(s, 2), "end": round(e, 2), "text": x})
            s = e
        for x in parts:
            if width(x) > a.max:
                print(f"ยาวเกินแต่ตัดไม่ได้ (ไม่มีช่องว่าง): {x}")
    c["captions"] = new
    p.write_text(json.dumps(c, ensure_ascii=False, indent=1))
    print(f"ซับ {len(new)} ท่อน (ไม่เกิน {a.max} ตัวอักษร บรรทัดเดียว)")


if __name__ == "__main__":
    main()
