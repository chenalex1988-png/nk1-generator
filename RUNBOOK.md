# NK1 RUNBOOK — 從 clone bundle 到一次離線生成

> 對象：接手者（數位經理）在**內網主機**（Linux aarch64）。macOS 對應寫法附在括號內。
> 🔴 **主機清空與管理者交接完成前，不裝任何東西**（見 `ENVIRONMENT.md`）。
> 每步都附：指令、預期輸出、常見失敗。指令在 repo 根目錄跑，除非另註。
> ⚠️ 本檔的生成指令以 Air2 實跑過的 M5.x 流程寫成；**在 Linux aarch64 上一次都還沒跑過**，首跑的差異請回送阿K 修本檔。

---

## §0 前置條件

| 條件 | 怎麼確認 | 缺了會怎樣 |
|---|---|---|
| 主機清空、管理者交接完成 | 數位經理回報 | 不得開始 |
| git ≥ 2.30、python3 ≥ 3.9、`lsof`、`zstd` | `git --version; python3 -V; which lsof zstd` | `lsof` 缺＝監看器無法取樣（零外連無從證明）；`zstd` 缺＝解不開 Ollama 包 |
| repo 外資料（`~/nk1-data/`）依 H5 交付範圍到位 | 見 `DATA.md` | 守衛 ③⑤ fail-closed；生成缺骨架 |

## §1 驗 bundle 並 clone

```bash
sha256sum -c nk1-handover-v0.10-handover.bundle.sha256      # (macOS: shasum -a 256 -c)
git bundle verify nk1-handover-v0.10-handover.bundle
git clone -b main nk1-handover-v0.10-handover.bundle ~/nk1-generator
cd ~/nk1-generator && git log --oneline -1 && git tag -l
git config user.name "數位經理"; git config user.email "nk1-dev@nk1.invalid"
```
- **預期**：`…bundle: OK`；`The bundle records a complete history.` 或 `The bundle requires…`（後者＝增量 bundle，要先有前一版）；`git tag -l` 含 `v0.10-handover`。
- **常見失敗**：sha 不符 → 介質損毀或檔案被換，**停，不要 clone**，回報阿K；`does not look like a v2 or v3 bundle file` → 檔案不完整。

收到後續 bundle 時：
```bash
git remote set-url origin /路徑/新的.bundle && git fetch origin && git merge --ff-only origin/main
```
- **常見失敗**：`Not possible to fast-forward` → 本地有尚未回送的 commit，先回送（`HANDOVER.md`「回送改動」），等阿K 合進下一版 bundle。

## §2 Python 環境（測試零依賴；渲染需 docxtpl）

```bash
python3 -m unittest discover -s tests          # 系統 python 即可跑（渲染測試會略過）
```
- **預期**：`Ran 142 tests … OK`。未建 `.venv` 時以系統 python 跑為 `OK (skipped=2)`（2 項需 docxtpl 的渲染測試自動略過）；交接判準以 `.venv/bin/python` 跑、**0 skipped** 為準。

渲染相依（docxtpl 等 6 個 wheel）**離線安裝**：
```bash
# 在有網路的機器先下載（平台綁定 wheel 換機要重取，見 ENVIRONMENT.md §3）
python3 -m venv .venv
.venv/bin/pip install --no-index --find-links /路徑/wheels --require-hashes -r requirements-docx.linux-aarch64.txt
```
- 🔴 `requirements-docx.txt` 是 **macOS arm64＋Python 3.9** 的鎖檔；Linux aarch64 要依 `ENVIRONMENT.md` §3 重產 `requirements-docx.linux-aarch64.txt`（`--require-hashes` 只認列出的 wheel）。
- **常見失敗**：`THESE PACKAGES DO NOT MATCH THE HASHES` → wheel 平台或版本不對；`No matching distribution` → wheel 目錄缺檔。

## §3 守衛（commit 前必跑）

```bash
bash scripts/nk1-guard.sh && git commit …        # 一律用 &&：守衛沒過就不會 commit
```
- **預期**：最後一行 `🟢 七道全過，可以 commit`。
- 七道：① 無 untracked docx／pdf／xlsx ② data/ 隔離與大檔 ③ 遮蔽閘＋文件編號閘 ④ 記憶包跟上源頭 ⑤ T-spec 原句洩漏 ⑥ 句子閘 ⑦ 對 origin ahead-behind。
- **常見失敗**：
  - ③ `代號對照表不存在（fail-closed）` → `~/nk1-data/refs/doc-codes.tsv` 未交付（H5）。**這是設計**，不要改閘。
  - ③ `遮蔽閘【拒絕】` → diff 有命中，**改內容**，不要改清單。
  - ④ `源頭已變但包未重產` → 跑 §9 產包後再 commit。
  - ⑤ `語料目錄不存在` → `~/nk1-data/templates` 未交付（H5）。
  - ⑦ `落後 origin` → 先 §1 對齊新 bundle。
- 🔴 不用 `git add -A`，只 add 明列路徑。

## §4 Ollama 離線安裝（Linux aarch64）

在有網路的機器下載並驗 sha（值見 `ENVIRONMENT.md` §2）：
```bash
curl -fLO https://github.com/ollama/ollama/releases/download/v0.34.4/ollama-linux-arm64.tar.zst
sha256sum ollama-linux-arm64.tar.zst      # 須＝96f50a1192133028cf4e010d8c333f8af14b1505db6be7b2034c11487e7fd7e6
```
經加密介質／內網搬到主機後：
```bash
sha256sum ollama-linux-arm64.tar.zst      # 再驗一次（搬運後）
mkdir -p ~/ollama && tar --zstd -C ~/ollama -xf ollama-linux-arm64.tar.zst
~/ollama/bin/ollama --version             # 預期：client version is 0.34.4（未起 serve 時另有 warning，正常）
```
- 🔴 **不要**用官方 `curl … | sh` 安裝腳本（會連網、會裝成 systemd 常駐服務並自動啟動；本線律＝平時停、要用再起）。
- 🔴 不設 `OLLAMA_HOST`（預設綁 127.0.0.1:11434）。
- **常見失敗**：`tar: zstd: Cannot exec` → 裝 `zstd`；GPU 未被用到（serve log 只見 CPU）→ 見 `ENVIRONMENT.md` §4 CUDA 待查項。

## §5 模型（qwen3.5:9b）離線搬運

Air2 上的模型：`qwen3.5:9b`，Q4_K_M，6,594,474,711 bytes，digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`。
搬運＝manifest 加其引用的 blobs，放進主機的 `OLLAMA_MODELS` 目錄（預設 `~/.ollama/models`）：
```bash
# 來源機：列出 manifest 引用的 blob（digest），連同 manifest 一起搬
cat ~/.ollama/models/manifests/registry.ollama.ai/library/qwen3.5/9b
# 主機：放回同樣相對路徑後
~/ollama/bin/ollama list                  # 預期 NAME qwen3.5:9b、ID 6488c96fa5fa
```
- **常見失敗**：`ollama list` 沒有該模型 → manifest 路徑層級錯；ID 不是 `6488c96fa5fa` → 搬錯檔，**不要用**。
- 📌 9B 之上的模型選型待 LC 模板到、骨架重建後再定（主機 128 GB，原「僅 9B」限制已解除，但未選型）。

## §6 一次離線生成（監看先起、模型後起；結束先停模型、後停監看）

> 律（Alex 2026-09-27 裁）：`OLLAMA_NO_CLOUD=1`＋**自程序啟動前到停止後的全程監看**。設定值不是證據，監看才是。

```bash
W=~/nk1-data/netwatch/run-$(date +%Y%m%d-%H%M%S); mkdir -p "$W"
python3 scripts/nk1-netwatch.py watch --log "$W/log.jsonl" --stop-file "$W/STOP" &      # 1 先起監看
python3 scripts/nk1-netwatch.py mark --phases "$W/phases.jsonl" "serve 啟動"
OLLAMA_NO_CLOUD=1 ~/ollama/bin/ollama serve > "$W/serve.log" 2>&1 &                     # 2 後起模型
SERVE=$!; sleep 5; grep -i "cloud disabled" "$W/serve.log"                               #   預期：Ollama cloud disabled: true
python3 scripts/nk1-netwatch.py mark --phases "$W/phases.jsonl" "生成"
.venv/bin/python scripts/nk1-gen.py \
  --intake fixtures/intake_synth_v0.6.json --intake-spec specs/intake_v0.6.yaml \
  --section-uses specs/guards/section_uses_T027.yaml \
  --skel ~/nk1-data/skel/<T027>/fbad2c5b.v0.7.yaml \
  --guides specs/guides/T027_v0.7.yaml --refs specs/refs/annex15_v1.json \
  --model qwen3.5:9b --out-dir ~/nk1-data/gen/handover --report /tmp/nk1-handover-report.md \
  --inbox ~/nk1-data/gen/handover-inbox                                                  # 3 生成（預設跑 2 輪）
python3 scripts/nk1-netwatch.py mark --phases "$W/phases.jsonl" "停 ollama"
kill -TERM $SERVE; wait $SERVE                                                           # 4 先停模型
sleep 5; touch "$W/STOP"; wait                                                           # 5 後停監看
python3 scripts/nk1-netwatch.py summary --log "$W/log.jsonl" --phases "$W/phases.jsonl" --md   # exit 0＝全段零外連
```
- **預期**：生成結束印兩輪 docx／內容包 sha 相同；`summary` 各分段「非本機端點」皆 **0**、exit 0。產物只在 `--out-dir`（repo 外）。
- `<T027>` 為骨架所在資料夾（代號對照見 repo 外對照表）；**骨架交付與否待 Alex 裁**（`OPEN_ITEMS.md` H5／骨架項）。
- 🔴 `--report` 指向 repo 外；要收進 repo 的報告只放統計（零正文）。
- **常見失敗**：
  - `🔴 模型不存在` → §5 未完成或 serve 未起。
  - `KeyError`／`StopIteration` 出在 `guide_for` → 骨架版本與指引句版本不對（指引 v0.7 對骨架 `fbad2c5b.v0.7`）。
  - `summary` exit 1（有非本機端點）→ **立刻停**，不重跑，回報 Alex；這是 2026-09-27 事件的同型。
  - 監看取不到任何 ollama 程序 → `lsof` 權限不足（以同一使用者跑 serve，或監看以 sudo 跑）；**看不到≠沒連**，不得當作零外連。

## §7 重掃／重渲染（不需模型）

```bash
# 以現行閘重掃既有生成（只出統計）
python3 scripts/nk1-recheck-v2.py --gen-dir ~/nk1-data/gen/<run> --skel <骨架.yaml> \
  --intake fixtures/intake_synth_v0.6.json --intake-spec specs/intake_v0.6.yaml \
  --section-uses specs/guards/section_uses_T027.yaml --refs specs/refs/annex15_v1.json
# 重渲染（引用搬審閱層、加參考資料節、出 review_map）
.venv/bin/python scripts/nk1-rerender.py --gen-dir ~/nk1-data/gen/<run> --skel <骨架.yaml> \
  --refs specs/refs/annex15_v1.json --intake fixtures/intake_synth_v0.6.json \
  --intake-spec specs/intake_v0.6.yaml --section-uses specs/guards/section_uses_T027.yaml \
  --out-dir ~/nk1-data/gen/<run>_rr --inbox-name <草稿檔名>.docx --inbox ~/nk1-data/gen/handover-inbox
```
- **常見失敗**：`FileNotFoundError …sections.jsonl` → `--gen-dir` 要指到含 `run1/` 的那層。

## §8 驗收表（交驗收人；開發方不填）

```bash
python3 scripts/nk1-acceptance-sheet.py --skel <骨架.yaml> --draft "<草稿檔名> <sha8>" --xlsx ~/nk1-data/gen/NK1_驗收表_vN.xlsx
```
- 七項判準與例句在 xlsx「說明」頁。驗收人＝三顧品保（開發期）；開發方回報**只寫自測數字與 sha，不寫「通過」「驗收」**（`specs/acceptance_protocol.md`）。

## §9 記憶包

```bash
bash scripts/gen-nk1-pack.sh        # 產 NK1_記憶包.md；遮蔽閘沒過或 >300 KB 即不產（fail-closed）
```
- 完成判據＝印出的「輸出 hash 前／後」與「閘 exit code ＝ 0」，不是「跑完沒噴錯」。

## §10 回送改動給阿K（她不持 GitHub 憑證）

見 `HANDOVER.md`「回送改動」。回送前先跑 §3 守衛；阿K 端另跑第 8 道（`scripts/nk1-inbound.sh`）。

## §11（阿K 端）收件與重出交付 bundle

```bash
scripts/nk1-inbound.sh ~/ak-inbox/nk1-in/<回送>.bundle      # 第 8 道；全過才照印出的指令手動合
git bundle create ~/ak-inbox/nk1-out/handover/nk1-<tag>.bundle main --tags
shasum -a 256 ~/ak-inbox/nk1-out/handover/nk1-<tag>.bundle > …/nk1-<tag>.bundle.sha256
git bundle verify ~/ak-inbox/nk1-out/handover/nk1-<tag>.bundle
```
- 🔴 bundle 只含 `main` 與 tags，**不用 `--all`**（會帶出本機封存分支 `archive/pre-M5.8`，含真號與原稿檔名）。
