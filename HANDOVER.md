# NK1 交接包（M6.0）

> 給接手者（數位經理）的入口頁。先讀本頁，再依序讀 `RUNBOOK.md` → `ENVIRONMENT.md` → `DATA.md` → `OPEN_ITEMS.md` → `docs/DECISIONS_摘要.md`。
> 依據：Alex 2026-10-02 裁定 NK1 開發由數位經理接手（見 `memory/decisions.md` 2026-10-02 M6.0）。

## 凍結點

| 項目 | 值 |
|---|---|
| 版本標籤 | `v0.10-handover`（annotated tag） |
| 標籤指向 | `87686b6`（main；v0.10 機制展示版，之後的 commit 只加交接文件） |
| 測試 | **142 項**，`python3 -m unittest discover -s tests` 全過（零依賴 unittest，**不是 pytest**） |
| 守衛 | `scripts/nk1-guard.sh` 七道（commit 前）＋第 8 道 `scripts/nk1-inbound.sh`（合併回送前） |
| NK1 記憶包 | 凍結點當下 sha256 前12 `3255f5c0bf5e`（源頭 hash `f1d29e60bcb7`）；之後每次 commit 會重產，以檔頭為準 |
| 草稿現況 | v0.10＝機制展示版（逐句內容閘 30 節攔 26），**不是可讀草稿**；LC 模板到後重建骨架再生成 |

## 未結 U／J（細節見 `OPEN_ITEMS.md`）

- **U 未結**：U4（LC 模板取得）、U5（阿析介面）、U6（硬體與樂迦主機；開發機已定，樂迦端部署主機另案）、U7（A5／G1 書面）、U9（本地模型環境）、U10（樂迦三樣）、U11（條號表認可）、U12（設備資料表欄位）。
- **U 已關**：U1（回薄管線）、U2（prompt＝三顧人寫）、U3（合約閘關閉，10/02）、U8（薄管線 v0.2 定版、本體延 v2）。
- **J**：J-01～J-17 皆未判定為通過；J-09 僅驗證器側過；J-13 9/28 暫判已撤回；J-14 判準改為品保七項；J-16 判定時點改為 LC 模板確定後。

## 真相與寫入權（Alex 2026-10-02 裁，交接前後不變）

- **真相永遠＝Alex 的 GitHub**（private repo，`main`）。
- **唯一寫入者＝阿K**（以 nk1 專用 deploy key push）。交接前後不變。
- **數位經理不持任何 GitHub 憑證。** 在內網主機開發，改動以 `git bundle`（或 `git format-patch`）回送到阿K 的 `~/ak-inbox/nk1-in/`。
- 阿K 收件流程：`scripts/nk1-inbound.sh <bundle>` → 自 bundle `git fetch` 到 `refs/inbound/*` → **第 8 道守衛**（diff 與 commit 作者／訊息不得含 `~/nk1-data` 內容、人名、信箱、IP；人名另比對 repo 外 `~/nk1-data/names.txt`，缺席＝fail-closed）＋ 全部測試 ＋ 守衛七道 → **過了才合進 main 並 push**；不過就退件、不合。
- **每次合併後重出 bundle** 給數位經理，她以 `git pull` 自新 bundle 對齊。
- 走的介質：加密介質或內網，**不走任何雲端**（含雲端硬碟、Email 附件、聊天軟體）。

### 數位經理回送改動（在內網主機）

```bash
# 只送 main 上、她手上有而上一版交付 bundle 沒有的 commit
git bundle create nk1-return-$(date +%Y%m%d-%H%M).bundle v0.10-handover..main
sha256sum nk1-return-*.bundle > nk1-return.sha256
# 或：git format-patch v0.10-handover..main -o nk1-return-patches/
```

📌 起點請用「上一次收到的交付 bundle 的 tip」（第一次＝`v0.10-handover`，之後依阿K 每次交付附的 tag）。
📌 commit 作者請設**職位與無效網域**，不設本名與真信箱（第 8 道會擋）：
`git config user.name "數位經理"`；`git config user.email "nk1-dev@nk1.invalid"`。

## 拿到 bundle 之後（接手者）

```bash
# 1. 驗 sha（值見同介質上的 .sha256 檔，與阿K 回報對一次）
sha256sum -c nk1-handover-v0.10-handover.bundle.sha256
# 2. 驗 bundle 完整
git bundle verify nk1-handover-v0.10-handover.bundle
# 3. clone
git clone -b main nk1-handover-v0.10-handover.bundle nk1-generator
cd nk1-generator && git tag -l      # 應含 v0.10-handover
# 4. 之後收到新 bundle：
git pull /路徑/新的.bundle main
```

⚠️ bundle **只含 `main` 與 tags**，不含本機封存分支（`archive/pre-M5.8` 含真文件編號與原稿檔名，永不外流）。

## 交接完成的判準（接手者自己跑、自己回報；阿K 不代跑）

`scripts/handover-check.sh` 三項：① 142 項測試全過 ② 守衛全過 ③ 以合成資料完成一次離線生成（全程監看零外連）。
③ 需模型，只能在內網主機跑（主機清空與管理者交接完成後、依 `ENVIRONMENT.md` 安裝之後）。**三項未全過＝交接未完成。**

## 不隨 bundle 交付、另走通道

見 `DATA.md`：三顧模板語料、遮蔽真清單（denylist）、代號對照表——與 bundle 同介質、**分開加密**；交付範圍待 Alex 裁 H5。樂迦側 16 份依 10-2 另案。
⚠️ 守衛 ③ 的文件編號閘在代號對照表缺席時 **fail-closed**——對照表未交付前，接手者機器上守衛 ③ 會 FAIL，這是設計，不是壞掉。
