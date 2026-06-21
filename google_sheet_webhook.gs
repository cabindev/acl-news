/**
 * CivicSpace Alcohol Briefing — Google Sheet webhook (self-contained)
 *
 * รับข้อมูลจาก pipeline (POST JSON {columns:[...], row:{...}}) แล้ว append เป็นแถว
 * ใช้คู่กับ tools/sheets.py
 *
 * ติดตั้ง: วางโค้ด "ทั้งไฟล์" ใน Apps Script editor → Save →
 *   Deploy ▸ Manage deployments ▸ ✏️ ▸ Version: New version ▸ Deploy
 *   (Execute as: Me, Who has access: Anyone)
 */

function doPost(e) {
  return handleRequest(e, 'POST');
}

function doGet(e) {
  return handleRequest(e, 'GET');
}

function handleRequest(e, method) {
  var SHEET_NAME = 'Briefings';
  var DEFAULT_COLUMNS = [
    'timestamp', 'Title', 'วันที่', 'เนื้อหาข่าวที่สรุป', 'ที่มาของข้อมูล', 'รูปปก',
    'region', 'kind', 'category', 'editor_note', 'express_url'
  ];

  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var cols = DEFAULT_COLUMNS;
    var rowData = {};

    if (method === 'POST' && e && e.postData && e.postData.contents) {
      var data = JSON.parse(e.postData.contents);
      if (data.columns && data.columns.length) cols = data.columns;
      rowData = data.row || {};
    } else if (e && e.parameter) {
      rowData = e.parameter;
    }

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);

    if (sheet.getLastRow() === 0) {
      sheet.appendRow(cols);
    } else {
      // keep header in sync when new columns are added
      var header = sheet.getRange(1, 1, 1, Math.max(sheet.getLastColumn(), 1)).getValues()[0];
      if (header.length < cols.length) {
        sheet.getRange(1, 1, 1, cols.length).setValues([cols]);
      }
    }

    var row = cols.map(function (c) {
      if (c === 'timestamp' && !rowData[c]) {
        return Utilities.formatDate(new Date(), 'Asia/Bangkok', 'yyyy-MM-dd HH:mm:ss');
      }
      return rowData[c] != null ? rowData[c] : '';
    });

    sheet.appendRow(row);
    var lastRow = sheet.getLastRow();

    // ฝังรูปการ์ดลงคอลัมน์ "รูปปก" ถ้าส่ง base64 มา
    var imgEmbedded = false;
    if (method === 'POST' && e.postData) {
      var payload = JSON.parse(e.postData.contents);
      var colIdx = cols.indexOf('รูปปก') + 1;
      if (payload.card_base64 && colIdx > 0) {
        var bytes = Utilities.base64Decode(payload.card_base64);
        var blob = Utilities.newBlob(bytes, 'image/png', 'card.png');
        sheet.getRange(lastRow, colIdx).clearContent();   // ลบ path เดิม
        var img = sheet.insertImage(blob, colIdx, lastRow);
        img.setWidth(120).setHeight(150);
        sheet.setRowHeight(lastRow, 160);
        imgEmbedded = true;
      }
    }

    return ContentService
      .createTextOutput(JSON.stringify({ ok: true, method: method, appended: row.length, image: imgEmbedded }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}
