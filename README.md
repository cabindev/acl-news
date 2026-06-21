# 🍺 Alcohol Briefing

Daily alcohol-news briefing, orchestrated by **Google Gemini**.

```
python main.py
   └─► Gemini (orchestrator.py)
          ├─► search_alcohol_news()  ← Tavily, TH + EN in parallel
          ├─► summarize_articles()   ← Gemini Flash, all articles in parallel
          │   [Gemini picks the best 5 + writes the Firefly prompt itself]
          ├─► generate_cover_image() ← Adobe Firefly → PIL logo overlay
          └─► compile_and_deliver()  ← .md + .json + Telegram
```

## Setup

```bash
bash setup.sh             # venv + deps + .env
nano .env                 # add GOOGLE_API_KEY, TAVILY_API_KEY (required)
cp your-logo.png assets/logo.png   # optional
source .venv/bin/activate
python main.py
```

## Keys

| Var | Required | Purpose |
|-----|----------|---------|
| `GOOGLE_API_KEY` | ✅ | Gemini orchestrator + summaries |
| `TAVILY_API_KEY` | ✅ | News search |
| `FIREFLY_CLIENT_ID` / `FIREFLY_CLIENT_SECRET` | ⬜ | Cover image (falls back to a local gradient cover) |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | ⬜ | Push cover + headlines via Telegram bot |

Output lands in `output/`: `briefing-YYYYMMDD.md`, `.json`, and `cover-YYYYMMDD.png`.

> **Telegram setup:** create a bot via [@BotFather](https://t.me/BotFather) to
> get `TELEGRAM_BOT_TOKEN`, send it a message, then read your chat id from
> `https://api.telegram.org/bot<TOKEN>/getUpdates`. The bot sends the cover
> image plus the headline list (HTML formatted, with links). If unset, delivery
> is skipped and the files are still written.

The pipeline degrades gracefully: without Telegram keys it still
produces the briefing files using local fallbacks.

## Google Sheet logging (optional)

Each published briefing is appended as a row to a Google Sheet via an Apps
Script Web App.

1. Open/create your Google Sheet (`https://docs.google.com/spreadsheets/d/1xwGG7Qs0yl0EyRjie8sb1iLywFjQZJDnzypBx2Ja0K4/edit?gid=0#gid=0`) → **Extensions ▸ Apps Script**.
2. Paste this code and **Save**:

   ```javascript
   function doPost(e) {
     return handleRequest(e, 'POST');
   }

   function doGet(e) {
     return handleRequest(e, 'GET');
   }

   function handleRequest(e, method) {
     const lock = LockService.getScriptLock();
     lock.waitLock(30000);
     try {
       let rowData = {};
       let cols = ["timestamp", "Title", "วันที่", "เนื้อหาข่าวที่สรุป", "ที่มาของข้อมูล", "รูปปก"];
       
       if (method === 'POST') {
         const data = JSON.parse(e.postData.contents);
         cols = data.columns || cols;
         rowData = data.row || {};
       } else if (method === 'GET') {
         rowData = e.parameter || {};
       }
       
       const ss = SpreadsheetApp.getActiveSpreadsheet();
       // Use active sheet or 'Briefings'
       const sheet = ss.getActiveSheet() || ss.getSheetByName('Briefings') || ss.insertSheet('Briefings');
       
       if (sheet.getLastRow() === 0) {
         sheet.appendRow(cols);
       }
       
       const row = cols.map(c => {
         if (c === "timestamp" && !rowData[c]) {
           return new Date().toLocaleString("th-TH");
         }
         return rowData[c] || "";
       });
       
       sheet.appendRow(row);
       return ContentService.createTextOutput(JSON.stringify({ok: true, method: method}))
         .setMimeType(ContentService.MimeType.JSON);
     } catch (err) {
       return ContentService.createTextOutput(JSON.stringify({ok: false, error: String(err)}))
         .setMimeType(ContentService.MimeType.JSON);
     } finally {
       lock.releaseLock();
     }
   }
   ```

3. **Deploy ▸ New deployment ▸ Web app** — *Execute as: Me*, *Who has access:
   Anyone* — **Deploy**, then authorize.
4. Copy the Web app URL (ends in `/exec`) into `.env`:
   `SHEET_WEBHOOK_URL=https://script.google.com/macros/s/.../exec`

Columns mapped automatically: `timestamp`, `Title`, `วันที่`, `เนื้อหาข่าวที่สรุป`, `ที่มาของข้อมูล`, `รูปปก` (and other optional fields like `region`, `kind`, `category`, `editor_note`, `express_url`). If `SHEET_WEBHOOK_URL` is unset, logging is skipped and everything else still runs.

