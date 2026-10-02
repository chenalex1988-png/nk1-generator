# NK1 llama-server 備援評估（唯讀；工單【NK1・M4 恢復】D）

> 不裝、不跑推論。依據＝`llama-server --help`／`--version`、Ollama 執行中的程序參數（ps）、模型 manifest、upstream `tools/server/README.md`。

## 結論
**可行，且不增加供應鏈。** Ollama 0.34.4 的 app bundle 內已附 `llama-server`，Ollama 推論時本來就以它**直接載入同一個 GGUF blob**；
直接呼叫它可拿掉 Ollama Go 層（雲端／remotes／registry 等網路功能）。代價是要換 API 介面並重建基準線。

## 事實
| 項 | 值 |
|---|---|
| 執行檔 | `/Applications/Ollama.app/Contents/Resources/llama-server`（隨 Ollama 0.34.4 公證 bundle；`--version`：0.4.1-dev，commit `161755f29`，Ollama 自建版本） |
| Ollama 啟動它的參數（ps 實錄） | `--model <blob> --host 127.0.0.1 --offline --no-webui -c 4096 -np 1 --no-jinja --chat-template chatml --mmproj <同 blob> …` |
| GGUF | `~/.ollama/models/blobs/sha256-dec52a44…bb99d37c`，魔數 `GGUF`，6,594,462,816 bytes；**sha256 實算＝檔名 digest**（manifest `application/vnd.ollama.image.model`） |
| 網路相關選項（皆需明確啟用） | `--model-url`、`-hf/--hf-repo/--hf-file`、`--docker-repo`、`--mmproj-url`、MCP（`--mcp-servers-*`、webui MCP proxy）、tools 的 `ssh:`／`docker:` runtime |
| 關網路 | `--offline`：「forces use of cache, prevents network access」 |
| 遙測／更新檢查 | help 與 README **皆未見**（未見≠已證不存在；仍須全程監看證明） |
| 約束輸出 | `/v1/chat/completions` 支援 `response_format` json_schema；`/completion` 支援 `json_schema`；兩者支援 `seed`、`temperature` |

## 供應鏈面積比較
| | 現行：Ollama serve | 備援①：直接用 bundle 內 llama-server | 備援②：upstream llama.cpp release |
|---|---|---|---|
| 新增安裝 | 無 | **無**（同一個已公證 bundle） | 新二進位（GitHub release，需 P4 紀錄） |
| 網路功能面 | Go 層：cloud、remotes（預設 ollama.com）、registry pull；+ llama-server | 只剩 llama-server 的明確下載類選項；`--offline` 可關 | 同②（依版本） |
| 已觀測外連 | 有（2026-09-27，NO_CLOUD=false） | 未觀測（未跑） | 未觀測（未跑） |
| API | `/api/chat`＋`format` schema（M3／M4 基準） | OpenAI 相容 `/v1/chat/completions`＋json_schema | 同左 |
| 聊天模板 | Ollama renderer（qwen3.5）＋ think false | 需自己指定模板與「不思考」處理 | 同左 |
| 代價 | — | nk1-gen／probe 要加 API 轉接；**M3／M4 的 sha 基準線要重建**；版本跟著 Ollama 升級走 | 同①＋獨立升級與驗證 |

## 建議（未做）
先維持 Ollama＋`NO_CLOUD=1`＋全程監看；若再有外連，改備援①（不需新裝），並以同一套監看器驗證零外連、重建 M4 基準。
