"""เทมเพลตกลาง "รีวิวลูกค้า": ให้เสียงลูกค้าเป็นพระเอก ดูอบอุ่น น่าเชื่อถือ ใช้ได้ทุกร้าน

หน้าตา: ไม่มีการ์ดหรือดาว ให้ภาพลูกค้าจริงเป็นพระเอก
เมื่อลูกค้าพูดคำสำคัญ (เช่น "ดีมาก" "ไม่เจ็บเลย") คำนั้นขึ้นตัวใหญ่ในเครื่องหมายคำพูดตรงจังหวะที่พูด
ซับอยู่ในกล่องคำพูด (มีหางชี้ลง), หัวข้อเป็นป้ายแคปซูลค้างด้านบน, การ์ดจบชื่อร้าน + ปุ่ม
ไม่มีชื่อลูกค้าและไม่มีป้ายชื่อคนพูด (ตามกฎ repo)

ใช้:
  python3 -I scripts/cut_shots.py plan.json raw shots --head-pad 0.4 --curves check.json
  python3 -I templates/review-voice/build.py content.json <โฟลเดอร์โปรเจกต์>
  cd <โฟลเดอร์โปรเจกต์> && npx hyperframes lint && npx hyperframes render -o out.mp4 --quiet

content.json (ดู content.example.json):
  duration, shots_dir, audio            เหมือน review-motion
  hook        {start, end, text}        ประโยคเปิด ด้านบนจอ
  titles      [{start, end, text}]      หัวข้อค้างบนจอ
  captions    [{start, end, text}]      ซับบรรทัดเดียว (*คำ* = สีแบรนด์) ไม่ใส่หรือ [] = ไม่มีซับ (ตามคำตอบข้อ 3.5 ใน docs/09)
              ไม่มีซับ: คำสำคัญอยู่ตำแหน่งซับ · มีซับ: คำสำคัญย้ายขึ้นเหนือซับ
  keywords    [{start, end?, text}]   คำสำคัญที่ลูกค้าพูด ขึ้นตัวใหญ่กลางจอค่อนล่าง (end ค่าเริ่ม start + 1.8)
              start = เวลาที่ลูกค้าเริ่มพูดคำนั้น ดูจากผลถอดเสียง (เวลารายคำ) ต้องเป็นคำที่ลูกค้าพูดจริง ห้ามแต่ง
              เลือก 2–4 คำต่อคลิป: คำชม / คำที่ตอบสิ่งที่ลูกค้ากังวล (ดูโปรไฟล์) / ผลลัพธ์ที่เห็นได้
  transitions {"<เลขช็อต>": "soft|rise|cut"}  ค่าเริ่ม: สลับ soft / rise
  end_card    {start, text?}            ชื่อร้าน + ข้อความสั้น + ปุ่มชวนจาก brand.json
"""
import html
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE.parent / "vendor"
BRAND = json.loads((HERE.parent.parent / "brand.json").read_text())


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
    shot_els, els, js = [], [], []

    # ---- ช็อต ----
    alt = ["soft", "rise"]
    for i, s in enumerate(shots):
        at, dur, pad = s["at"], s["dur"], s["head_pad"]
        if i == 0:
            v_start, v_dur, media = 0, dur, f' data-media-start="{pad}"'
        else:
            v_start, v_dur, media = round(at - pad, 3), round(dur + pad, 3), ""
        shot_els.append(
            f'<div id="sh{i}" class="shot"><video id="v{i}" class="clip" src="shots/{s["file"]}" muted playsinline '
            f'data-start="{v_start}" data-duration="{v_dur}"{media} data-track-index="0"></video></div>')
        js.append(f'tl.fromTo("#v{i}", {{scale: 1.06}}, {{scale: 1.0, duration: {v_dur}, ease: "none"}}, {v_start});')
        if i == 0:
            continue
        kind = overrides.get(str(i)) or alt[i % 2]
        p = min(pad, 0.4)
        if kind == "soft":
            js.append(f'tl.fromTo("#sh{i}", {{opacity: 0, scale: 1.08, filter: "blur(10px)"}}, '
                      f'{{opacity: 1, scale: 1, filter: "blur(0px)", duration: {p}, ease: "power2.out"}}, {at - p});')
        elif kind == "rise":
            js.append(f'tl.fromTo("#sh{i}", {{yPercent: 100, borderRadius: "60px 60px 0 0"}}, '
                      f'{{yPercent: 0, borderRadius: "0px 0px 0 0", duration: {p}, ease: "power3.out"}}, {at - p});')
            js.append(f'tl.to("#sh{i-1}", {{scale: 0.92, opacity: 0.6, duration: {p}, ease: "power2.in"}}, {at - p});')
        js.append(f'tl.set("#sh{i-1}", {{scale: 1, opacity: 1, filter: "none"}}, {at + 0.01});')

    # ---- ประโยคเปิด ----
    hook = content.get("hook")
    if hook:
        a, b = hook["start"], hook["end"]
        els.append(f'<div id="hook" class="hook clip" data-start="{a}" data-duration="{b - a:.2f}" data-track-index="6">'
                   f'<div class="hk-q">“</div><div class="hk-tx">{rich(hook["text"])}</div></div>')
        js.append(f'tl.fromTo("#hook .hk-q", {{scale: 0, rotation: -20}}, {{scale: 1, rotation: 0, duration: 0.5, ease: "back.out(2.5)"}}, {a});')
        js.append(f'tl.fromTo("#hook .hk-tx", {{y: 30, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.5, ease: "power3.out"}}, {a + 0.2});')
        js.append(f'tl.to("#hook", {{y: -30, opacity: 0, duration: 0.3, ease: "power2.in"}}, {b - 0.3});')

    # ---- หัวข้อแคปซูล ----
    for i, t in enumerate(content["titles"]):
        a, b = t["start"], t["end"]
        els.append(f'<div id="t{i}" class="title clip" data-start="{a}" data-duration="{b - a:.2f}" data-track-index="3">'
                   f'<div class="pill"><span class="dot"></span><span class="tx">{rich(t["text"])}</span></div></div>')
        js.append(f'tl.fromTo("#t{i} .pill", {{y: -30, opacity: 0, scale: 0.9}}, {{y: 0, opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.8)"}}, {a + 0.05});')
        js.append(f'tl.fromTo("#t{i} .dot", {{scale: 0}}, {{scale: 1, duration: 0.3, ease: "back.out(3)"}}, {a + 0.35});')
        js.append(f'tl.to("#t{i} .pill", {{y: -20, opacity: 0, duration: 0.28, ease: "power2.in"}}, {b - 0.28});')

    # ---- คำสำคัญที่ลูกค้าพูด: ขึ้นตัวใหญ่ตรงจังหวะที่พูด ----
    for i, kw in enumerate(content.get("keywords", [])):
        a, b = kw["start"], kw.get("end", kw["start"] + 1.8)
        kw_pos = "kw-high" if content.get("captions") else "kw-low"
        els.append(f'<div id="k{i}" class="kw {kw_pos} clip" data-start="{a}" data-duration="{b - a:.2f}" data-track-index="4">'
                   f'<div class="kw-in"><span class="kq">“</span><span class="kt">{rich(kw["text"])}</span><span class="kq">”</span>'
                   f'<span class="kbar"></span></div></div>')
        js.append(f'tl.fromTo("#k{i} .kbar", {{scaleX: 0}}, {{scaleX: 1, duration: 0.25, ease: "power3.out"}}, {a});')
        js.append(f'tl.fromTo("#k{i} .kt", {{scale: 1.6, opacity: 0, filter: "blur(10px)"}}, '
                  f'{{scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.32, ease: "back.out(2)"}}, {a + 0.05});')
        js.append(f'tl.fromTo("#k{i} .kq", {{scale: 0}}, {{scale: 1, duration: 0.3, ease: "back.out(3)", stagger: 0.06}}, {a + 0.2});')
        js.append(f'tl.to("#k{i} .kw-in", {{scale: 1.04, duration: {max(b - a - 0.6, 0.3):.2f}, ease: "none"}}, {a + 0.35});')
        js.append(f'tl.to("#k{i} .kw-in", {{opacity: 0, y: -20, duration: 0.25, ease: "power2.in"}}, {b - 0.25});')

    # ---- ซับในกล่องคำพูด ----
    for i, c in enumerate(content.get("captions", [])):
        a, b = c["start"], c["end"]
        els.append(f'<div id="c{i}" class="line clip" data-start="{a}" data-duration="{b - a:.2f}" '
                   f'data-track-index="{7 + i % 2}"><span>{rich(c["text"])}</span></div>')
        js.append(f'tl.fromTo("#c{i} span", {{opacity: 0, scale: 0.92}}, {{opacity: 1, scale: 1, duration: 0.22, ease: "back.out(2)"}}, {a});')
        js.append(f'tl.to("#c{i} span", {{opacity: 0, duration: 0.12}}, {b - 0.12});')

    # ---- การ์ดจบ ----
    ea = end["start"]
    sub = f'<div class="end-sub">{html.escape(end["text"])}</div>' if end.get("text") else ""
    els.append(f'<div id="endshade" class="clip" data-start="{ea}" data-duration="{total - ea:.2f}" data-track-index="9"></div>')
    els.append(f'<div id="endcard" class="end clip" data-start="{ea}" data-duration="{total - ea:.2f}" data-track-index="10">'
               f'<div class="end-name">{html.escape(end["brand"])}</div>{sub}<div class="end-cta">{html.escape(end["cta"])}</div></div>')
    js.append(f'tl.fromTo("#endshade", {{opacity: 0}}, {{opacity: 1, duration: 0.6}}, {ea});')
    js.append(f'tl.fromTo("#endcard .end-name", {{y: 40, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.55, ease: "back.out(1.6)"}}, {ea + 0.2});')
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
    print(f"สร้างแล้ว: {proj / 'index.html'} ({len(shots)} ช็อต, {len(content.get('keywords', []))} คำสำคัญ, "
          f"{len(content['titles'])} หัวข้อ, {len(content.get('captions', []))} ซับ)")


if __name__ == "__main__":
    main()
