#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 附件⑤ 三顧模板參考清單（工單【M5.5】B；Alex 2026-10-01 四裁 ②：三顧模板仍作撰寫參考，不複製正文、不進草稿）。

依據＝各工具實際讀取範圍（程式碼為準）＋ specs/T層清冊.md（資料夾＝文件）：
  - 充足度測試 nk1-sufficiency.py：E1–E3 共 12 夾的 docx 與 prompt（E4–E6 只列名、未讀）
  - 封閉集合 E3 基準：T003～T008 的 NK 輸出 docx
  - T-spec 候選詞表 tspec-candidates.py：116 份 prompt（全夾）
  - 節名詞彙表八個共用骨架詞：取自 F 系列 NK 輸出共用節名（M1.1 A）
  - 骨架／詞彙表其餘節名：取自 LC-EN 夾 B 群（樂迦側 C 層樣本，**不是三顧模板**）
分類：採用（撰寫參考，進入 NK1 規格者）／讀過但未採用（範圍內只做統計、範圍外）；排除＝建檔者指向樂迦之 16 份。
只列文件編號與標題（節名級可進 repo）；版次欄留白給文管。
"""
import argparse, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nk1_xlsx  # noqa: E402
import nk1_codes  # noqa: E402

IN_SCOPE = ["T023", "T024", "T025", "T026", "T027", "T002", "T003", "T004", "T005", "T006", "T007", "T008"]
ADOPTED = {"T003", "T004", "T005", "T006", "T007", "T008"}
SHARED8 = "目的／範圍／程序／職責／參考資料／政策／定義／附件和表單"
LEJIA = ("三顧受控文件原稿（NK 輸入）", "人寫模板（NK 輸入）", "人審回饋")


def split_code(code, real=False):
    """代號 →（顯示編號, 標題）。預設只出代號（進 repo 用）；--real 經 repo 外對照表換回真號與標題（對外附件用）。"""
    if not real:
        return code, "—"
    for c, f, n, ti in nk1_codes.load():
        if c == code:
            return (n or "—"), (ti or f.replace("+", " "))
    raise SystemExit(f"🔴 代號 {code} 不在對照表（fail-closed）")


def load(path):
    fold = {}
    for l in open(path, encoding="utf8"):
        if not l.startswith("| `"):
            continue
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        f = c[0].strip("`").split("-f")[0]  # 清冊 v0.3：代號-f序（M5.8 起 repo 內無檔名）
        d = fold.setdefault(f, {"prompt": 0, "nk": 0, "lejia": 0})
        if c[1] == "json":
            d["prompt"] += 1
        elif c[5] == "NK 輸出":
            d["nk"] += 1
        elif c[5] in LEJIA:
            d["lejia"] += 1
    return fold


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--md", required=True)
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--real", action="store_true", help="輸出真號與標題（讀 repo 外對照表；輸出檔須落 repo 外）")
    ap.add_argument("--label", default="附件⑤", help="xlsx 表頭附件標籤（對外信件可改，如「附件 E」）")
    a = ap.parse_args()
    fold = load(a.inventory)
    adopted, read_only, excluded = [], [], []
    for f, d in sorted(fold.items()):
        code = f
        shown, title = split_code(code, a.real)
        if d["lejia"]:
            excluded.append((shown, title, d["lejia"]))
        if code in ADOPTED:
            adopted.append((shown, title, "節名", f"共用骨架詞（{SHARED8}）進節名詞彙表；另作充足度節名統計、封閉集合 E3 數值基準",
                            f"NK 輸出 docx {d['nk']} 份；prompt {d['prompt']} 份讀過（統計／候選詞，未採用）"))
        elif code in IN_SCOPE:
            read_only.append((shown, title, "範圍內", "充足度測試（節名統計）、T-spec 候選詞表；未進規格與草稿",
                              f"prompt {d['prompt']} 份" + ("；NK 輸出 0 份" if not d["nk"] else f"；NK 輸出 {d['nk']} 份")))
        elif d["prompt"]:
            read_only.append((shown, title, "範圍外", "T-spec 候選詞表（規則抽取，未採用）", f"prompt {d['prompt']} 份"))
    hdr = ("# 附件⑤ 三顧模板參考清單（NK1，2026-10-01）\n\n"
           "> Alex 2026-10-01 四裁：① LC 現行模板為結構基礎，三顧模板不作結構來源；② 三顧模板仍作撰寫參考（節名用語、欄位名、句型），"
           "不複製正文、不進草稿。\n> 依各工具實際讀取範圍列出（程式碼為準）；只列文件編號與標題；**版次欄留白，待文管回填**。\n\n"
           f"**要點**：NK1 草稿迄今**未直接使用三顧模板正文**；骨架取自 {split_code('T027', a.real)[0]}（樂迦側），指引句為合成撰寫。"
           "實際進入 NK1 規格的三顧內容只有「節名用語」——F 系列共用骨架詞八個。\n\n")
    L = [hdr, f"## 一、採用（撰寫參考）— {len(adopted)} 份\n\n| 文件編號 | 標題 | 用途 | 採用內容 | 版次 | 備註 |\n|---|---|---|---|---|---|\n"]
    L += [f"| {c} | {t} | {u} | {w} | | {n} |\n" for c, t, u, w, n in adopted]
    L += [f"\n## 二、讀過但未採用 — {len(read_only)} 份\n\n| 文件編號 | 標題 | 範圍 | 讀取方式 | 版次 | 備註 |\n|---|---|---|---|---|---|\n"]
    L += [f"| {c} | {t} | {s} | {w} | | {n} |\n" for c, t, s, w, n in read_only]
    L += [f"\n## 三、排除（建檔者指向樂迦，C 層樣本，不是三顧模板）— {sum(x[2] for x in excluded)} 份\n\n| 文件編號 | 標題 | 份數 |\n|---|---|---:|\n"]
    L += [f"| {c} | {t} | {k} |\n" for c, t, k in excluded]
    open(a.md, "w", encoding="utf8").write("".join(L))
    rows = [[f"{a.label} 三顧模板參考清單（NK1，2026-10-01）｜只列文件編號與標題｜版次欄留白待文管回填｜草稿迄今未直接使用三顧模板正文"],
            ["文件編號", "標題", "用途（節名／欄位／句型）", "版次", "備註"]]
    rows += [[c, t, f"採用：{u}（{w}）", None, n] for c, t, u, w, n in adopted]
    rows += [[c, t, f"讀過但未採用（{s}）：{w}", None, n] for c, t, s, w, n in read_only]
    nk1_xlsx.write_xlsx(os.path.expanduser(a.xlsx), [{"name": a.label.replace("附件", "附件").replace(" ", "")[:31], "rows": rows, "widths": [12, 34, 60, 10, 34],
                                                     "note_row": 1, "header_row": 2, "fill_cols": {3}, "freeze": 3}])
    print(f"✅ 採用 {len(adopted)}／讀過未採用 {len(read_only)}（範圍內 {sum(1 for r in read_only if r[2] == '範圍內')}、範圍外 {sum(1 for r in read_only if r[2] == '範圍外')}）／排除 {sum(x[2] for x in excluded)} 份", file=sys.stderr)


if __name__ == "__main__":
    main()
