# NK1 環境

> 🔴 **內網主機：主機清空與管理者交接完成後才裝。** 清空進度由管理者（數位經理）回報董事長；未完成前本檔 §2～§4 只作清單，不執行。
> 兩台平台不同（macOS arm64 ↔ Linux aarch64）：**平台綁定的 wheel 與 Ollama 執行檔都不通用，一律重取、重驗 sha。**
> 本檔版本值於 2026-10-02 在 Air2 現查。

## §1 現有環境：Air2（macOS arm64，現執行腦開發機）

| 項目 | 版本／值 | 路徑／備註 |
|---|---|---|
| OS | macOS 26.6.2（25G83），arm64 | — |
| git | 2.54.0（macOS 內建版，build 157） | — |
| Python | 3.9.6（系統 CommandLineTools） | 測試零依賴，系統 python 即可跑 |
| venv | Python 3.9.6 | `.venv/`（gitignore），`requirements-docx.txt` 鎖 hash 安裝 |
| docxtpl | 0.20.2（LGPL-2.1-only） | 渲染 |
| python-docx | 1.2.0（MIT） | |
| Jinja2 | 3.1.6（BSD） | |
| lxml | 6.1.3（BSD-3-Clause） | wheel `cp39-cp39-macosx_10_9_universal2`（**平台綁定**） |
| MarkupSafe | 3.0.3（BSD-3-Clause） | wheel `cp39-cp39-macosx_11_0_arm64`（**平台綁定**） |
| typing_extensions | 4.16.0（PSF-2.0） | |
| SQLite | 3.51.0 | v1 未用（檢索延 v2） |
| Ollama | 0.34.4（`Ollama-darwin.zip`，sha256 `f7ed834269e98929d9ed63d884c982287ec09d7ab6ee89587f90b9697a003ff1`，codesign／公證通過） | `/Applications/Ollama.app`；以 `ollama serve` 直接起、不開 GUI；綁 127.0.0.1:11434；平時停 |
| 模型 | `qwen3.5:9b`（9.7B，Q4_K_M，6,594,474,711 bytes） | digest `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`；`~/.ollama/models` |
| 監看 | `lsof`（系統內建） | `scripts/nk1-netwatch.py`、`nk1-gen.py` 內 Watch 皆用 `lsof -nP -i -a -c ollama -c llama-server` |
| repo 外資料 | `~/nk1-data/` | 見 `DATA.md` |

供應鏈紀錄：`memory/decisions.md` 2026-09-26（docxtpl）、2026-09-27（Ollama＋模型）。

## §2 內網主機安裝清單：Ollama（Linux aarch64）

主機：ARM aarch64 20 核、NVIDIA GB10（Blackwell）、約 128 GB 記憶體、驅動 580.95.05／CUDA 13.0（管理者 2026-10-02 實機查得）。

| 檔 | 版本 | 大小 | sha256（GitHub release asset digest，2026-10-02 現查） |
|---|---|---:|---|
| `ollama-linux-arm64.tar.zst` | v0.34.4（2026-09-23 發佈） | 1,549,684,612 | `96f50a1192133028cf4e010d8c333f8af14b1505db6be7b2034c11487e7fd7e6` |
| `sha256sum.txt`（release 附） | v0.34.4 | 1,472 | `05307bc104c4cd4d1905ecaccb86743c64db770b4510f294c55a0ce49c6f23a6` |

來源：`https://github.com/ollama/ollama/releases/tag/v0.34.4`。安裝步驟見 `RUNBOOK.md` §4（解壓到使用者目錄、不用安裝腳本、不裝 systemd 服務）。
- ⚠️ 同 release 另有 `ollama-linux-arm64-jetpack5／jetpack6`——那是 **Jetson** 用的，**GB10 不適用**，不要選。
- 版本與 Air2 對齊（0.34.4），讓兩邊生成可比；要升級另開工單。
- 模型搬運見 `RUNBOOK.md` §5；digest 必須與 §1 相同。

## §3 內網主機安裝清單：Python wheel（aarch64）

純 Python（跨平台通用，與 Air2 同一個 wheel、同 sha）：docxtpl 0.20.2、python-docx 1.2.0、Jinja2 3.1.6、typing_extensions 4.16.0（sha 見 `requirements-docx.txt`）。

平台綁定（**須依主機 Python 版本挑一個**；主機 Python 版本＝🔶 待查）。來源 PyPI，sha256 為 PyPI JSON digests（2026-10-02 現查）：

| 套件 | wheel | sha256 |
|---|---|---|
| lxml 6.1.3 | `lxml-6.1.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl` | `ff88a92cafde90888511242d1c54afcc1a8adbb6dc0a88fa7f87e29e92400d4a` |
| lxml 6.1.3 | `lxml-6.1.3-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.whl` | `4a579dfb9c835f8ab47f4b8ed33440cbc75b806b73297208e6ec2a33e903740b` |
| lxml 6.1.3 | `lxml-6.1.3-cp312-cp312-manylinux2014_aarch64.manylinux_2_17_aarch64.whl` | `f683dc6300317700025e41d89a43e0276692ded16113a3c43eab704d605c58e5` |
| lxml 6.1.3 | （另有 `manylinux_2_26/2_28` 版：cp310 `773062ae…f975cf`、cp311 `ea2c01cd…f951d41`、cp312 `b3777210…c0d0a`） | glibc ≥2.28 時 pip 會優先選 |
| MarkupSafe 3.0.3 | `markupsafe-3.0.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl` | `1ba88449deb3de88bd40044603fafffb7bc2b055d626a330323a9ed736661695` |
| MarkupSafe 3.0.3 | `markupsafe-3.0.3-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl` | `6b5420a1d9450023228968e7e6a9ce57f65d148ab56d2313fcd589eee96a7a50` |
| MarkupSafe 3.0.3 | `markupsafe-3.0.3-cp312-cp312-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl` | `3a7e8ae81ae39e62a41ec302f972ba6ae23a5c5396c8e60113e9066ef893da0d` |

做法：在有網路的機器以 `pip download --only-binary=:all: --platform manylinux2014_aarch64 --python-version <主機版本> -r …` 取 wheel → 逐一比對上表 sha → 產 `requirements-docx.linux-aarch64.txt`（`--require-hashes`）→ 加密介質搬運 → `RUNBOOK.md` §2 離線裝。

## §4 待查項（主機清空後、安裝前由管理者現查回報）

| # | 項目 | 為什麼要查 | 怎麼查 |
|---|---|---|---|
| E1 | OS 發行版與版本、glibc 版本 | wheel 選 `manylinux2014` 或 `2_28`；`tar --zstd` 可用否 | `cat /etc/os-release; ldd --version` |
| E2 | Python 版本 | 決定 §3 選哪個 cp 標籤 | `python3 -V` |
| E3 | **Ollama 0.34.4 linux-arm64 包對 GB10（Blackwell）＋CUDA 13 的支援** | 包內附的 CUDA runtime 版本是否涵蓋 GB10；不支援時會靜默退回 CPU（只會慢，不會報錯） | 起 serve 後看 log 的 GPU 偵測行與 `ollama ps` 的 PROCESSOR 欄；`nvidia-smi` 看是否有 ollama 行程 |
| E4 | 驅動 580.95.05 與包內 CUDA runtime 的相容性 | 驅動版本須 ≥ runtime 要求 | 同 E3；不相容時記錄 log 原文回報 |
| E5 | `lsof` 是否可用、能否看到 ollama 行程的連線 | 監看器靠它；看不到＝零外連無從證明 | `which lsof`；serve 起後 `lsof -nP -i -a -c ollama` |
| E6 | 是否容器化、誰有 root、可否建本機帳號 | 監看權限、日後 v2 每 scope 一 OS user | 管理者回答 |
| E7 | 主機是否另有其他 Ollama／模型服務殘留 | 清空是否完成；避免連到舊服務 | `ss -ltnp`；`ps aux | grep -i ollama` |
| E8 | 主機對外網路出口（可否 OS 層斷網） | OS 層斷網是零外連的更強證據（部署主機確定後改由主機層斷網） | 管理者回答 |

📌 E3／E4 在 Air2 上**無法驗**（無 NVIDIA GPU），只能在主機上現查。查不到就寫「查不到：原因」，不以印象作答。
