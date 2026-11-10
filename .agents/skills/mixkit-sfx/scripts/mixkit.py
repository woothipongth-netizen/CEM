#!/usr/bin/env python3
"""ค้นหาและดาวน์โหลดเสียงเอฟเฟกต์จาก Mixkit (mixkit.co) เท่านั้น ใช้ Python มาตรฐาน ไม่ต้องใช้คีย์

  mixkit.py search <คำค้นภาษาอังกฤษ 1 คำ> [-n 10]    แสดง: รหัส  ชื่อ  ความยาว  ลิงก์ฟังตัวอย่าง
  mixkit.py get <โฟลเดอร์> <รหัส>[=ชื่อไฟล์.mp3] ...  ดาวน์โหลด (wav) ถ้าใส่ =ชื่อ.mp3 จะแปลงเป็น mp3 ชื่อนั้น
  mixkit.py music <อารมณ์หรือแนว> [-n 10]          ค้นเพลงพื้นหลัง เช่น happy calm elegant energetic upbeat chillout
  mixkit.py getmusic <โฟลเดอร์> <รหัส>[=ชื่อ.mp3] ...  ดาวน์โหลดเพลง (mp3)

ตัวอย่าง: mixkit.py get work/sfx 1492=whoosh-short.mp3 871=sparkle.mp3
ดัดแปลงจากส่วน Mixkit ของ github.com/sxhzju/sfx (MIT) ตัดแหล่งอื่นออกทั้งหมด
"""
import argparse, html, re, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 mixkit-sfx"}


def fetch(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def search(a):
    kw = re.sub(r"\s+", "-", a.keyword.strip().lower())
    h = fetch(f"https://mixkit.co/free-sound-effects/discover/{urllib.parse.quote(kw)}/").decode()
    rows = 0
    for blk in h.split('data-audio-player-item-id-value="')[1:]:
        i = blk.split('"', 1)[0]
        t = re.search(r'item-grid-card__title">\s*(.*?)\s*</h2>', blk, re.S)
        d = re.search(r'data-test-id="duration">\s*([\d:]+)', blk)
        print("\t".join([i, html.unescape(t.group(1)) if t else "", d.group(1) if d else "",
                         f"https://assets.mixkit.co/active_storage/sfx/{i}/{i}-preview.mp3"]))
        rows += 1
        if rows >= a.n:
            break
    if not rows:
        print("(ไม่เจอ ลองคำอื่นที่กว้างขึ้น เช่น whoosh, pop, click, ding)")


def get(a):
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ok = True
    for item in a.ids:
        sid, _, name = item.partition("=")
        if not sid.isdigit():
            print(f"FAIL {item}: รหัสต้องเป็นตัวเลข"); ok = False; continue
        try:
            data = fetch(f"https://assets.mixkit.co/active_storage/sfx/{sid}/{sid}.wav", timeout=300)
        except Exception as e:
            print(f"FAIL {sid}: {e}"); ok = False; continue
        wav = out / f"mixkit_{sid}.wav"
        wav.write_bytes(data)
        if name:
            dst = out / name
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), str(dst)], check=True)
            wav.unlink()
            print(dst)
        else:
            print(wav)
    sys.exit(0 if ok else 1)


def music(a):
    kw = re.sub(r"\s+", "-", a.keyword.strip().lower())
    h = ""
    for path in (f"mood/{kw}", kw, f"tag/{kw}"):  # อารมณ์ (mood) → แนวเพลง → แท็ก
        try:
            h = fetch(f"https://mixkit.co/free-stock-music/{urllib.parse.quote(path)}/").decode()
        except Exception:
            continue
        if 'data-audio-player-item-id-value="' in h:
            break
    rows = 0
    for blk in h.split('data-audio-player-item-id-value="')[1:]:
        i = blk.split('"', 1)[0]
        t = re.search(r'item-grid-card__title">\s*(.*?)\s*</h2>', blk, re.S)
        d = re.search(r'data-test-id="duration">\s*([\d:]+)', blk)
        tags = [html.unescape(x) for x in re.findall(r'class="meta-links__link"[^>]*>([^<]+)</a>', blk)][:4]
        print("\t".join([i, html.unescape(t.group(1)) if t else "", d.group(1) if d else "", ", ".join(tags),
                         f"https://assets.mixkit.co/music/{i}/{i}.mp3"]))
        rows += 1
        if rows >= a.n:
            break
    if not rows:
        print("(ไม่เจอ ลองอารมณ์อื่น เช่น happy calm elegant energetic upbeat dreamy)")


def getmusic(a):
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ok = True
    for item in a.ids:
        sid, _, name = item.partition("=")
        if not sid.isdigit():
            print(f"FAIL {item}: รหัสต้องเป็นตัวเลข"); ok = False; continue
        try:
            data = fetch(f"https://assets.mixkit.co/music/{sid}/{sid}.mp3", timeout=300)
        except Exception as e:
            print(f"FAIL {sid}: {e}"); ok = False; continue
        dst = out / (name or f"mixkit_music_{sid}.mp3")
        dst.write_bytes(data)
        print(dst)
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("search"); s.add_argument("keyword"); s.add_argument("-n", type=int, default=10); s.set_defaults(fn=search)
    m = sp.add_parser("music"); m.add_argument("keyword"); m.add_argument("-n", type=int, default=10); m.set_defaults(fn=music)
    gm = sp.add_parser("getmusic"); gm.add_argument("out_dir"); gm.add_argument("ids", nargs="+"); gm.set_defaults(fn=getmusic)
    g = sp.add_parser("get"); g.add_argument("out_dir"); g.add_argument("ids", nargs="+"); g.set_defaults(fn=get)
    a = ap.parse_args()
    try:
        a.fn(a)
    except OSError as e:
        sys.exit(f"เชื่อมต่อ Mixkit ไม่ได้: {getattr(e, 'reason', e)} (เช็กว่า environment อนุญาต mixkit.co และ assets.mixkit.co)")


if __name__ == "__main__":
    main()
