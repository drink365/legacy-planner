# 永傳｜數位傳承顧問（Streamlit + Supabase）

> 高資產家族的線上顧問體驗：問答式路徑模擬 → 顧問級 PDF 報告（需留 Email）→ 顧問 AI 導流預約。

---

## 🚀 快速開始（新 repo 推薦流程）

1. **建立 Supabase 專案**
   - 進入 Supabase > SQL Editor，貼上 `supabase.sql` 內容執行（建立 `leads`、`events` 兩張表）。

2. **設定 Secrets**
   - 在 Streamlit Cloud > App settings > Secrets，貼上 `.streamlit/secrets.example.toml` 的內容，並將 `url / key / api_key` 改為你的專案值。
   - 本地測試可把此檔另存為 `.streamlit/secrets.toml`。

3. **部署**
   - 將本 repo 上傳至 GitHub。
   - 於 Streamlit Cloud 連線本 repo → Deploy。

4. **測試**
   - 進入 App：
     - `Home` 首頁 → 點「開始路徑模擬」
     - 填寫問答 → 產生結果 → 輸入 Email → 下載 PDF
     - 前往 Supabase 確認 `leads` 與 `events` 有新資料

---

## 📁 專案結構

```
.
├─ Home.py                         # 首頁（權威＋CTA）
├─ pages/
│  ├─ 02_Tax_Path_Simulator.py     # 問答式傳承路徑模擬（示意版）
│  ├─ 09_Demo_Lead_and_Report.py   # Demo：以示意資料產生 PDF
│  └─ 99_Copilot.py                # 永傳顧問 AI（導向 CTA）
├─ components/
│  └─ lead_capture_and_pdf.py      # Email 留存 + 顧問級 PDF 下載
├─ src/
│  ├─ supabase_client.py           # Supabase 連線（取自 secrets）
│  ├─ repos/
│  │  └─ leads_repo.py             # leads/events 寫入查詢
│  └─ report/
│     └─ report_builder.py         # ReportLab 品牌化 PDF 產生器
├─ assets/
│  └─ logo_placeholder.png
├─ .streamlit/
│  ├─ config.toml                  # 主題色
│  └─ secrets.example.toml         # Secrets 樣板（請勿上傳真正金鑰）
├─ supabase.sql                    # 建表 SQL
├─ requirements.txt
└─ README.md
```

---

## 🔐 隱私與合規

- 請將 Supabase **Service Role Key** 僅放在 **Streamlit Secrets**，不要提交到 GitHub。
- 本 App 的計算僅為 **教育用途示意**；實際規劃以專業顧問審視為準。

---

## 🧩 如何接上你既有的試算器

在你的結果頁面結尾，呼叫：

```python
from components.lead_capture_and_pdf import lead_capture_and_pdf

lead_capture_and_pdf(
    inputs_summary=inputs_summary,
    result_summary=result_summary,
    comparisons=comparisons,
    recommendations=recommendations
)
```

即可完成：**Email 留存 → 生成品牌化 PDF → 提供下載**。

---

## 🧭 官網（Vercel）建議

- 首屏標語：**「高資產家族的數位傳承顧問」**｜**「30 年專業 × AI 智能」**
- CTA：**開始路徑模擬 → 下載顧問報告**（導到本 Streamlit App）
- 可在 `.streamlit/secrets` 設定 `brand.invite_code` 啟用邀請制下載。

---

## 🛠️ 常見問題

- **Logo 無法出現在 PDF？**  
  預設使用內建佔位圖；若你填 `brand.logo_url` 為遠端圖片，有時 ReportLab 取圖失敗會自動略過，屬正常。

- **名單沒有寫入？**  
  檢查 Streamlit Secrets 的 `supabase.url` 與 `supabase.key` 是否正確，且資料表已建立。

- **OpenAI 無回應？**  
  檢查 `openai.api_key` 與 `openai.model`；可先用 `gpt-4o-mini`。

祝上線順利！
