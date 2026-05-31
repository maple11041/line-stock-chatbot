# 台股抽籤 LINE 自動通知機器人

這個專案每天抓取臺灣證券交易所「公開申購公告-抽籤日程表」，整理成 LINE 訊息，推播到指定家族 LINE 群組。預設通知：

- 今日抽籤案件
- 今日仍可申購案件
- 排除中央登錄公債，只保留台股相關公開申購

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

已建立 `.github/workflows/daily-line-notify.yml`，每天台北時間 07:30 執行一次。

請到 GitHub repo 的 `Settings > Secrets and variables > Actions` 新增：

- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_TO_ID`

也可以手動從 Actions 頁面執行 `Daily LINE stock subscription notify` workflow。手動執行時，即使當天沒有案件，也會推播一則訊息供測試；每日排程則只在有案件時推播。

## 可用環境變數

- `TARGET_DATE`：指定日期，格式 `YYYY-MM-DD`
- `DRY_RUN`：設為 `true` 時只印出訊息不推播
- `SEND_EMPTY`：設為 `true` 時，即使當天沒有案件也推播
- `INCLUDE_BONDS`：設為 `true` 時納入中央登錄公債

## 資料來源

臺灣證券交易所公開申購公告：

`https://www.twse.com.tw/announcement/publicForm?response=json&yy=2026`
