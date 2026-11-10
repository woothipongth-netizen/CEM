---
name: mixkit-sfx
description: ค้นหาและดาวน์โหลดเสียงเอฟเฟกต์ (SFX) และเพลงพื้นหลังจาก Mixkit ซึ่งใช้เชิงพาณิชย์ได้ ไม่ต้องใส่เครดิต ใช้เมื่อเจ้าของขอหา/เพิ่มเสียงเอฟเฟกต์ หรือสร้างคลัง SFX ของร้าน (ข้อ 7.3 ในสัมภาษณ์) ใช้แหล่ง Mixkit เท่านั้น
allowed-tools: Bash(python3 */mixkit-sfx/scripts/*)
---
# mixkit-sfx

ค้นหาและโหลด SFX จาก Mixkit อย่างเดียว (ใบอนุญาต Mixkit: ใช้ในคลิปเชิงพาณิชย์ได้ ไม่ต้องใส่เครดิต **แต่ห้ามแจกไฟล์เสียงต่อ** จึงห้าม commit ไฟล์เสียงลง repo)

```
S=${CLAUDE_SKILL_DIR}/scripts/mixkit.py
python3 -I $S search whoosh               # คำค้นภาษาอังกฤษ 1 คำ: whoosh pop click ding swoosh sparkle cash camera
python3 -I $S get <โฟลเดอร์> 1492 2019       # โหลด wav
python3 -I $S get <โฟลเดอร์> 1492=whoosh-short.mp3   # โหลดแล้วแปลงเป็น mp3 ตั้งชื่อเอง
python3 -I $S music happy                 # เพลงพื้นหลังตามอารมณ์/แนว: happy calm elegant energetic upbeat chillout dreamy
python3 -I $S getmusic <โฟลเดอร์> 839       # โหลดเพลง (mp3)
```
เพลง: ใช้เมื่อคลังเพลงของร้านไม่มีเพลงที่เข้ากับคลิป แล้วเลือกด้วย `scripts/music_index.py` ตาม [docs/04-workflow.md](../../../docs/04-workflow.md) ขั้น 5

## ใช้เมื่อไหร่
- **สร้างคลัง SFX ของร้าน (ครั้งเดียว):** ค้นเสียงที่ใช้บ่อย ส่งลิงก์ฟังตัวอย่าง (คอลัมน์สุดท้าย) ให้เจ้าของเลือก
  โหลดลง `work/sfx-library/` แล้วบอกเจ้าของอัปโหลดเข้าโฟลเดอร์คลัง SFX ใน Drive ของร้าน (`brand.json` → `sfx_library`)
  ไฟล์เสียงส่งในแชทได้ (ตัวเชื่อม Drive อัปไฟล์ใหญ่ไม่ได้ แต่ SFX ไฟล์เล็ก ลองอัปผ่านตัวเชื่อมได้)
- **ในงานตัดคลิป:** ใช้ไฟล์จากคลังของร้านก่อนเสมอ ค้น Mixkit เฉพาะเมื่อเจ้าของขอเสียงใหม่
- ใช้กับ `scripts/mix_audio.sh`: ตั้งชื่อ `whoosh-short.mp3` (เปลี่ยนช่วง) และ `sparkle.mp3` (ตอนจบ) แล้วรันด้วย `SFX_DIR=<โฟลเดอร์>`

## ข้อจำกัด
- ต้องเปิดเว็บ `mixkit.co` และ `assets.mixkit.co` ใน environment (ทดสอบแล้วใช้ได้)
- ห้ามเพิ่มแหล่งอื่นในสคริปต์นี้ (Pixabay ต้องหลบระบบกันบอท, Freesound บล็อกเครื่อง cloud, Kenney โหลดอัตโนมัติไม่ได้)
- เพลง: ใช้ได้เฉพาะ Mixkit ตามกฎเพลงใน CLAUDE.md ห้ามหาเพลงจากเว็บอื่น
