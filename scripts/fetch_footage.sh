#!/usr/bin/env bash
# ดึงฟุตเทจจาก Google Drive และทำไฟล์เฟรมหลัก (720p) ทันทีที่แต่ละไฟล์โหลดเสร็จ
#
# ใช้: scripts/fetch_footage.sh <ids.txt> <โฟลเดอร์งาน>
#   ids.txt บรรทัดละ "<ชื่อไฟล์> <Drive file id>" (เหมือน drive_download.sh)
# ผลลัพธ์: <งาน>/raw/ (ไฟล์ต้นฉบับ 4K), <งาน>/kf/ (เฟรมหลัก 720p สำหรับดูภาพรวม)
#          <งาน>/.fetch_done เมื่อเสร็จทุกไฟล์ (ใช้รอแทนการเช็กชื่อ process)
#
# ทำไมเฟรมหลัก: ไฟล์ 4K ถอดรหัสทุกเฟรมช้ามาก (~13 นาที / 64 คลิป) การอ่านเฉพาะเฟรมหลัก
# (-skip_frame nokey) ใช้ ~1 นาที ภาพพอให้เลือกช็อตตามเนื้อหาและวัดความคมได้
# แต่ "วัดกล้องสั่นไม่ได้" ต้องวัดละเอียดเฉพาะคลิปที่เลือกด้วย check_shots.py อีกที
set -euo pipefail
IDS="$1"; W="$2"
mkdir -p "$W/raw" "$W/kf"
rm -f "$W/.fetch_done"
xargs -P 4 -L 1 sh -c '
  curl -sSL --retry 3 -m 1800 -o "'"$W"'/raw/$0" \
    "https://drive.usercontent.google.com/download?id=$1&export=download&confirm=t" || { echo "FAIL $0"; exit 0; }
  ffmpeg -v error -y -skip_frame nokey -i "'"$W"'/raw/$0" -vf scale=720:-2 -fps_mode passthrough \
    -an -c:v libx264 -preset ultrafast -crf 23 "'"$W"'/kf/${0%.*}.mp4" && echo "ok   $0"
' < "$IDS"
touch "$W/.fetch_done"
echo "ดาวน์โหลดแล้ว: $(ls "$W/raw" | wc -l) ไฟล์, $(du -sh "$W/raw" | cut -f1)"
