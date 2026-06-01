# 台股抽籤 LINE 自動通知機器人

這個專案每天抓取臺灣證券交易所「公開申購公告-抽籤日程表」，整理成 LINE 訊息，推播到指定家族 LINE 群組。預設通知：

- 今日仍在申購期間且溢價率大於 20% 的案件
- 最新收盤價、溢價率，以及目前累積筆數估算的動態即時中籤率
- 排除中央登錄公債，只保留台股相關公開申購
- 申購截止日晚間 20:30 發送預估中籤率賽況

## 環境需求

- Python 3.11+
- uv
- LINE Messaging API channel access token
- 要推播的 LINE 群組 ID 或使用者 ID

## 本機執行

```bash
uv sync
uv run line-stock-chatbot --dry-run
```

指定日期測試：

```bash
uv run line-stock-chatbot --date 2026-06-05 --dry-run
```

包含公債：

```bash
uv run line-stock-chatbot --include-bonds --dry-run
```

指定日期測試晚間賽況預報：

```bash
uv run line-stock-forecast --date 2026-05-29 --dry-run
```

## LINE 設定

複製 `.env.example` 為 `.env` 後填入：

```bash
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_TO_ID=your_group_or_user_id
```

`LINE_TO_ID` 可以是個人 ID 或群組 ID。個人 ID 通常以 `U` 開頭，群組 ID 通常以 `C` 開頭。取得 ID 的做法是開啟 webhook，讓目標使用者或群組發一則訊息，再從 webhook event 裡的 `source.userId` 或 `source.groupId` 取得。

### 取得 LINE userId / groupId

本專案提供一個 debug webhook server，可以把 LINE webhook 收到的來源 ID 印出來。

啟動本機 server：

```bash
uv run line-webhook-debug
```

另開一個終端機，用 ngrok 或 Cloudflare Tunnel 暴露本機 `8000` port，例如：

```bash
ngrok http 8000
```

到 LINE Developers Console 的 Messaging API channel 設定：

- `Use webhook`：Enabled
- `Webhook URL`：`https://你的公開網址/callback`

按下 Verify 或直接用 LINE 傳訊息給 bot。終端機會印出：

```text
source.userId: Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
source.groupId: Cxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

把要推播的那個 ID 放進 `.env` 的 `LINE_TO_ID`。

正式推播：

```bash
LINE_CHANNEL_ACCESS_TOKEN=xxx LINE_TO_ID=yyy uv run line-stock-chatbot
```

## GitHub Actions 部署

已建立兩個 workflow：

- `.github/workflows/daily-line-notify.yml`：每天台北時間 08:30 發送每日摘要
- `.github/workflows/evening-line-forecast.yml`：每天台北時間 20:30 發送申購截止賽況

請到 GitHub repo 的 `Settings > Secrets and variables > Actions` 新增：

- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_TO_ID`

也可以手動從 Actions 頁面執行 workflow。早上摘要即使沒有符合條件的案件，也會推播一則訊息，方便確認排程正常運作。晚間賽況在手動執行時也會推播測試訊息。

## 晚間賽況預報

每天台北時間 20:30，機器人會找出當天截止申購且申購總筆數大於 0 的股票，發送預估中籤率。

計算方式：

```text
承銷張數 = 實際承銷股數 / 1,000
預估中籤率 = 承銷張數 / 申購總筆數 * 100%
```

TWSE 公開申購表的截止日晚間申購筆數尚未更新，因此預報使用：

- TWSE 公開申購公告：申購日程、實際承銷股數
- 撿股讚公開彙整頁：截止日晚間申購總筆數

預報是參考值，實際中籤率以 TWSE 後續公告為準。

## 動態即時中籤率

每天台北時間 08:30 的摘要只列出仍在申購期間且溢價率大於 20% 的股票。溢價率依最新收盤價計算：

```text
溢價率 = (最新收盤價 - 承銷價) / 承銷價 * 100%
```

摘要也會讀取目前公開彙整的申購總筆數。當累積筆數大於 0 時，訊息會顯示動態即時中籤率：

```text
動態即時中籤率 = 承銷張數 / 目前累積申購總筆數 * 100%
```

申購總筆數會持續累積，因此這個數字會隨申購進度變動。實際中籤率仍以 TWSE 後續公告為準。

## 可用環境變數

- `TARGET_DATE`：指定日期，格式 `YYYY-MM-DD`
- `DRY_RUN`：設為 `true` 時只印出訊息不推播
- `SEND_EMPTY`：設為 `true` 時，即使當天沒有案件也推播
- `INCLUDE_BONDS`：設為 `true` 時納入中央登錄公債

## 資料來源

臺灣證券交易所公開申購公告：

`https://www.twse.com.tw/announcement/publicForm?response=json&yy=2026`

撿股讚公開申購彙整：

`https://stock.wespai.com/draw`
