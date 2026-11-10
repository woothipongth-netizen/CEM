"""เทมเพลตกลาง "มินิมอล หรูหรา": เรียบ นิ่ง พื้นที่ว่างเยอะ ใช้ได้ทุกร้าน

หน้าตา: ภาพโทนนุ่มลดสีลงเล็กน้อย + ขอบภาพมืดบางๆ, ตัวหนังสือบาง เว้นระยะตัวอักษรกว้าง,
เส้นบางสีแบรนด์เป็นเส้นนำสายตา, หัวข้อค้างด้านบนมีเลขช่วงเล็กๆ (I, II, III),
ซับไม่มีกล่อง มีเงาบางให้อ่านง่าย, ทรานสิชันช้าและนุ่ม, การ์ดจบเรียบไม่มีปุ่ม (ข้อความชวนมีเส้นใต้)
สีจาก brand.json (accent) ทั้งหมด ไม่มีสีอื่นเพิ่ม

ใช้:
  python3 -I scripts/cut_shots.py plan.json raw shots --head-pad 0.4 --curves check.json
  python3 -I templates/review-luxe/build.py content.json <โฟลเดอร์โปรเจกต์>
  cd <โฟลเดอร์โปรเจกต์> && npx hyperframes lint && npx hyperframes render -o out.mp4 --quiet

content.json (ดู content.example.json):
  duration, shots_dir, audio            เหมือน review-motion
  hook        {start, end, text}        ประโยคเปิด ด้านบนจอ ค่อยๆ ปรากฏทีละบรรทัด
  titles      [{start, end, text, pos?}] หัวข้อค้างด้านบน มีเลขช่วงให้เอง  pos: "low" = ย้ายลงใต้กลางจอ
  captions    [{start, end, text}]      ซับบรรทัดเดียว (*คำ* = สีแบรนด์)
  transitions {"<เลขช็อต>": "fade|dip|reveal|cut"}  ค่าเริ่ม: จุดเปลี่ยนหัวข้อ = dip, ที่เหลือสลับ fade / reveal
  end_card    {start, text?}            ชื่อร้าน + ข้อความสั้น + ข้อความชวนจาก brand.json
ไม่มีป้ายชื่อคนพูด (ตามกฎ repo)
"""
import html
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE.parent / "vendor"
BRAND = json.loads((HERE.parent.parent / "brand.json").read_text())
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def rich(text):
    """*คำ* = สีแบรนด์, | = ขึ้นบรรทัดใหม่"""
    out, on = [], False
    for part in html.escape(text).split("*"):
        out.append(f"<em>{part}</em>" if on else part)
        on = not on
    return "".join(out).replace("|", "<br />")


def split_words(text):
    """แยกหัวข้อเป็นคำตามช่องว่าง (ทั้งคำ ไม่แยกตัวอักษร ภาษาไทยไม่เพี้ยน), *คำ* = สีแบรนด์, | = ขึ้นบรรทัดใหม่"""
    out, on = [], False
    for part in text.split("*"):
        for li, line in enumerate(part.split("|")):
            if li:
                out.append("<br />")
            for w in line.split():
                w = html.escape(w)
                out.append(f'<span class="wd">{"<em>" + w + "</em>" if on else w}</span>')
        on = not on
    return " ".join(out).replace(" <br /> ", "<br />")


def main():
    content = json.loads(Path(sys.argv[1]).read_text())
    proj = Path(sys.argv[2])
    (proj / "fonts").mkdir(parents=True, exist_ok=True)
    (proj / "shots").mkdir(exist_ok=True)
    shutil.copy(VENDOR / "gsap.min.js", proj)
    for f in (VENDOR / "fonts").glob("*.woff2"):
        shutil.copy(f, proj / "fonts")
    shots_dir = Path(content["shots_dir"])
    shots = json.loads((shots_dir / "shots.json").read_text())
    for s in shots:
        shutil.copy(shots_dir / s["file"], proj / "shots" / s["file"])
    audio = Path(content["audio"])
    shutil.copy(audio, proj / audio.name)

    total = content["duration"]
    end = {"brand": BRAND["shop_name"], "cta": BRAND["cta"], **content["end_card"]}
    title_starts = {round(t["start"], 1) for t in content["titles"]}
    overrides = content.get("transitions", {})
    shot_els, els, js = [], [], []

    # ---- ช็อต: ซูมช้ามาก + ทรานสิชันนุ่ม ----
    alt = ["fade", "reveal"]
    for i, s in enumerate(shots):
        at, dur, pad = s["at"], s["dur"], s["head_pad"]
        if i == 0:
            v_start, v_dur, media = 0, dur, f' data-media-start="{pad}"'
        else:
            v_start, v_dur, media = round(at - pad, 3), round(dur + pad, 3), ""
        shot_els.append(
            f'<div id="sh{i}" class="shot"><video id="v{i}" class="clip" src="shots/{s["file"]}" muted playsinline '
            f'data-start="{v_start}" data-duration="{v_dur}"{media} data-track-index="0"></video></div>')
        js.append(f'tl.fromTo("#v{i}", {{scale: 1.02}}, {{scale: 1.06, duration: {v_dur}, ease: "none"}}, {v_start});')
        if i == 0:
            continue
        kind = overrides.get(str(i)) or ("dip" if round(at, 1) in title_starts else alt[i % 2])
        p = pad  # ใช้ช่วงเผื่อหัวเต็มที่ ให้ทรานสิชันช้า
        if kind == "fade":
            js.append(f'tl.fromTo("#sh{i}", {{opacity: 0}}, {{opacity: 1, duration: {p}, ease: "sine.inOut"}}, {at - p});')
        elif kind == "reveal":
            js.append(f'tl.fromTo("#sh{i}", {{clipPath: "inset(0% 0% 100% 0%)"}}, '
                      f'{{clipPath: "inset(0% 0% 0% 0%)", duration: {p}, ease: "power2.inOut"}}, {at - p});')
        elif kind == "dip":
            js.append(f'tl.set("#sh{i}", {{opacity: 0}}, {at - p}); tl.set("#sh{i}", {{opacity: 1}}, {at});')
            js.append(f'tl.fromTo("#dip", {{opacity: 0}}, {{opacity: 1, duration: {p}, ease: "sine.in", immediateRender: false}}, {at - p});')
            js.append(f'tl.to("#dip", {{opacity: 0, duration: 0.5, ease: "sine.out"}}, {at});')
        # cut = ตัดตรง
        js.append(f'tl.set("#sh{i}", {{clipPath: "none"}}, {at + 0.01});')

    # ---- ประโยคเปิด: ค่อยๆ ปรากฏทีละบรรทัด + เส้นบางลากออกจากกลาง ----
    hook = content.get("hook")
    if hook:
        a, b = hook["start"], hook["end"]
        lines = "".join(f'<div class="hk-line">{rich(l)}</div>' for l in hook["text"].split("|"))
        els.append(f'<div id="hook" class="hook clip" data-start="{a}" data-duration="{b - a:.2f}" data-track-index="6">'
                   f'<div class="hair"></div>{lines}</div>')
        js.append(f'tl.fromTo("#hook .hair", {{scaleX: 0}}, {{scaleX: 1, duration: 0.9, ease: "power3.inOut"}}, {a});')
        js.append(f'tl.fromTo("#hook .hk-line", {{opacity: 0, y: 18, filter: "blur(8px)"}}, '
                  f'{{opacity: 1, y: 0, filter: "blur(0px)", duration: 1.0, ease: "power2.out", stagger: 0.3}}, {a + 0.2});')
        js.append(f'tl.to("#hook", {{opacity: 0, duration: 0.4, ease: "sine.in"}}, {b - 0.4});')

    # ---- หัวข้อ: เลขช่วง + เส้นบาง + ข้อความ ค้างด้านบน ----
    for i, t in enumerate(content["titles"]):
        a, b = t["start"], t["end"]
        low = " low" if t.get("pos") == "low" else ""
        num = ROMAN[i] if i < len(ROMAN) else str(i + 1)
        els.append(f'<div id="t{i}" class="title clip{low}" data-start="{a}" data-duration="{b - a:.2f}" data-track-index="3">'
                   f'<div class="num">{num}</div><div class="hair"></div><div class="tt">{split_words(t["text"])}</div></div>')
        js.append(f'tl.fromTo("#t{i} .num", {{opacity: 0}}, {{opacity: 1, duration: 0.6, ease: "sine.out"}}, {a + 0.1});')
        js.append(f'tl.fromTo("#t{i} .hair", {{scaleX: 0}}, {{scaleX: 1, duration: 0.8, ease: "power3.inOut"}}, {a + 0.15});')
        # text stagger: ทยอยเข้าทีละคำ (ชัดจากเบลอ + ลอยขึ้น) แล้วแสงวิ่งผ่านคำเน้นหนึ่งครั้ง
        js.append(f'tl.fromTo("#t{i} .wd", {{opacity: 0, y: 16, filter: "blur(8px)"}}, '
                  f'{{opacity: 1, y: 0, filter: "blur(0px)", duration: 0.7, ease: "power2.out", stagger: 0.12}}, {a + 0.35});')
        if "*" in t["text"]:
            js.append(f'tl.fromTo("#t{i} em", {{backgroundPosition: "130% 0"}}, {{backgroundPosition: "-30% 0", duration: 1.2, ease: "power2.inOut"}}, {a + 1.1});')
        js.append(f'tl.to("#t{i} .wd", {{opacity: 0, y: -10, filter: "blur(6px)", duration: 0.3, ease: "sine.in", stagger: 0.05}}, {b - 0.45});')
        js.append(f'tl.to("#t{i} .num, #t{i} .hair", {{opacity: 0, duration: 0.3, ease: "sine.in"}}, {b - 0.35});')

    # ---- ซับ: ไม่มีกล่อง ค่อยๆ ปรากฏ ----
    for i, c in enumerate(content["captions"]):
        a, b = c["start"], c["end"]
        els.append(f'<div id="c{i}" class="line clip" data-start="{a}" data-duration="{b - a:.2f}" '
                   f'data-track-index="{7 + i % 2}"><span>{rich(c["text"])}</span></div>')
        js.append(f'tl.fromTo("#c{i} span", {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: 0.3, ease: "sine.out"}}, {a});')
        js.append(f'tl.to("#c{i} span", {{opacity: 0, duration: 0.15}}, {b - 0.15});')

    # ---- การ์ดจบ: ภาพหรี่ลง ชื่อร้านเว้นระยะกว้าง ----
    ea = end["start"]
    sub = f'<div class="end-sub">{html.escape(end["text"])}</div>' if end.get("text") else ""
    els.append(f'<div id="endshade" class="clip" data-start="{ea}" data-duration="{total - ea:.2f}" data-track-index="9"></div>')
    els.append(f'<div id="endcard" class="end clip" data-start="{ea}" data-duration="{total - ea:.2f}" data-track-index="10">'
               f'<div class="end-name">{html.escape(end["brand"])}</div><div class="hair"></div>{sub}'
               f'<div class="end-cta">{html.escape(end["cta"])}</div></div>')
    js.append(f'tl.fromTo("#endshade", {{opacity: 0}}, {{opacity: 1, duration: 1.0, ease: "sine.inOut"}}, {ea});')
    js.append(f'tl.fromTo("#endcard .end-name", {{opacity: 0, scale: 1.08, filter: "blur(10px)"}}, '
              f'{{opacity: 1, scale: 1, filter: "blur(0px)", duration: 1.4, ease: "power2.out"}}, {ea + 0.3});')
    js.append(f'tl.fromTo("#endcard .hair", {{scaleX: 0}}, {{scaleX: 1, duration: 0.9, ease: "power3.inOut"}}, {ea + 0.8});')
    if sub:
        js.append(f'tl.fromTo("#endcard .end-sub", {{opacity: 0}}, {{opacity: 1, duration: 0.8, ease: "sine.out"}}, {ea + 1.2});')
    js.append(f'tl.fromTo("#endcard .end-cta", {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: 0.8, ease: "sine.out"}}, {ea + 1.5});')

    page = (HERE / "index.template.html").read_text()
    page = (page.replace("{{TOTAL}}", str(total))
                .replace("{{AUDIO}}", audio.name)
                .replace("{{ACCENT}}", BRAND["colors"]["accent"])
                .replace("{{ACCENT_LIGHT}}", BRAND["colors"]["accent_light"])
                .replace("{{SHOTS}}", "\n      ".join(shot_els))
                .replace("{{ELEMENTS}}", "\n      ".join(els))
                .replace("{{JS}}", "\n      ".join(js)))
    (proj / "index.html").write_text(page)
    print(f"สร้างแล้ว: {proj / 'index.html'} ({len(shots)} ช็อต, {len(content['titles'])} หัวข้อ, {len(content['captions'])} ซับ)")


if __name__ == "__main__":
    main()
