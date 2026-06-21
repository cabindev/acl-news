#!/usr/bin/env bash
# ตั้ง crontab รัน Alcohol Briefing วันละ 2 ครั้ง
# 06:00 น. → ข่าวต่างประเทศ (intl)
# 09:00 น. → ข่าวในไทย (thai)

PROJECT_DIR="/Applications/MAMP/htdocs/alc-news"
PYTHON="$PROJECT_DIR/.venv/bin/python3"
LOG_DIR="$PROJECT_DIR/output/logs"

mkdir -p "$LOG_DIR"

# crontab entries ใหม่
NEW_CRON="0 6 * * * cd $PROJECT_DIR && $PYTHON main.py intl >> $LOG_DIR/intl.log 2>&1
0 9 * * * cd $PROJECT_DIR && $PYTHON main.py thai >> $LOG_DIR/thai.log 2>&1"

# เพิ่มเข้า crontab (ไม่ลบของเดิม)
( crontab -l 2>/dev/null | grep -v "alc-news\|main.py"; echo "$NEW_CRON" ) | crontab -

echo "✅ ตั้ง crontab เรียบร้อย:"
crontab -l | grep "main.py"
echo ""
echo "Log ไฟล์:"
echo "  06:00 ต่างประเทศ → $LOG_DIR/intl.log"
echo "  09:00 ในไทย      → $LOG_DIR/thai.log"
