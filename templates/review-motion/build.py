"""เทมเพลตคลิปแบบมีโมชั่น: ทรานสิชันระหว่างช็อต, Ken Burns, light leak, film grain,
หัวข้อทองมีแสงวิ่ง, ป้ายชื่อแบบ lower third, ซับแบบ rail, การ์ดปิดท้าย

ใช้:
  python3 -I scripts/cut_shots.py plan.json raw shots --head-pad 0.4
  python3 -I templates/review-motion/build.py content.json <โฟลเดอร์โปรเจกต์>
  cd <โฟลเดอร์โปรเจกต์> && npx hyperframes lint && npx hyperframes render -o out.mp4 --quiet

content.json ใช้รูปแบบเดียวกับ review-captions เพิ่ม:
  "shots_dir":      โฟลเดอร์ที่ cut_shots.py สร้าง (ต้องตัดด้วย --head-pad)
  "audio":          เสียงที่มิกซ์แล้ว (เสียงพากย์ + เพลง + SFX) จาก scripts/mix_audio.sh
  "lower_thirds":   [{"start", "end", "kicker", "name"}]  ป้ายชื่อ (ไม่ใส่ kicker/name จะใช้ staff_role/staff_name จาก brand.json)
  "transitions":    {"<เลขช็อต>": "blur|slide|zoom|leak|flash|cut"} กำหนดเองเฉพาะจุด
ถ้าไม่กำหนด: จุดเปลี่ยนหัวข้อใช้ leak, ช็อตอื่นสลับ blur / slide

ที่มาของเอฟเฟกต์ (hyperframes-registry): transitions-blur, transitions-scale, transitions-light,
grain-overlay, lt-kicker-name, text-shimmer ปรับสีและชื่อตาม brand.json ที่ราก repo
สไตล์ซับยืมจาก identity "anchor" ของ embedded-captions (rail อ่านง่าย คำสำคัญเด้งสีทอง)
"""
import html
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE.parent / "vendor"
BRAND = json.loads((HERE.parent.parent / "brand.json").read_text())
GRAIN = ("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E"
         "%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E"
         "%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")


def rich(text):
    """*คำ* = สีทอง, | = ขึ้นบรรทัดใหม่"""
    out, gold = [], False
    for part in html.escape(text).split("*"):
        out.append(f"<em>{part}</em>" if gold else part)
        gold = not gold
    return "".join(out).replace("|", "<br />")


# สระบน/ล่างและวรรณยุกต์ไทยไม่กินความกว้าง นับเฉพาะตัวที่กินที่
THAI_MARKS = set(chr(c) for c in [0x0E31, *range(0x0E34, 0x0E3B), *range(0x0E47, 0x0E4F)])


def brand_size(text, width=940, max_px=150):
    """ย่อชื่อร้านที่การ์ดจบให้พอดีจอ 1080 (ชื่อยาวเช่น 17 ตัวอักษรไทยเคยล้นจอที่ 150px)"""
    n = sum(1 for ch in text if ch not in THAI_MARKS)
    return min(max_px, int(width / (max(1, n) * 0.62)))


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

    # ---- ช็อต: วิดีโอแต่ละช็อตอยู่ใน wrapper ที่ใช้ทำทรานสิชัน, ตัววิดีโอทำ Ken Burns ----
    alt = ["blur", "slide"]
    for i, s in enumerate(shots):
        at, dur, pad = s["at"], s["dur"], s["head_pad"]
        if i == 0:
            v_start, v_dur, media = 0, dur, f' data-media-start="{pad}"'
        else:
            v_start, v_dur, media = round(at - pad, 3), round(dur + pad, 3), ""
        shot_els.append(
            f'<div id="sh{i}" class="shot"><video id="v{i}" class="clip" src="shots/{s["file"]}" muted playsinline '
            f'data-start="{v_start}" data-duration="{v_dur}"{media} data-track-index="0"></video></div>')
        zoom_in = i % 2 == 0
        js.append(f'tl.fromTo("#v{i}", {{scale: {1.0 if zoom_in else 1.08}}}, '
                  f'{{scale: {1.08 if zoom_in else 1.0}, duration: {v_dur}, ease: "none"}}, {v_start});')
        if i == 0:
            continue
        kind = overrides.get(str(i)) or ("leak" if round(at, 1) in title_starts else alt[i % 2])
        p = min(pad, 0.4)
        if kind == "blur":
            js.append(f'tl.fromTo("#sh{i}", {{opacity: 0, filter: "blur(18px)"}}, '
                      f'{{opacity: 1, filter: "blur(0px)", duration: {p}, ease: "power2.out"}}, {at - p});')
            js.append(f'tl.to("#sh{i-1}", {{filter: "blur(18px)", duration: {p}, ease: "power2.in"}}, {at - p});')
        elif kind == "slide":
            js.append(f'tl.fromTo("#sh{i}", {{opacity: 0, x: 180, skewX: 6, filter: "blur(10px)"}}, '
                      f'{{opacity: 1, x: 0, skewX: 0, filter: "blur(0px)", duration: {p}, ease: "power3.out"}}, {at - p});')
            js.append(f'tl.to("#sh{i-1}", {{x: -180, skewX: -6, filter: "blur(10px)", duration: {p}, ease: "power3.in"}}, {at - p});')
        elif kind == "zoom":
            js.append(f'tl.fromTo("#sh{i}", {{opacity: 0, scale: 0.6, filter: "blur(8px)"}}, '
                      f'{{opacity: 1, scale: 1, filter: "blur(0px)", duration: {p}, ease: "power3.out"}}, {at - p});')
            js.append(f'tl.to("#sh{i-1}", {{scale: 2.2, filter: "blur(10px)", duration: {p}, ease: "power3.in"}}, {at - p});')
        elif kind == "flash":
            js.append(f'tl.set("#sh{i}", {{opacity: 0}}, {at - p}); tl.set("#sh{i}", {{opacity: 1}}, {at});')
            js.append(f'tl.to("#sh{i-1}", {{filter: "brightness(2.6)", duration: {p}, ease: "power2.in"}}, {at - p});')
            js.append(f'tl.fromTo("#flash", {{opacity: 0}}, {{opacity: 0.8, duration: 0.15, ease: "power2.in", immediateRender: false}}, {at - 0.15});')
            js.append(f'tl.to("#flash", {{opacity: 0, duration: 0.4, ease: "power2.out"}}, {at});')
        elif kind == "leak":
            js.append(f'tl.set("#sh{i}", {{opacity: 0}}, {at - p}); tl.set("#sh{i}", {{opacity: 1}}, {at});')
            js.append(f'tl.fromTo("#leak-warm", {{opacity: 0}}, {{opacity: 0.55, duration: 0.3, ease: "power1.in", immediateRender: false}}, {at - 0.3});')
            js.append(f'tl.fromTo("#leak-1", {{opacity: 0, x: -200}}, {{opacity: 0.9, x: 200, duration: 0.5, ease: "sine.inOut", immediateRender: false}}, {at - 0.3});')
            js.append(f'tl.fromTo("#leak-2", {{opacity: 0, x: -100}}, {{opacity: 0.8, x: 160, duration: 0.6, ease: "sine.inOut", immediateRender: false}}, {at - 0.25});')
            js.append(f'tl.to("#leak-warm", {{opacity: 0, duration: 0.5, ease: "power2.out"}}, {at + 0.05});')
            js.append(f'tl.to("#leak-1", {{opacity: 0, x: 500, duration: 0.45, ease: "power1.out"}}, {at + 0.2});')
            js.append(f'tl.to("#leak-2", {{opacity: 0, x: 380, duration: 0.45, ease: "power1.out"}}, {at + 0.35});')
        # cut = ตัดตรง ไม่มีเอฟเฟกต์
        # คืนค่าช็อตก่อนหน้าหลังทรานสิชัน (กันค่าค้างตอน seek)
        js.append(f'tl.set("#sh{i-1}", {{x: 0, skewX: 0, scale: 1, filter: "none"}}, {at + 0.01});')

    # ---- หัวข้อ: เส้นทองวาด + ตัวอักษรเลื่อนขึ้น + แสงวิ่งผ่านหนึ่งครั้ง ----
    hook = content.get("hook")
    if hook:
        els.append(f'<div id="hook" class="hook clip" data-start="{hook["start"]}" '
                   f'data-duration="{hook["end"] - hook["start"]:.2f}" data-track-index="6">'
                   f'<div class="shine">{rich(hook["text"])}</div></div>')
        a, b = hook["start"], hook["end"]
        js.append(f'tl.fromTo("#hook .shine", {{opacity: 0, scale: 1.25, filter: "blur(14px)"}}, '
                  f'{{opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.7, ease: "expo.out"}}, {a});')
        js.append(f'tl.fromTo("#hook .shine", {{backgroundPosition: "120% 0"}}, {{backgroundPosition: "-20% 0", duration: 1.1, ease: "power2.inOut"}}, {a + 0.6});')
        js.append(f'tl.to("#hook", {{opacity: 0, y: -30, duration: 0.35, ease: "power2.in"}}, {b - 0.35});')

    for i, t in enumerate(content["titles"]):
        a, b = t["start"], t["end"]
        els.append(f'<div id="t{i}" class="title clip" data-start="{a}" data-duration="{b - a:.2f}" data-track-index="3">'
                   f'<div class="title-mask"><div class="shine">{rich(t["text"])}</div></div><div class="rule"></div></div>')
        js.append(f'tl.fromTo("#t{i} .rule", {{scaleX: 0}}, {{scaleX: 1, duration: 0.6, ease: "power4.out"}}, {a + 0.05});')
        js.append(f'tl.fromTo("#t{i} .shine", {{yPercent: 110}}, {{yPercent: 0, duration: 0.55, ease: "power3.out"}}, {a + 0.1});')
        js.append(f'tl.fromTo("#t{i} .shine", {{backgroundPosition: "120% 0"}}, {{backgroundPosition: "-20% 0", duration: 1.0, ease: "power2.inOut"}}, {a + 0.7});')
        js.append(f'tl.to("#t{i} .rule", {{scaleX: 0, transformOrigin: "100% 50%", duration: 0.3, ease: "power2.in"}}, {b - 0.35});')
        js.append(f'tl.to("#t{i} .shine", {{yPercent: -110, duration: 0.3, ease: "power2.in"}}, {b - 0.32});')

    # ---- ป้ายชื่อ (lower third แบบ lt-kicker-name) ----
    for i, lt in enumerate(content.get("lower_thirds", [])):
        lt = {"kicker": BRAND["staff_role"], "name": BRAND["staff_name"], **lt}
        a, b = lt["start"], lt["end"]
        els.append(f'<div id="lt{i}" class="lt clip" data-start="{a}" data-duration="{b - a:.2f}" data-track-index="4">'
                   f'<div class="lt-kickwrap"><span class="lt-kicker">{html.escape(lt["kicker"])}</span></div>'
                   f'<div class="lt-name">{html.escape(lt["name"])}</div><div class="lt-base"></div></div>')
        js.append(f'tl.fromTo("#lt{i} .lt-kicker", {{y: -46}}, {{y: 0, duration: 0.42, ease: "back.out(2)"}}, {a + 0.1});')
        js.append(f'tl.fromTo("#lt{i} .lt-name", {{y: 34, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.45, ease: "back.out(1.5)"}}, {a + 0.3});')
        js.append(f'tl.fromTo("#lt{i} .lt-base", {{scaleX: 0}}, {{scaleX: 1, duration: 0.5, ease: "power4.out"}}, {a + 0.5});')
        js.append(f'tl.to("#lt{i} .lt-base", {{scaleX: 0, duration: 0.3, ease: "power2.in"}}, {b - 0.5});')
        js.append(f'tl.to("#lt{i} .lt-name", {{y: -16, opacity: 0, duration: 0.32, ease: "power2.in"}}, {b - 0.45});')
        js.append(f'tl.to("#lt{i} .lt-kicker", {{y: -46, duration: 0.3, ease: "power2.in"}}, {b - 0.42});')

    # ---- ซับ (rail): ขึ้นจากล่าง คำสีทองเด้งเล็กน้อย ----
    for i, c in enumerate(content["captions"]):
        a, b = c["start"], c["end"]
        els.append(f'<div id="c{i}" class="line clip" data-start="{a}" data-duration="{b - a:.2f}" '
                   f'data-track-index="{7 + i % 2}"><span>{rich(c["text"])}</span></div>')
        js.append(f'tl.fromTo("#c{i} span", {{opacity: 0, y: 26, filter: "blur(6px)"}}, '
                  f'{{opacity: 1, y: 0, filter: "blur(0px)", duration: 0.28, ease: "power2.out"}}, {a});')
        if "*" in c["text"]:
            js.append(f'tl.fromTo("#c{i} em", {{scale: 0.8}}, {{scale: 1, duration: 0.35, ease: "back.out(3)"}}, {a + 0.12});')
        js.append(f'tl.to("#c{i} span", {{opacity: 0, duration: 0.14}}, {b - 0.14});')

    # ---- การ์ดปิดท้าย ----
    ea = end["start"]
    els.append(f'<div id="endshade" class="clip" data-start="{ea}" data-duration="{total - ea:.2f}" data-track-index="9"></div>')
    els.append(f'<div id="brand" class="end clip" data-start="{ea}" data-duration="{total - ea:.2f}" data-track-index="10">'
               f'<div class="shine" style="font-size: {brand_size(end["brand"])}px">{html.escape(end["brand"])}</div>'
               f'<div class="end-rule"></div></div>')
    els.append(f'<div id="cta" class="cta clip" data-start="{ea}" data-duration="{total - ea:.2f}" data-track-index="11">'
               f'<span>{html.escape(end["cta"])}</span></div>')
    js.append(f'tl.fromTo("#endshade", {{opacity: 0}}, {{opacity: 1, duration: 0.7}}, {ea});')
    js.append(f'tl.fromTo("#brand .shine", {{opacity: 0, scale: 1.35, filter: "blur(12px)"}}, '
              f'{{opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.9, ease: "expo.out"}}, {ea + 0.2});')
    js.append(f'tl.fromTo("#brand .end-rule", {{scaleX: 0}}, {{scaleX: 1, duration: 0.7, ease: "power4.out"}}, {ea + 0.6});')
    js.append(f'tl.fromTo("#brand .shine", {{backgroundPosition: "120% 0"}}, {{backgroundPosition: "-20% 0", duration: 1.2, ease: "power2.inOut"}}, {ea + 1.0});')
    js.append(f'tl.fromTo("#cta span", {{opacity: 0, scale: 0.7}}, {{opacity: 1, scale: 1, duration: 0.55, ease: "back.out(2.2)"}}, {ea + 0.9});')
    js.append(f'tl.to("#cta span", {{scale: 1.06, duration: 0.5, ease: "sine.inOut", yoyo: true, repeat: 3}}, {ea + 1.6});')

    # ---- เกรนฟิล์ม: เลื่อนตำแหน่งแบบกำหนดได้ทุกเฟรม (แทน CSS animation) ----
    js.append(f'for (let k = 0; k < {int(total * 12)}; k++) '
              f'tl.set("#grain .g", {{x: ((k * 37) % 20 - 10) + "%", y: ((k * 53) % 20 - 10) + "%"}}, k / 12);')

    page = (HERE / "index.template.html").read_text()
    page = (page.replace("{{TOTAL}}", str(total))
                .replace("{{AUDIO}}", audio.name)
                .replace("{{GRAIN}}", GRAIN)
                .replace("{{ACCENT}}", BRAND["colors"]["accent"])
                .replace("{{ACCENT_LIGHT}}", BRAND["colors"]["accent_light"])
                .replace("{{ACCENT_DARK}}", BRAND["colors"]["accent_dark"])
                .replace("{{SHOTS}}", "\n      ".join(shot_els))
                .replace("{{ELEMENTS}}", "\n      ".join(els))
                .replace("{{JS}}", "\n      ".join(js)))
    (proj / "index.html").write_text(page)
    print(f"สร้างแล้ว: {proj / 'index.html'} ({len(shots)} ช็อต, {len(content['titles'])} หัวข้อ, "
          f"{len(content['captions'])} ซับ, {len(content.get('lower_thirds', []))} ป้ายชื่อ)")


if __name__ == "__main__":
    main()
