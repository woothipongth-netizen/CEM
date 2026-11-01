"""วัดละเอียดเฉพาะคลิปที่เลือกใส่แผน จากไฟล์ 4K ต้นฉบับ: กล้องสั่น / เบลอ + เก็บค่าการเคลื่อนไหวรายเฟรม

ใช้: python3 -I scripts/check_shots.py <plan.json> <โฟลเดอร์ raw> <โฟลเดอร์งาน>
ผลลัพธ์: <งาน>/check.json (cut_shots.py --curves ใช้ต่อ จะได้ไม่ต้องอ่านไฟล์ 4K ซ้ำ)
พิมพ์ตาราง: คลิปไหน "สั่น" หรือ "นุ่ม" ให้เปลี่ยนเป็นคลิปสำรอง แล้วรันใหม่ (วัดเฉพาะคลิปที่ยังไม่เคยวัด)

เกณฑ์:
  สั่น  = jitter > 0.355 (ค่าตายตัว ใช้ได้ข้ามชุดฟุตเทจ)
  นุ่ม  = เบลอกว่าเกณฑ์ของชุด (จาก sheets/kf.json ที่ contact_sheet.py สร้าง) ถ้าไม่มีไฟล์นั้นจะไม่ตัดสินเรื่องนี้
          คลิปที่พื้นหลังละลาย (หน้าคมแต่หลังเบลอ) อาจได้ป้ายนี้ ให้ดูภาพจริงก่อนตัดทิ้ง
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agents/skills/video-understand/scripts"))
import index as ix  # noqa: E402

SHAKY = 0.355


def measure(video, tmp):
    tmp.mkdir(parents=True, exist_ok=True)
    meta = ix.probe(str(video))
    _, stats, _, _ = ix.run_passes(str(video), None, None, False, tmp)
    rows = [r for r in stats if "blur" in r and "signalstats.YAVG" in r]
    lit = [r for r in rows if 25 <= r["signalstats.YAVG"] <= 235] or rows
    ydif = [r.get("signalstats.YDIF", 0.0) for r in rows]
    n = len(rows)
    motion = sum(ydif) / max(1, n)
    jitter = (sum(abs(ydif[i] - ydif[i - 1]) for i in range(1, n)) / max(1, n - 1)) / (motion + 1.0)
    return {"clip": video.name, "len": round(meta["duration_s"], 2),
            "blur": round(sum(r["blur"] for r in lit) / max(1, len(lit)), 3), "jitter": round(jitter, 3),
            "curve": [[round(r["t"], 3), round(r.get("signalstats.YDIF", 0.0), 3)] for r in rows]}


def main():
    plan, raw, w = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out = w / "check.json"
    done = {r["clip"]: r for r in json.loads(out.read_text())} if out.exists() else {}
    clips = list(dict.fromkeys(s["clip"] for s in json.loads(plan.read_text())))
    todo = [c for c in clips if c not in done]
    with ThreadPoolExecutor(2) as ex:
        for r in ex.map(lambda c: measure(raw / c, w / "check_tmp" / Path(c).stem), todo):
            done[r["clip"]] = r
    out.write_text(json.dumps(list(done.values())))
    kf = w / "sheets" / "kf.json"
    soft_at = json.loads(kf.read_text())["soft_threshold"] if kf.exists() else None
    bad = 0
    for c in clips:
        r = done[c]
        flags = (["สั่น"] if r["jitter"] > SHAKY else []) + (["นุ่ม"] if soft_at and r["blur"] > soft_at else [])
        bad += "สั่น" in flags
        print(f"{c:<16} {r['len']:6.1f}s  blur {r['blur']:.2f}  jitter {r['jitter']:.3f}  {' '.join(flags)}")
    print(f"วัดใหม่ {len(todo)} คลิป | สั่น {bad} คลิป → {out}")


if __name__ == "__main__":
    main()
