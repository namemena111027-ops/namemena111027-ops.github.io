# Lucius Rhinesonus — 個人作品集網站

從理解，開始設計。這個網站收錄 UI／UX 案例研究、可以實際操作的互動原型，以及網站本身的設計與實作紀錄。

網站：<https://namemena111027-ops.github.io>

## 頁面

| 檔案 | 內容 |
| --- | --- |
| `index.html` | 首頁：精選作品、UX 互動實驗室（線索工作台、預約 A／B 原型）、UX 學習報告、關於我 |
| `work-booking.html` | 案例 01：預約修改流程設計（A／B 互動原型、測試規劃、修改紀錄） |
| `work-fridge.html` | 案例 02：共享冰箱資訊辨識（情境模擬、標籤方案、正式研究規劃） |
| `work-site.html` | 案例 03：個人網站視覺與互動系統（設計系統、c 型連續圓角、動效規格、無障礙、測試） |
| `process.html` | 版本時間軸、除錯紀錄（28 筆）、測試紀錄、AI 協作分工 |

## 技術

- 靜態網站，每頁一個 HTML 檔：CSS、JavaScript 與圖片都內嵌在檔案裡，不使用框架，也沒有建置步驟。
- c 型連續圓角：JavaScript 依每個元件的實際像素尺寸產生 `clip-path: path()`，尺寸改變時才重算（說明見 `work-site.html#radius`）。
- 部署：GitHub Pages，`main` 分支根目錄。

## 研究與測試狀態

這些狀態在網站上也逐一標示：

- 預約原型：原型完成，**尚未進行使用者測試**；網站上沒有任何測試數據。
- 冰箱案例：情境推演與劇本式模擬（未標記時第三盒才找到是預設規則），**不是實際測試結果**。
- 自動化測試：Playwright（Chromium）。實機測試：iPhone Safari（V1–V12，由 Lucius 錄影回報）；V2.0 待實機驗收；iPad Safari、Android Chrome、macOS Safari、Edge 尚未測試。
- Core Web Vitals 尚未量測。

## 測試

`tests/` 內是 V2.0 使用的兩個檢查程式（需要 Python 3 與 Playwright）：

- `tests/motion_diff.py old.html new.html`：從兩個版本讀出所有 transition、animation、@keyframes 與 JavaScript 動畫設定，逐項比對。V2.0 的結果：187 項全部相同。
- `tests/v2_test.py index.html`：預約狀態與操作紀錄、練習計分與重設、鍵盤與焦點、對話框等 100 項功能測試。

## 協作

程式由 AI（Anthropic 的 Claude）依需求撰寫；問題與需求、設計方向、實機測試與驗收由 Lucius 負責。完整分工見 `process.html#ai`。

## 動效保護原則

V2.0 只修改內容、資訊架構、功能邏輯與無障礙，不更動任何既有動效（持續時間、曲線、模糊、位移、c 型圓角、展開收合、觸發時機）。
