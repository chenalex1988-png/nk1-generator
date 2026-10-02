# T 層清冊 v0.2 — 三顧模板（NK-templates_20260918）

| 標頭 | 值 |
|---|---|
| 版本 | **v0.2**（v0.1＝檔名與 hash；v0.2 加**來源／推定**兩欄，依 2026-09-19 Alex 裁決） |
| 產生時間 | 2026-09-19 14:52:26 +0800 |
| 來源包 | `NK-templates_20260918.zip` |
| 來源包 sha256 前 8 | `ef54ea51` |
| 來源落點 | `~/nk1-data/`（**repo 外**，解壓至 `~/nk1-data/templates/`） |
| **文件數** | **116**（＝資料夾數，一夾一文件） |
| 檔案數（備註） | 249（docx 111／json 116／pdf 22） |
| **v0.3 代號化（M5.8，2026-10-02）** | 依 Alex 裁 ①：repo 內**只留代號（T001～T116，`-f`＝夾內第 n 檔）與 sha8**；原稿檔名、資料夾名、文件編號、檔名版次欄已移除。對照表（代號↔真號↔原稿檔名）在 **repo 外** `~/nk1-data/refs/doc-codes.tsv`；v0.2 全文原樣存 `~/nk1-data/refs/T層清冊_full_v0.2.md` |
| 本清冊性質 | **只讀檔名、hash、docProps／PDF metadata**；**未開任何正文**、未讀 json value |
| 核定狀態 | 全部 **未核定**（本線不判定核定，由 Alex 裁決） |

> 🔴 **原檔一律不進 repo、不進記憶包。** 本清冊只記「有哪些、多大、hash 是什麼、從哪來」。
> 🔑 **來源欄＝觀察值**（metadata 實測所得）；**推定欄＝推定**（依裁決寫死的對應，非查證結果）。
> 　 **兩欄不可混為一談**：來源查得到，推定查不到。
> 🔑 **版次欄**：只從**檔名**抓；抓不到寫 `—`，**不代填、不推測**。
> 　 **docx 屬性未採用為版次**——`docProps/core.xml`／`app.xml` **沒有版次欄位**，
> 　 只有 Word 的修訂儲存次數（`cp:revision`），那**不是 GMP 版次**，填了就是代填。
> 　 另：屬性內含**人名欄位**（作者／最後修改者），依雷區**一律不取、不記錄**。
> 🔒 **遮蔽欄**：檔名中的客戶名／人名／產品代號樣式，清冊內以`[遮]`取代；**原檔名不動**。
> 　 規則來源＝真清單 `~/nk1-data/denylist.txt`（**repo 外**，含實際樣式，永不 commit）。

### 來源欄與推定欄的對應規則（v0.2 寫死）

| 檔型 | 來源欄（觀察值） | 推定欄 | 份數 |
|---|---|---|---:|
| docx | 程式產出（docProps 空、epoch） | NK 輸出 | 87 |
| docx | 無 core.xml | NK 輸出 | 1 |
| docx | Word 起稿（有作者、有日期）・`(管制明文)`樣式 | 三顧受控文件原稿（NK 輸入） | 11 |
| docx | Word 起稿（有作者、有日期）・`*模板*`樣式 | 人寫模板（NK 輸入） | 3 |
| docx | Word 起稿（有作者、有日期）・【審閱意見回饋】樣式 | 人審回饋 | 2 |
| docx | Word 起稿（有作者、有日期）・純中文名 | — | 2 |
| docx | 待查（docProps 作者空、但有實際日期） | — | 5 |
| pdf | 瀏覽器列印（Skia＋Chrome／Edge UA） | 外部法規／指引下載件 | 9 |
| pdf | Word・Acrobat・InDesign 轉出・**老件**（2009／2019／2020） | 外部法規／指引下載件 | 3 |
| pdf | Word・Acrobat・InDesign 轉出 | — | 5 |
| pdf | Print To PDF | — | 5 |
| json | chat payload（role/content ×2） | NK 生成紀錄 | 116 |

---

## 一、清冊（每檔一列）

| 代號（T＝資料夾／文件；-f＝夾內第 n 檔） | 副檔名 | 大小 (bytes) | sha256 前 8 | 來源（觀察值） | 推定 | 核定狀態 |
|---|---|---:|---|---|---|---|
| `T001-f1` | docx | 41866 | `64098ca5` | Word 起稿（有作者、有日期） | — | 未核定 |
| `T001-f2` | json | 109 | `be34ea67` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T003-f1` | json | 1605 | `023b442a` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T003-f2` | docx | 17601 | `7fefe909` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T004-f1` | json | 1935 | `a9891500` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T004-f2` | docx | 14968 | `42ded092` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T005-f1` | docx | 45267 | `552e162a` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T005-f2` | json | 1480 | `eaf86b0f` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T006-f1` | json | 1690 | `19b168dd` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T006-f2` | docx | 14436 | `e22dbbf4` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T007-f1` | json | 2187 | `76427a50` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T007-f2` | docx | 17081 | `42e349e7` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T008-f1` | json | 1575 | `e5f56335` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T008-f2` | docx | 14733 | `e36d5d39` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T009-f1` | docx | 19335 | `e1c9a4c6` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T009-f2` | json | 5910 | `2e4bf817` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T010-f1` | docx | 47885 | `de55eac7` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T010-f2` | json | 1991 | `64e2ffbe` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T011-f1` | docx | 47525 | `6a5e257d` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T011-f2` | json | 2765 | `ef7ccb22` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T012-f1` | pdf | 674342 | `1b02a1cf` | 瀏覽器列印 | 外部法規／指引下載件 | 未核定 |
| `T012-f2` | json | 2628 | `7be9b9a1` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T013-f1` | docx | 44680 | `894536f3` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T013-f2` | json | 2006 | `b8bdc4b3` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T014-f1` | docx | 44973 | `fef5b1da` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T014-f2` | json | 3129 | `5e6280ab` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T015-f1` | docx | 44983 | `425baf3b` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T015-f2` | json | 1388 | `31cce05c` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T016-f1` | docx | 17601 | `7df5db11` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T016-f2` | json | 2286 | `04cc6edd` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T017-f1` | docx | 47018 | `1d077901` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T017-f2` | json | 1873 | `5efa0fb9` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T018-f1` | docx | 20271 | `13b5ae51` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T018-f2` | json | 4465 | `5860586c` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T019-f1` | docx | 44667 | `900d106a` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T019-f2` | json | 1749 | `712c0922` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T020-f1` | docx | 16682 | `98c17cc2` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T020-f2` | json | 1854 | `68fc3fbc` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T021-f1` | docx | 46570 | `3c66bfc1` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T021-f2` | json | 1753 | `da8d5638` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T022-f1` | docx | 68651 | `f4595a4a` | Word 起稿（有作者、有日期） | 三顧受控文件原稿（NK 輸入） | 未核定 |
| `T022-f2` | docx | 30322 | `9beb7111` | Word 起稿（有作者、有日期） | 三顧受控文件原稿（NK 輸入） | 未核定 |
| `T022-f3` | json | 5091 | `12795e36` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T022-f4` | docx | 83938 | `2bd09245` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T002-f1` | json | 1592 | `3daa8f91` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T002-f2` | docx | 138308 | `c32c75c8` | Word 起稿（有作者、有日期） | — | 未核定 |
| `T023-f1` | docx | 48175 | `f1b3244e` | Word 起稿（有作者、有日期） | 三顧受控文件原稿（NK 輸入） | 未核定 |
| `T023-f2` | docx | 50593 | `5f2d91d7` | Word 起稿（有作者、有日期） | 三顧受控文件原稿（NK 輸入） | 未核定 |
| `T023-f3` | json | 1328 | `ae80c633` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T024-f1` | docx | 51637 | `a19ff101` | Word 起稿（有作者、有日期） | 三顧受控文件原稿（NK 輸入） | 未核定 |
| `T024-f2` | docx | 49886 | `68cd07b8` | Word 起稿（有作者、有日期） | 三顧受控文件原稿（NK 輸入） | 未核定 |
| `T024-f3` | json | 2246 | `b63a6883` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T025-f1` | docx | 26567 | `bac3b739` | Word 起稿（有作者、有日期） | 三顧受控文件原稿（NK 輸入） | 未核定 |
| `T025-f2` | docx | 26901 | `6c522b46` | Word 起稿（有作者、有日期） | 三顧受控文件原稿（NK 輸入） | 未核定 |
| `T025-f3` | json | 900 | `b389bbb0` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T026-f1` | docx | 33118 | `ffc1d219` | Word 起稿（有作者、有日期） | 三顧受控文件原稿（NK 輸入） | 未核定 |
| `T026-f2` | docx | 33267 | `cb1bb76e` | Word 起稿（有作者、有日期） | 三顧受控文件原稿（NK 輸入） | 未核定 |
| `T026-f3` | json | 2277 | `5c4da52b` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T026-f4` | docx | 53508 | `52d5d060` | Word 起稿（有作者、有日期） | 人寫模板（NK 輸入） | 未核定 |
| `T027-f1` | docx | 38540 | `fbad2c5b` | Word 起稿（有作者、有日期） | 三顧受控文件原稿（NK 輸入） | 未核定 |
| `T027-f2` | json | 1582 | `dac9d622` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T027-f3` | docx | 44190 | `f776d88c` | Word 起稿（有作者、有日期） | 人審回饋 | 未核定 |
| `T027-f4` | docx | 53877 | `661b5650` | Word 起稿（有作者、有日期） | 人審回饋 | 未核定 |
| `T028-f1` | json | 5905 | `23a8d152` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T028-f2` | docx | 23834 | `555319a1` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T029-f1` | json | 3481 | `05523e39` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T029-f2` | docx | 22761 | `853dab01` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T030-f1` | json | 1741 | `1c94023f` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T030-f2` | docx | 17476 | `7926d009` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T031-f1` | json | 3287 | `a0fe1e3f` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T031-f2` | pdf | 554221 | `ab3c4368` | Word・Acrobat・InDesign 轉出 | — | 未核定 |
| `T032-f1` | json | 3417 | `99790ef1` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T032-f2` | pdf | 576672 | `28aa1456` | Word・Acrobat・InDesign 轉出 | 外部法規／指引下載件 | 未核定 |
| `T032-f3` | pdf | 188256 | `15b90c98` | Word・Acrobat・InDesign 轉出 | — | 未核定 |
| `T035-f1` | docx | 16726 | `12e1ad18` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T035-f2` | json | 2558 | `bcbe499b` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T036-f1` | docx | 49350 | `bc0ada88` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T036-f2` | json | 5086 | `422ef370` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T037-f1` | docx | 23463 | `e5c12141` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T037-f2` | json | 3273 | `bf3fcf7d` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T038-f1` | docx | 17845 | `6d47cd3b` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T038-f2` | json | 2509 | `6dff31ef` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T039-f1` | docx | 23463 | `e5c12141` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T039-f2` | json | 2856 | `83d46fa5` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T040-f1` | json | 1978 | `b34f5ca1` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T040-f2` | docx | 15268 | `e909c9c1` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T041-f1` | docx | 17388 | `b0b3a32d` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T041-f2` | json | 3178 | `b257c2d2` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T042-f1` | json | 4536 | `45f1e18b` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T042-f2` | pdf | 3327284 | `5be1d875` | Print To PDF | — | 未核定 |
| `T043-f1` | json | 13320 | `691027f3` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T043-f2` | docx | 18497 | `b7ca0ca6` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T043-f3` | pdf | 3507373 | `6b35e2cd` | Print To PDF | — | 未核定 |
| `T033-f1` | json | 1189 | `bd1d9528` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T033-f2` | docx | 160243 | `ed009c9e` | Word 起稿（有作者、有日期） | 人寫模板（NK 輸入） | 未核定 |
| `T034-f1` | json | 823 | `8fe424d7` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T034-f2` | docx | 143827 | `b6043367` | Word 起稿（有作者、有日期） | 人寫模板（NK 輸入） | 未核定 |
| `T044-f1` | docx | 16608 | `0a10d0c0` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T044-f2` | json | 1383 | `04953463` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T045-f1` | docx | 15910 | `6ae4ad8c` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T045-f2` | json | 1965 | `bd9fc211` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T046-f1` | docx | 17614 | `df382e43` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T046-f2` | json | 875 | `c49e81c3` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T047-f1` | docx | 15740 | `c565dc24` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T047-f2` | json | 2857 | `050b46d1` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T048-f1` | docx | 16091 | `1a77488f` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T048-f2` | json | 1334 | `71db88e0` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T049-f1` | docx | 14343 | `a45a9dbb` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T049-f2` | json | 1358 | `21db97ca` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T050-f1` | docx | 15440 | `0a5aa3b1` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T050-f2` | json | 2573 | `8ea255cf` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T051-f1` | json | 4393 | `0d0a3637` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T051-f2` | pdf | 2514148 | `86677b14` | Print To PDF | — | 未核定 |
| `T051-f3` | pdf | 750647 | `dc0d5bf1` | Word・Acrobat・InDesign 轉出 | — | 未核定 |
| `T052-f1` | pdf | 1949789 | `29a278d4` | Print To PDF | — | 未核定 |
| `T052-f2` | json | 827 | `6922d0da` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T053-f1` | json | 4393 | `2d5aeb6c` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T053-f2` | pdf | 2378444 | `cd8aaee0` | Print To PDF | — | 未核定 |
| `T053-f3` | pdf | 750647 | `dc0d5bf1` | Word・Acrobat・InDesign 轉出 | — | 未核定 |
| `T054-f1` | docx | 44009 | `83f0cd91` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T054-f2` | json | 2660 | `186867bc` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T055-f1` | docx | 15423 | `582d32ec` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T055-f2` | json | 1803 | `fcffc5fa` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T056-f1` | docx | 16233 | `4c2ac0a0` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T056-f2` | json | 3252 | `b3f1bf95` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T057-f1` | docx | 15071 | `4713471c` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T057-f2` | json | 1935 | `d40c3f9e` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T058-f1` | docx | 15454 | `3787a697` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T058-f2` | json | 2576 | `1a924b36` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T059-f1` | docx | 53248 | `35c4e940` | 無 core.xml | NK 輸出 | 未核定 |
| `T059-f2` | json | 1975 | `da5187d8` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T060-f1` | docx | 45382 | `9873bd22` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T060-f2` | json | 1900 | `1f4f9616` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T061-f1` | docx | 14600 | `1831851c` | 待查 | — | 未核定 |
| `T061-f2` | json | 1066 | `6fe6b615` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T062-f1` | docx | 14537 | `ef3593c8` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T062-f2` | json | 2015 | `4189557e` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T063-f1` | pdf | 241735 | `a289b5d7` | Word・Acrobat・InDesign 轉出 | 外部法規／指引下載件 | 未核定 |
| `T063-f2` | docx | 13697 | `01c7b33c` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T063-f3` | json | 1355 | `b3ab1a15` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T065-f1` | docx | 91469 | `f3fe3f07` | 待查 | — | 未核定 |
| `T065-f2` | json | 553 | `a6517c2b` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T065-f3` | docx | 53390 | `83f5e976` | 待查 | — | 未核定 |
| `T064-f1` | docx | 19804 | `3953cc48` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T064-f2` | json | 9251 | `fe9445cf` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T064-f3` | docx | 28577 | `938b445f` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T066-f1` | docx | 17864 | `baf3c3d2` | 待查 | — | 未核定 |
| `T066-f2` | json | 3934 | `fbdcfdbf` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T067-f1` | json | 1828 | `6ae2c63a` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T067-f2` | docx | 14372 | `2838f4ad` | 待查 | — | 未核定 |
| `T068-f1` | json | 2251 | `312d68d7` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T068-f2` | pdf | 983384 | `fcbf34c4` | 瀏覽器列印 | 外部法規／指引下載件 | 未核定 |
| `T069-f1` | json | 2563 | `a5fee4fa` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T069-f2` | pdf | 1237980 | `33968da1` | 瀏覽器列印 | 外部法規／指引下載件 | 未核定 |
| `T070-f1` | pdf | 237631 | `b32c1f3f` | Word・Acrobat・InDesign 轉出 | 外部法規／指引下載件 | 未核定 |
| `T070-f2` | docx | 13789 | `7f134c76` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T070-f3` | json | 2183 | `70091e6a` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T071-f1` | docx | 16541 | `3367dade` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T071-f2` | json | 2860 | `b9477107` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T072-f1` | pdf | 1160909 | `fe485780` | 瀏覽器列印 | 外部法規／指引下載件 | 未核定 |
| `T072-f2` | json | 2754 | `aa28abb3` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T073-f1` | pdf | 1078751 | `af96fdf7` | 瀏覽器列印 | 外部法規／指引下載件 | 未核定 |
| `T073-f2` | json | 2708 | `b4c51f6a` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T074-f1` | pdf | 1024814 | `74c94ee5` | 瀏覽器列印 | 外部法規／指引下載件 | 未核定 |
| `T074-f2` | json | 2607 | `5a8c00d2` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T075-f1` | pdf | 1027974 | `9988abe4` | 瀏覽器列印 | 外部法規／指引下載件 | 未核定 |
| `T075-f2` | json | 4671 | `68eab590` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T076-f1` | pdf | 1294379 | `9cbe27b0` | 瀏覽器列印 | 外部法規／指引下載件 | 未核定 |
| `T076-f2` | json | 3209 | `52c7f64f` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T077-f1` | docx | 16138 | `1c7c9a5c` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T077-f2` | json | 5495 | `386d47f4` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T078-f1` | pdf | 994472 | `dc96ceb8` | 瀏覽器列印 | 外部法規／指引下載件 | 未核定 |
| `T078-f2` | json | 3049 | `2f893158` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T079-f1` | docx | 14468 | `267154d5` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T079-f2` | json | 3354 | `350df128` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T080-f1` | docx | 14955 | `34b862da` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T080-f2` | json | 2093 | `9ceec385` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T081-f1` | docx | 14806 | `2bee3db9` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T081-f2` | json | 3161 | `a82e32a4` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T082-f1` | docx | 16302 | `29315186` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T082-f2` | json | 4472 | `e3d38355` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T083-f1` | json | 100 | `1affbea8` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T083-f2` | docx | 26378 | `4468e4d2` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T084-f1` | json | 2882 | `ba5e9469` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T084-f2` | docx | 22485 | `7c312a0e` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T085-f1` | json | 2836 | `72e6fa0c` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T085-f2` | docx | 21859 | `c0d0b5d0` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T086-f1` | json | 3486 | `0579f1a9` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T086-f2` | docx | 22835 | `ad4850b6` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T087-f1` | json | 3913 | `564a4008` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T087-f2` | docx | 24494 | `f807d7a0` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T088-f1` | json | 2965 | `18d65de2` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T088-f2` | docx | 22637 | `d730909b` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T089-f1` | json | 3622 | `f2c70142` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T089-f2` | docx | 16779 | `9d1c37fc` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T090-f1` | json | 4902 | `10558058` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T090-f2` | docx | 24629 | `015853a5` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T091-f1` | docx | 23588 | `c58e47b1` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T091-f2` | json | 2679 | `bf479b6d` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T092-f1` | json | 3157 | `3762bf3b` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T092-f2` | docx | 24253 | `796d3219` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T093-f1` | docx | 19509 | `0b20c5c4` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T093-f2` | json | 7480 | `d6c17cd3` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T094-f1` | json | 2939 | `63f684ce` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T094-f2` | docx | 23853 | `c206a7ed` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T095-f1` | docx | 17914 | `5c1ad2e2` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T095-f2` | json | 4000 | `6366b233` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T096-f1` | json | 4254 | `e958dd7c` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T096-f2` | docx | 22160 | `da5f8c9e` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T097-f1` | json | 4552 | `18f5cd4a` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T097-f2` | docx | 22820 | `40f36727` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T098-f1` | json | 1975 | `095a4922` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T098-f2` | docx | 18778 | `2aa6c0ed` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T099-f1` | json | 1752 | `ec5b7df4` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T099-f2` | docx | 18030 | `96d4e9af` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T100-f1` | json | 1803 | `f7803a07` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T100-f2` | docx | 17451 | `3fe0179a` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T101-f1` | json | 2391 | `eb4bf7a3` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T101-f2` | docx | 19637 | `a05d6e5c` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T102-f1` | json | 2839 | `dba29a90` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T102-f2` | docx | 18373 | `549faede` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T103-f1` | json | 1735 | `13764271` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T103-f2` | docx | 17463 | `b17b4f12` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T104-f1` | json | 2150 | `5bd9fbc2` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T104-f2` | docx | 18145 | `17a638f7` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T105-f1` | json | 2007 | `bf79503c` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T105-f2` | docx | 21408 | `532500f8` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T106-f1` | json | 2016 | `4470444a` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T106-f2` | docx | 18112 | `69725e2e` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T107-f1` | json | 2459 | `a34cfa37` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T107-f2` | docx | 17365 | `ee8c980d` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T108-f1` | json | 1642 | `bec60ac0` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T108-f2` | docx | 17373 | `3dc5f921` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T109-f1` | json | 1999 | `dd9f30fa` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T109-f2` | docx | 18390 | `d4f5f5fc` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T110-f1` | json | 4232 | `391d1c17` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T110-f2` | docx | 17415 | `27bc9e07` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T111-f1` | json | 1769 | `9c432db3` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T111-f2` | docx | 16723 | `f0ffecff` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T112-f1` | json | 1989 | `506fc0ca` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T112-f2` | docx | 16364 | `16e98525` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T113-f1` | docx | 19185 | `4694b4d1` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T113-f2` | json | 3440 | `a59976e7` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T114-f1` | json | 3165 | `1b6e3eef` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T114-f2` | docx | 23723 | `51a037f2` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T115-f1` | json | 3462 | `dc5e70b4` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |
| `T115-f2` | docx | 23027 | `db8b2c43` | 程式產出（docProps 空、epoch） | NK 輸出 | 未核定 |
| `T116-f1` | pdf | 46894 | `b63525af` | Word・Acrobat・InDesign 轉出 | — | 未核定 |
| `T116-f2` | json | 130 | `d8062425` | chat payload（role/content ×2） | NK 生成紀錄 | 未核定 |

---

## 二、表尾統計

| 項目 | 值 |
|---|---|
| **文件數** | **116**（資料夾數） |
| 檔案數（備註） | 249 |
| 遮蔽命中 | 21 筆 |
| 版次抓得到 | 11 筆；抓不到（`—`） 238 筆 |
| 核定 | **0 份**（零份經核定） |

### 副檔名分佈

| 副檔名 | 檔數 |
|---|---:|
| json | 116 |
| docx | 111 |
| pdf | 22 |

### 最大檔（前 5）

| 大小 (bytes) | 檔（已遮） |
|---:|---|
| 3507373 | `T043-f3` |
| 3327284 | `T042-f2` |
| 2514148 | `T051-f2` |
| 2378444 | `T053-f2` |
| 1949789 | `T052-f1` |

---

## 三、計數與可用性

**原 104 無對應。** 本包實際＝**116 文件／249 檔案**，與前提 4 記載的「104 份模板文件」對不上，
亦無任何 104 的子集或超集可資對應；**104 此數廢止**。

**可外用地基推定＝`(管制明文)` 11 ＋ `*模板*` 3 ＝ 14 份 docx。**

**NK 輸出 87 份與 prompt json 116 份的使用權，待詮隼合約產出物歸屬條款確認，確認前只作參照。**

> ⚠️ 「地基 14 份」是**推定**，**零份經核定**——核定是 Alex 的裁決，不是本清冊的判定。

### 其他已知落差

1. **遮蔽規則為 fail-closed**：21 筆命中中有 1 筆為通用英文詞被姓名樣式誤命中（寧可多遮，不放寬規則）。
2. **pdf metadata 取法**：本機無 `pdfinfo`（poppler 未裝）、無 `pypdf`；改以①檔頭字串掃描、
   ②對掃不到的 6 份用 `mdls`。**兩者皆不解析頁面內容。**
3. **5 份「待查」**：docProps 作者空但有實際建檔日期（2026-03 ×2／2025-10 ×2／2025-09 ×1），
   分佈 4 個資料夾，**所在夾皆無 pdf**。歸屬未定。
