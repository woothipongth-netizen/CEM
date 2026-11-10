"""เทมเพลตกลาง "ป๊อป": สนุก สีสด จังหวะเร็ว ใช้ได้ทุกร้าน

หน้าตา: หัวข้อเป็นสติกเกอร์เอียงมีขอบหนา, ซับเด้งทีละคำในป้ายสีขาว, ดาว/ประกายเด้งรอบหัวข้อ,
ทรานสิชันแบบซูมกระแทก / แถบสีปาด / ภาพเด้ง, การ์ดจบเป็นป้ายชื่อร้านกับปุ่มเด้ง
สีหลักจาก brand.json (accent) จับคู่กับสีป๊อปคงที่ (ชมพู เหลือง ฟ้า)

ใช้:
  python3 -I scripts/cut_shots.py plan.json raw shots --head-pad 0.4 --curves check.json
  python3 -I templates/review-pop/build.py content.json <โฟลเดอร์โปรเจกต์>
  cd <โฟลเดอร์โปรเจกต์> && npx hyperframes lint && npx hyperframes render -o out.mp4 --quiet

content.json (ดู content.example.json):
  duration, shots_dir, audio            เหมือน review-motion
  hook        {start, end, text}        ประโยคเปิดตัวใหญ่ เด้งทีละบรรทัด
  titles      [{start, end, text, pos?}] หัวข้อสติกเกอร์ค้างบนจอ สีสลับกันทุกช่วง  pos: "low" = ย้ายลงกลางจอ
  captions    [{start, end, text}]      ซับบรรทัดเดียว เด้งทีละคำ (*คำ* = เน้นสี)
  transitions {"<เลขช็อต>": "punch|wipe|bounce|cut"}  ค่าเริ่ม: จุดเปลี่ยนหัวข้อ = wipe, ที่เหลือสลับ punch / bounce
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
POP = ["#ff4f8b", "#ffd23f", "#3ec7ff"]  # ชมพู เหลือง ฟ้า


def rich(text):
    """*คำ* = เน้นสี, | = ขึ้นบรรทัดใหม่"""
    out, on = [], False
    for part in html.escape(text).split("*"):
        out.append(f"<em>{part}</em>" if on else part)
        on = not on
    return "".join(out).replace("|", "<br />")


def words(text):
    """แยกซับเป็นก้อนตามช่องว่าง ให้เด้งทีละก้อน (ภาษาไทยเว้นวรรคเป็นวลี)"""
    out, on = [], False
    for part in text.replace("|", " ").split("*"):
        for w in part.split():
            w = html.escape(w)
            out.append(f'<b class="w{" hl" if on else ""}">{w}</b>')
        on = not on
    return " ".join(out)


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

    # ---- ช็อต + ทรานสิชัน ----
    alt = ["punch", "bounce"]
    for i, s in enumerate(shots):
        at, dur, pad = s["at"], s["dur"], s["head_pad"]
        if i == 0:
            v_start, v_dur, media = 0, dur, f' data-media-start="{pad}"'
        else:
            v_start, v_dur, media = round(at - pad, 3), round(dur + pad, 3), ""
        shot_els.append(
            f'<div id="sh{i}" class="shot"><video id="v{i}" class="clip" src="shots/{s["file"]}" muted playsinline '
            f'data-start="{v_start}" data-duration="{v_dur}"{media} data-track-index="0"></video></div>')
        js.append(f'tl.fromTo("#v{i}", {{scale: 1.04}}, {{scale: 1.12, duration: {v_dur}, ease: "none"}}, {v_start});')
        if i == 0:
            continue
        kind = overrides.get(str(i)) or ("wipe" if round(at, 1) in title_starts else alt[i % 2])
        p = min(pad, 0.35)
        if kind == "punch":
            js.append(f'tl.to("#sh{i-1}", {{scale: 1.35, duration: {p}, ease: "power3.in"}}, {at - p});')
            js.append(f'tl.set("#sh{i}", {{opacity: 0}}, {at - p}); tl.set("#sh{i}", {{opacity: 1}}, {at});')
            js.append(f'tl.fromTo("#sh{i}", {{scale: 1.3}}, {{scale: 1, duration: 0.35, ease: "back.out(1.6)", immediateRender: false}}, {at});')
        elif kind == "bounce":
            js.append(f'tl.fromTo("#sh{i}", {{opacity: 1, yPercent: 100}}, {{yPercent: 0, duration: {p + 0.1}, ease: "back.out(1.3)"}}, {at - p});')
        elif kind == "wipe":
            js.append(f'tl.set("#sh{i}", {{opacity: 0}}, {at - p}); tl.set("#sh{i}", {{opacity: 1}}, {at});')
            for k in range(3):
                js.append(f'tl.fromTo("#bar{k}", {{xPercent: -110}}, {{xPercent: 0, duration: 0.22, ease: "power3.out", immediateRender: false}}, {at - p + k * 0.05});')
                js.append(f'tl.to("#bar{k}", {{xPercent: 110, duration: 0.25, ease: "power3.in"}}, {at + 0.02 + k * 0.05});')
        # cut = ตัดตรง
        js.append(f'tl.set("#sh{i-1}", {{scale: 1, yPercent: 0}}, {at + 0.01});')

    # ---- ประโยคเปิด: เด้งทีละบรรทัด + ดาวกระจาย ----
    hook = content.get("hook")
    if hook:
        a, b = hook["start"], hook["end"]
        lines = "".join(f'<div class="hl-line"><span>{rich(l)}</span></div>' for l in hook["text"].split("|"))
        els.append(f'<div id="hook" class="hook clip" data-start="{a}" data-duration="{b - a:.2f}" data-track-index="6">{lines}'
                   f'<i class="spark s1"></i><i class="spark s2"></i><i class="spark s3"></i></div>')
        # kinetic slam: แต่ละบรรทัดพุ่งเข้าสลับซ้าย/ขวา กระแทกแล้วจอสั่นนิดๆ
        for k in range(len(hook["text"].split("|"))):
            d = -1 if k % 2 == 0 else 1
            at = a + k * 0.32
            js.append(f'tl.fromTo("#hook .hl-line:nth-of-type({k + 1}) span", {{x: {d * 900}, scale: 1.5, rotation: {d * -10}}}, '
                      f'{{x: 0, scale: 1, rotation: 0, duration: 0.32, ease: "power4.out"}}, {at:.2f});')
            js.append(f'tl.fromTo("#hook", {{x: {d * -14}}}, {{x: 0, duration: 0.25, ease: "elastic.out(1.2, 0.3)", immediateRender: false}}, {at + 0.2:.2f});')
        js.append(f'tl.fromTo("#hook .spark", {{scale: 0, rotation: 0}}, {{scale: 1, rotation: 90, duration: 0.5, ease: "back.out(3)", stagger: 0.08}}, {a + 0.35});')
        js.append(f'tl.to("#hook .spark", {{rotation: 270, duration: {max(b - a - 1, 0.5)}, ease: "none"}}, {a + 0.85});')
        js.append(f'tl.to("#hook", {{scale: 0.6, opacity: 0, duration: 0.25, ease: "back.in(2)"}}, {b - 0.25});')

    # ---- หัวข้อสติกเกอร์ค้างบนจอ ----
    for i, t in enumerate(content["titles"]):
        a, b = t["start"], t["end"]
        color = POP[i % len(POP)]
        tilt = -3 if i % 2 == 0 else 3
        low = " low" if t.get("pos") == "low" else ""
        els.append(f'<div id="t{i}" class="title clip{low}" data-start="{a}" data-duration="{b - a:.2f}" data-track-index="3">'
                   f'<div class="sticker" style="--c:{color}; --tilt:{tilt}deg">{rich(t["text"])}</div>'
                   f'<i class="spark s4"></i><i class="spark s5"></i></div>')
        js.append(f'tl.fromTo("#t{i} .sticker", {{scale: 0, rotation: {tilt * 5}}}, {{scale: 1, rotation: {tilt}, duration: 0.5, ease: "back.out(2.2)"}}, {a + 0.05});')
        # inline highlight: แถบสีเข้มวิ่งหลังคำเน้น คำเปลี่ยนเป็นสีขาว
        if "*" in t["text"]:
            js.append(f'tl.fromTo("#t{i} .sticker em", {{backgroundSize: "0% 100%", color: "#1b1530"}}, '
                      f'{{backgroundSize: "100% 100%", color: "#ffffff", duration: 0.4, ease: "power2.inOut"}}, {a + 0.5});')
        js.append(f'tl.fromTo("#t{i} .spark", {{scale: 0}}, {{scale: 1, rotation: 180, duration: 0.45, ease: "back.out(3)", stagger: 0.1}}, {a + 0.35});')
        # หายใจเบาๆ ให้หัวข้อดูมีชีวิตตลอดช่วง
        reps = max(int((b - a - 1.2) / 1.2), 0)
        if reps:
            js.append(f'tl.to("#t{i} .sticker", {{scale: 1.04, duration: 0.6, ease: "sine.inOut", yoyo: true, repeat: {reps * 2 - 1}}}, {a + 0.6});')
        js.append(f'tl.to("#t{i}", {{scale: 0, opacity: 0, duration: 0.22, ease: "back.in(2)"}}, {b - 0.22});')

    # ---- ซับ: เด้งทีละคำ ----
    for i, c in enumerate(content["captions"]):
        a, b = c["start"], c["end"]
        n = max(len(c["text"].replace("*", "").split()), 1)
        step = min(0.12, max(b - a - 0.4, 0.1) / n)
        els.append(f'<div id="c{i}" class="line clip" data-start="{a}" data-duration="{b - a:.2f}" '
                   f'data-track-index="{7 + i % 2}"><span>{words(c["text"])}</span></div>')
        js.append(f'tl.fromTo("#c{i} span", {{scale: 0.85, opacity: 0}}, {{scale: 1, opacity: 1, duration: 0.18, ease: "back.out(2)"}}, {a});')
        js.append(f'tl.fromTo("#c{i} .w", {{y: 24, scale: 0.6, opacity: 0}}, {{y: 0, scale: 1, opacity: 1, duration: 0.25, ease: "back.out(3)", stagger: {step:.3f}}}, {a + 0.05});')
        js.append(f'tl.to("#c{i} span", {{opacity: 0, duration: 0.12}}, {b - 0.12});')

    # ---- การ์ดจบ ----
    ea = end["start"]
    sub = f'<div class="end-sub">{html.escape(end["text"])}</div>' if end.get("text") else ""
    els.append(f'<div id="endbg" class="clip" data-start="{ea}" data-duration="{total - ea:.2f}" data-track-index="9"></div>')
    els.append(f'<div id="endcard" class="end clip" data-start="{ea}" data-duration="{total - ea:.2f}" data-track-index="10">'
               f'<div class="end-name">{html.escape(end["brand"])}</div>{sub}'
               f'<div class="end-cta">{html.escape(end["cta"])}</div>'
               f'<i class="spark s6"></i><i class="spark s7"></i><i class="spark s8"></i></div>')
    js.append(f'tl.fromTo("#endbg", {{clipPath: "circle(0% at 50% 50%)"}}, {{clipPath: "circle(75% at 50% 50%)", duration: 0.5, ease: "power3.out"}}, {ea});')
    js.append(f'tl.fromTo("#endcard .end-name", {{scale: 0, rotation: -12}}, {{scale: 1, rotation: -3, duration: 0.6, ease: "back.out(2.2)"}}, {ea + 0.25});')
    if sub:
        js.append(f'tl.fromTo("#endcard .end-sub", {{y: 40, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.4, ease: "back.out(2)"}}, {ea + 0.6});')
    js.append(f'tl.fromTo("#endcard .end-cta", {{scale: 0}}, {{scale: 1, duration: 0.5, ease: "back.out(2.5)"}}, {ea + 0.8});')
    js.append(f'tl.to("#endcard .end-cta", {{scale: 1.08, duration: 0.45, ease: "sine.inOut", yoyo: true, repeat: 5}}, {ea + 1.4});')
    js.append(f'tl.fromTo("#endcard .spark", {{scale: 0}}, {{scale: 1, rotation: 180, duration: 0.5, ease: "back.out(3)", stagger: 0.1}}, {ea + 0.5});')

    page = (HERE / "index.template.html").read_text()
    page = (page.replace("{{TOTAL}}", str(total))
                .replace("{{AUDIO}}", audio.name)
                .replace("{{ACCENT}}", BRAND["colors"]["accent"])
                .replace("{{POP1}}", POP[0]).replace("{{POP2}}", POP[1]).replace("{{POP3}}", POP[2])
                .replace("{{SHOTS}}", "\n      ".join(shot_els))
                .replace("{{ELEMENTS}}", "\n      ".join(els))
                .replace("{{JS}}", "\n      ".join(js)))
    (proj / "index.html").write_text(page)
    print(f"สร้างแล้ว: {proj / 'index.html'} ({len(shots)} ช็อต, {len(content['titles'])} หัวข้อ, {len(content['captions'])} ซับ)")


if __name__ == "__main__":
    main()
