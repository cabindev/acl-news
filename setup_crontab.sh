#!/usr/bin/env bash
# ตั้ง crontab รัน Alcohol Briefing สัปดาห์ละครั้ง ทุกวันจันทร์
# จันทร์ 06:00 น. → ข่าวต่างประเทศ (intl)
# จันทร์ 09:00 น. → ข่าวในไทย (thai)
# จันทร์ 14:00 น. → งานศพปลอดเหล้า (funeral)

PROJECT_DIR="/Applications/MAMP/htdocs/alc-news"
PYTHON="$PROJECT_DIR/.venv/bin/python3"
LOG_DIR="$PROJECT_DIR/output/logs"

mkdir -p "$LOG_DIR"

# crontab entries ใหม่ (field สุดท้าย = วันจันทร์)
NEW_CRON="0 6 * * 1 cd $PROJECT_DIR && $PYTHON main.py intl >> $LOG_DIR/intl.log 2>&1
0 9 * * 1 cd $PROJECT_DIR && $PYTHON main.py thai >> $LOG_DIR/thai.log 2>&1
0 14 * * 1 cd $PROJECT_DIR && $PYTHON main.py funeral >> $LOG_DIR/funeral.log 2>&1"

# เพิ่มเข้า crontab (ไม่ลบของเดิม)
( crontab -l 2>/dev/null | grep -v "alc-news\|main.py"; echo "$NEW_CRON" ) | crontab -

echo "✅ ตั้ง crontab เรียบร้อย (สัปดาห์ละครั้ง ทุกวันจันทร์):"
crontab -l | grep "main.py"
echo ""
echo "Log ไฟล์:"
echo "  จันทร์ 06:00 ต่างประเทศ → $LOG_DIR/intl.log"
echo "  จันทร์ 09:00 ในไทย      → $LOG_DIR/thai.log"
echo "  จันทร์ 14:00 งานศพ      → $LOG_DIR/funeral.log"
