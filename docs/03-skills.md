# 3. Skills: มีอะไร เก็บที่ไหน

## เก็บไว้ที่ไหน

```
.agents/skills/<ชื่อ skill>/     ← ตัวจริง (SKILL.md + scripts + references)
.claude/skills/<ชื่อ skill>      ← symlink ชี้ไปที่ .agents/skills/<ชื่อ> ให้ Claude Code มองเห็น
skills-lock.json                 ← เวอร์ชันของชุด HyperFrames
```

skill อยู่ใน repo แล้ว **เครื่องใหม่ไม่ต้องติดตั้ง skill ซ้ำ** เปิดแชทกับ repo นี้ก็พร้อมใช้
สิ่งที่ต้องติดตั้งใหม่ทุกครั้งคือ "โปรแกรม" ที่ skill เรียกใช้ ซึ่ง `scripts/setup.sh` ทำให้

## skill ที่มีมาให้ (ใช้จริงทั้ง 6 ตัว)

| skill | ที่มา | ใช้ทำอะไรในงานนี้ |
|---|---|---|
| `hyperframes` | heygen-com/hyperframes | กฎหลักการทำวิดีโอด้วย HTML |
| `hyperframes-cli` | heygen-com/hyperframes | คำสั่ง lint / snapshot / render |
| `hyperframes-registry` | heygen-com/hyperframes | ที่มาของทรานสิชันและโมชั่นในเทมเพลต `review-motion` |
| `media-use` | heygen-com/hyperframes | เสียงเอฟเฟกต์ whoosh / sparkle (**ห้ามใช้สร้างเพลง**) |
| `video-understand` | ชุดเพิ่มเติม | คัดฟุตเทจ ให้คะแนนความคม ความนิ่ง แสง (`cull.py`) |
| `mixkit-sfx` | ของเราเอง (ดัดแปลงจาก `sxhzju/sfx`, MIT) | หา/โหลดเสียงเอฟเฟกต์จาก Mixkit (ใช้เชิงพาณิชย์ได้ ไม่ต้องใส่เครดิต) ไว้สร้างคลัง SFX ของร้าน · ต้องเปิดเว็บ `mixkit.co`, `assets.mixkit.co` ([02-setup.md](02-setup.md) ขั้นที่ 3) · ห้าม commit ไฟล์เสียง |

## ติดตั้ง skill เพิ่ม (ถ้าต้องการ)

**จาก GitHub:**
```bash
npx -y skills add <owner>/<repo> --all
```
ตัวติดตั้งวางไฟล์ใน `.agents/skills/` และสร้าง symlink ใน `.claude/skills/` ให้เอง
(ชุด HyperFrames ทั้งหมดมีอีกหลายตัว เช่น `slideshow` `figma` ติดตั้งด้วย `npx -y skills add heygen-com/hyperframes --all`)

**จากไฟล์ zip:**
1. อัป zip ขึ้น Google Drive แล้วส่งลิงก์ให้ Claude
2. Claude ดาวน์โหลด แตกไฟล์ **อ่านโค้ดข้างในก่อน** (skill รันด้วยสิทธิ์เต็ม) แล้ววางใน `.agents/skills/<ชื่อ>/`
3. สร้าง symlink: `ln -s ../../.agents/skills/<ชื่อ> .claude/skills/<ชื่อ>`
4. commit แล้ว PR เข้า `main`

## skill ที่ลองแล้วแต่ไม่ได้ใส่มา
- `embedded-captions`: รับเฉพาะคลิปคนพูดหน้ากล้องช็อตเดียว ใช้กับคลิปเสียงพากย์หลายช็อตไม่ได้
- `music-to-video`, `faceless-explainer`: งานคนละแบบ ไม่ได้ใช้
