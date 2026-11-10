"""เทมเพลตกลาง "ก่อน-หลัง": เทียบภาพให้เห็นผลชัด ใช้ได้ทุกร้านที่ขายผลงาน

หน้าตา: สะอาด ทันสมัย ป้าย "ก่อน" สีเข้ม / "หลัง" สีแบรนด์, ป้ายผลลัพธ์เด้งหลังเห็นภาพหลัง
ช่วงเทียบมี 3 แบบ:
  slider  เส้นแบ่งเลื่อนไปมา ซ้าย = ก่อน ขวา = หลัง (มีปุ่มจับกลางเส้น)
  stack   แบ่งจอบน (ก่อน) / ล่าง (หลัง) ภาพหลังปาดเข้าจากขวา
  flip    เห็นภาพก่อนเต็มจอ แล้วม่านปาดเปิดเป็นภาพหลัง ป้ายสลับตาม
หัวข้อแบบการ์ดขาวมีแถบสีแบรนด์ ค้างด้านบนทุกช่วง (ช่วง stack หัวข้อย้ายมากลางจอบนเส้นแบ่ง)

ใช้:
  python3 -I scripts/cut_shots.py plan.json raw shots --head-pad 0.4 --curves check.json
  python3 -I templates/review-compare/build.py content.json <โฟลเดอร์โปรเจกต์>
  cd <โฟลเดอร์โปรเจกต์> && npx hyperframes lint && npx hyperframes render -o out.mp4 --quiet

content.json (ดู content.example.json):
  duration, shots_dir, audio            เหมือน review-motion
  hook        {start, end, text}        ประโยคเปิด ด้านบนจอ
  titles      [{start, end, text}]      หัวข้อค้างบนจอ
  captions    [{start, end, text}]      ซับบรรทัดเดียว (*คำ* = สีแบรนด์)
  compare     [{start, end, before, after, mode?, result?, moves?}]
              before/after = เลขช็อตใน shots.json (เริ่มที่ 0) คลิปต้องยาวไม่น้อยกว่าช่วงนี้ (ตั้ง dur ในแผนช็อตให้พอ)
              mode = slider (ค่าเริ่ม) | stack | flip
              result = ข้อความป้ายผลลัพธ์ เช่น "ทำครั้งเดียว" (ไม่ใส่ = ไม่มีป้าย)
              moves (slider) = ตำแหน่งเส้นเป็น % จากซ้าย ค่าเริ่ม [100, 0, 50]  (100 = เห็นแต่ก่อน, 0 = เห็นแต่หลัง)
  transitions {"<เลขช็อต>": "push|fade|cut"}  ค่าเริ่ม: สลับ push / fade
  end_card    {start, text?}            ชื่อร้าน + ข้อความสั้น + ปุ่มชวนจาก brand.json
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
W = 1080


def rich(text):
    """*คำ* = สีแบรนด์, | = ขึ้นบรรทัดใหม่"""
    out, on = [], False
    for part in html.escape(text).split("*"):
        out.append(f"<em>{part}</em>" if on else part)
        on = not on
    return "".join(out).replace("|", "<br />")


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
    overrides = content.get("transitions", {})
    compares = content.get("compare", [])
    shot_els, els, js = [], [], []

    # ---- ช็อตปกติ ----
    alt = ["push", "fade"]
    for i, s in enumerate(shots):
        at, dur, pad = s["at"], s["dur"], s["head_pad"]
        if i == 0:
            v_start, v_dur, media = 0, dur, f' data-media-start="{pad}"'
        else:
            v_start, v_dur, media = round(at - pad, 3), round(dur + pad, 3), ""
        shot_els.append(
            f'<div id="sh{i}" class="shot"><video id="v{i}" class="clip" src="shots/{s["file"]}" muted playsinline '
            f'data-start="{v_start}" data-duration="{v_dur}"{media} data-track-index="0"></video></div>')
        js.append(f'tl.fromTo("#v{i}", {{scale: 1.0}}, {{scale: 1.05, duration: {v_dur}, ease: "none"}}, {v_start});')
        if i == 0:
            continue
        kind = overrides.get(str(i)) or alt[i % 2]
        p = min(pad, 0.35)
        if kind == "push":
            js.append(f'tl.fromTo("#sh{i}", {{xPercent: 100}}, {{xPercent: 0, duration: {p}, ease: "power3.inOut"}}, {at - p});')
            js.append(f'tl.to("#sh{i-1}", {{xPercent: -30, duration: {p}, ease: "power3.inOut"}}, {at - p});')
        elif kind == "fade":
            js.append(f'tl.fromTo("#sh{i}", {{opacity: 0}}, {{opacity: 1, duration: {p}, ease: "sine.inOut"}}, {at - p});')
        js.append(f'tl.set("#sh{i-1}", {{xPercent: 0}}, {at + 0.01});')

    # ---- ช่วงก่อน-หลัง: วางทับช็อตปกติ ----
    stack_ranges = []
    for k, c in enumerate(compares):
        a, b = c["start"], c["end"]
        d = round(b - a, 2)
        mode = c.get("mode", "slider")
        sel = f"#cmp{k}"

        def vid(idx, side):
            s = shots[idx]
            return (f'<video id="cmp{k}{side}" class="clip" src="shots/{s["file"]}" muted playsinline '
                    f'data-start="{a}" data-duration="{d}" data-media-start="{s["head_pad"]}" data-track-index="{11 + k * 2 + (side == "a")}"></video>')
        result = (f'<div class="result"><span class="r-tick"></span>{html.escape(c["result"])}</div>'
                  if c.get("result") else "")
        bl, al = '<div class="tag tag-b">ก่อน</div>', '<div class="tag tag-a">หลัง</div>'

        if mode == "stack":
            stack_ranges.append((a, b))
            els.append(f'<div id="cmp{k}" class="cmp stack">'
                       f'<div class="half top">{vid(c["before"], "b")}{bl}</div>'
                       f'<div class="half bot">{vid(c["after"], "a")}{al}</div><div class="seam"></div>{result}</div>')
            js.append(f'tl.fromTo("{sel} .top", {{xPercent: -100}}, {{xPercent: 0, duration: 0.45, ease: "power3.out"}}, {a});')
            js.append(f'tl.fromTo("{sel} .bot", {{xPercent: 100}}, {{xPercent: 0, duration: 0.45, ease: "power3.out"}}, {a + 0.5});')
            js.append(f'tl.fromTo("{sel} .seam", {{scaleX: 0}}, {{scaleX: 1, duration: 0.4, ease: "power2.out"}}, {a + 0.9});')
            js.append(f'tl.fromTo("{sel} .tag-b", {{x: -40, opacity: 0}}, {{x: 0, opacity: 1, duration: 0.35, ease: "back.out(2)"}}, {a + 0.35});')
            js.append(f'tl.fromTo("{sel} .tag-a", {{x: -40, opacity: 0}}, {{x: 0, opacity: 1, duration: 0.35, ease: "back.out(2)"}}, {a + 0.85});')
            reveal = a + 1.1
        elif mode == "flip":
            els.append(f'<div id="cmp{k}" class="cmp flip">'
                       f'<div class="full fb">{vid(c["before"], "b")}</div><div class="full fa">{vid(c["after"], "a")}</div>'
                       f'<div class="sweep"></div><div class="corner">{bl}{al}</div>{result}</div>')
            mid = a + max(d * 0.4, 1.0)
            js.append(f'tl.fromTo("{sel} .tag-b", {{y: -30, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.35, ease: "back.out(2)"}}, {a + 0.15});')
            js.append(f'tl.fromTo("{sel} .fa", {{clipPath: "inset(0% 0% 0% 100%)"}}, {{clipPath: "inset(0% 0% 0% 0%)", duration: 0.6, ease: "power3.inOut"}}, {mid});')
            js.append(f'tl.fromTo("{sel} .sweep", {{x: {W}}}, {{x: -40, duration: 0.6, ease: "power3.inOut"}}, {mid});')
            js.append(f'tl.to("{sel} .sweep", {{opacity: 0, duration: 0.2}}, {mid + 0.6});')
            js.append(f'tl.to("{sel} .tag-b", {{y: 30, opacity: 0, duration: 0.25, ease: "power2.in"}}, {mid + 0.1});')
            js.append(f'tl.fromTo("{sel} .tag-a", {{y: -30, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.35, ease: "back.out(2)"}}, {mid + 0.4});')
            reveal = mid + 0.6
        else:  # slider
            moves = c.get("moves", [100, 0, 50])
            els.append(f'<div id="cmp{k}" class="cmp slider">'
                       f'<div class="full fa">{vid(c["after"], "a")}</div><div class="full fb">{vid(c["before"], "b")}</div>'
                       f'<div class="handle"><div class="knob"><i class="ar l"></i><i class="ar r"></i></div></div>'
                       f'<div class="side side-l">{bl}</div><div class="side side-r">{al}</div>{result}</div>')
            # fb (ก่อน) แสดงเฉพาะซ้ายของเส้น
            js.append(f'tl.set("{sel} .fb", {{clipPath: "inset(0% {100 - moves[0]}% 0% 0%)"}}, {a}); '
                      f'tl.set("{sel} .handle", {{x: {moves[0] * W / 100}}}, {a});')
            js.append(f'tl.fromTo("{sel} .handle", {{opacity: 0}}, {{opacity: 1, duration: 0.3}}, {a + 0.1});')
            js.append(f'tl.fromTo("{sel} .tag", {{scale: 0}}, {{scale: 1, duration: 0.35, ease: "back.out(2.4)", stagger: 0.12}}, {a + 0.2});')
            seg = max((d - 1.4) / max(len(moves) - 1, 1), 0.6)
            t = a + 0.6
            for p0, p1 in zip(moves, moves[1:]):
                js.append(f'tl.fromTo("{sel} .fb", {{clipPath: "inset(0% {100 - p0}% 0% 0%)"}}, '
                          f'{{clipPath: "inset(0% {100 - p1}% 0% 0%)", duration: {seg * 0.7:.2f}, ease: "power2.inOut", immediateRender: false}}, {t:.2f});')
                js.append(f'tl.fromTo("{sel} .handle", {{x: {p0 * W / 100}}}, {{x: {p1 * W / 100}, duration: {seg * 0.7:.2f}, ease: "power2.inOut", immediateRender: false}}, {t:.2f});')
                t += seg
            reveal = a + 0.6 + seg
        if c.get("result"):
            js.append(f'tl.fromTo("{sel} .result", {{scale: 0, rotation: -6}}, {{scale: 1, rotation: -2, duration: 0.45, ease: "back.out(2.5)"}}, {reveal:.2f});')
            js.append(f'tl.fromTo("{sel} .r-tick", {{scale: 0}}, {{scale: 1, duration: 0.3, ease: "back.out(3)"}}, {reveal + 0.25:.2f});')
        # กล่องเทียบไม่มีเวลาของตัวเอง (วิดีโอข้างในมีแล้ว) คุมการแสดงด้วย timeline
        js.append(f'tl.set("{sel}", {{autoAlpha: 0}}, 0); tl.set("{sel}", {{autoAlpha: 1}}, {a}); tl.set("{sel}", {{autoAlpha: 0}}, {b});')

    # ---- ประโยคเปิด ----
    hook = content.get("hook")
    if hook:
        a, b = hook["start"], hook["end"]
        lines = "".join(f'<div class="hk-line"><span>{rich(l)}</span></div>' for l in hook["text"].split("|"))
        els.append(f'<div id="hook" class="hook clip" data-start="{a}" data-duration="{b - a:.2f}" data-track-index="6">{lines}</div>')
        js.append(f'tl.fromTo("#hook .hk-line span", {{yPercent: 110}}, {{yPercent: 0, duration: 0.5, ease: "power3.out", stagger: 0.15}}, {a});')
        js.append(f'tl.to("#hook .hk-line span", {{yPercent: -110, duration: 0.3, ease: "power2.in", stagger: 0.05}}, {b - 0.35});')

    # ---- หัวข้อการ์ดขาว ----
    def in_stack(a, b):
        return any(sa < b and a < sb for sa, sb in stack_ranges)
    for i, t in enumerate(content["titles"]):
        a, b = t["start"], t["end"]
        mid = " mid" if in_stack(a, b) else ""
        els.append(f'<div id="t{i}" class="title clip{mid}" data-start="{a}" data-duration="{b - a:.2f}" data-track-index="3">'
                   f'<div class="card"><span class="bar"></span><span class="tx">{rich(t["text"])}</span></div></div>')
        js.append(f'tl.fromTo("#t{i} .card", {{clipPath: "inset(0% 100% 0% 0%)"}}, {{clipPath: "inset(0% 0% 0% 0%)", duration: 0.45, ease: "power3.out"}}, {a + 0.05});')
        js.append(f'tl.fromTo("#t{i} .tx", {{x: -24, opacity: 0}}, {{x: 0, opacity: 1, duration: 0.4, ease: "power2.out"}}, {a + 0.25});')
        js.append(f'tl.to("#t{i} .card", {{clipPath: "inset(0% 0% 0% 100%)", duration: 0.3, ease: "power2.in"}}, {b - 0.3});')

    # ---- ซับ ----
    for i, c in enumerate(content["captions"]):
        a, b = c["start"], c["end"]
        els.append(f'<div id="c{i}" class="line clip" data-start="{a}" data-duration="{b - a:.2f}" '
                   f'data-track-index="{7 + i % 2}"><span>{rich(c["text"])}</span></div>')
        js.append(f'tl.fromTo("#c{i} span", {{opacity: 0, y: 16}}, {{opacity: 1, y: 0, duration: 0.22, ease: "power2.out"}}, {a});')
        js.append(f'tl.to("#c{i} span", {{opacity: 0, duration: 0.12}}, {b - 0.12});')

    # ---- การ์ดจบ ----
    ea = end["start"]
    sub = f'<div class="end-sub">{html.escape(end["text"])}</div>' if end.get("text") else ""
    els.append(f'<div id="endshade" class="clip" data-start="{ea}" data-duration="{total - ea:.2f}" data-track-index="9"></div>')
    els.append(f'<div id="endcard" class="end clip" data-start="{ea}" data-duration="{total - ea:.2f}" data-track-index="10">'
               f'<div class="end-name">{html.escape(end["brand"])}</div>{sub}<div class="end-cta">{html.escape(end["cta"])}</div></div>')
    js.append(f'tl.fromTo("#endshade", {{opacity: 0}}, {{opacity: 1, duration: 0.5}}, {ea});')
    js.append(f'tl.fromTo("#endcard .end-name", {{y: 40, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.55, ease: "power3.out"}}, {ea + 0.2});')
    if sub:
        js.append(f'tl.fromTo("#endcard .end-sub", {{opacity: 0}}, {{opacity: 1, duration: 0.4}}, {ea + 0.55});')
    js.append(f'tl.fromTo("#endcard .end-cta", {{scale: 0.6, opacity: 0}}, {{scale: 1, opacity: 1, duration: 0.45, ease: "back.out(2.2)"}}, {ea + 0.8});')
    js.append(f'tl.to("#endcard .end-cta", {{scale: 1.05, duration: 0.5, ease: "sine.inOut", yoyo: true, repeat: 3}}, {ea + 1.4});')

    page = (HERE / "index.template.html").read_text()
    page = (page.replace("{{TOTAL}}", str(total))
                .replace("{{AUDIO}}", audio.name)
                .replace("{{ACCENT}}", BRAND["colors"]["accent"])
                .replace("{{ACCENT_LIGHT}}", BRAND["colors"]["accent_light"])
                .replace("{{ACCENT_DARK}}", BRAND["colors"]["accent_dark"])
                .replace("{{SHOTS}}", "\n      ".join(shot_els))
                .replace("{{ELEMENTS}}", "\n      ".join(els))
                .replace("{{JS}}", "\n      ".join(js)))
    (proj / "index.html").write_text(page)
    print(f"สร้างแล้ว: {proj / 'index.html'} ({len(shots)} ช็อต, {len(compares)} ช่วงก่อน-หลัง, "
          f"{len(content['titles'])} หัวข้อ, {len(content['captions'])} ซับ)")


if __name__ == "__main__":
    main()
