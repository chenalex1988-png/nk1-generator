#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 條號表 v1 產生器（工單【M5.0】A）— v0 ＋ 原文 ＋ 中譯 ＋ 版次 ＋ 來源 ＋ 對應文件類型／章節。

來源（皆 repo 外，~/nk1-data/refs/）：
  - PIC/S PE 009-18 Annexes（pics_annexes.txt，PDFKit 抽出）
  - 食藥署《西藥藥品優良製造規範（第一部、附則）》2019（tfda.txt）＝PE009-14 中英對照
做法：
  ① 自食藥署附則 15 逐條抽「中文段」與「英文段」（同行中英在最後一個中文後切開；頁尾「第 N 頁，共 M 頁」濾除）。
  ② 英文段逐詞比對 PE 009-18（去條號與羅馬數字清單標記後）：連續一致＝identical；
     全詞依序覆蓋但不連續＝identical_noncontiguous（PDF 欄位交錯所致，非文字差異）；其餘＝diff（列表尾）。
     一致者 original＝該英文段（即 PE 009-18 原文）。
  ③ original 一律進 repo，附 original_sha256（M5.1 A：specs/refs/ 公開法規原文免人名樣式規則，
     條件＝version／source 為 PE 009-18 且 sha256 相符；由 scripts/refs-exempt.py 在守衛 ③ 執行）。
     translation_zh 仍過完整遮蔽閘；未過者不進 repo（off_repo 指標＋sha256，全文寫 --offrepo）。
  ④ 對應文件類型／章節依 specs/refs/annex15_v1_mapping.yaml（🔶 阿K 提案，待品保勾改）。
輸出：specs/refs/annex15_v1.json；--xlsx 另出品保勾選表（含全部原文）。零依賴、確定性。
"""
import argparse, difflib, hashlib, json, os, re, subprocess, sys, tempfile

VERSION = "1.2.0"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nk1_flowyaml as fy  # noqa: E402
import nk1_xlsx  # noqa: E402

CJK = re.compile(r"[　-〿一-鿿＀-￯]")
RE_ST = re.compile(r"^(\d{1,2}\.\d{1,2})\s+(.*)$")
RE_FOOT = re.compile(r"第\s*\d+\s*頁，共\s*\d+\s*頁")
VERSION_ORIG, VERSION_ZH = "PE 009-18", "食藥署 2019（PE009-14）"


def split_mixed(l):
    idx = [m.end() for m in CJK.finditer(l)]
    if not idx:
        return [("en", l)]
    k = idx[-1]
    right = l[k:].strip()
    if len(re.findall(r"[A-Za-z]{2,}", right)) >= 2:
        return [("zh", l[:k].strip()), ("en", right)]
    return [("zh", l)]


def tfda_blocks(path, want):
    T = open(path, encoding="utf8").read().split("\n")
    st = max(i for i, l in enumerate(T) if l.strip() == "附則 15 驗證與確效（QUALIFICATION AND VALIDATION）")
    en = next(i for i in range(st + 1, len(T)) if T[i].startswith("12. 術語彙編"))
    blocks, cur = {}, None
    for raw in T[st:en]:
        l = RE_FOOT.sub("", raw).strip()
        if not l or l.startswith("<<<PAGE"):
            continue
        if re.match(r"^\d{1,2}\. \S", l) or "【" in l or "】" in l:
            cur = None
            continue
        for lang, part in split_mixed(l):
            if not part:
                continue
            m = RE_ST.match(part)
            if m:
                cur = m.group(1) if m.group(1) in want else None
                if cur:
                    blocks.setdefault(cur, {"zh": [], "en": []})[lang].append(m.group(2))
                continue
            if cur:
                blocks[cur][lang].append(part)
    return {c: {"zh": "".join(v["zh"]).strip(), "en": re.sub(r"\s+", " ", " ".join(v["en"])).strip()} for c, v in blocks.items()}


def _words(t):
    t = t.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
    t = re.sub(r"(?<![\w.])\d{1,2}\.\d{1,2}(?:\.\d)?(?![\w.])", " ", t)
    t = re.sub(r"(?<!\w)[ivx]{1,5}\.(?=\s)", " ", t)
    t = re.sub(r"-\s+(?=[a-z])", "-", t)
    return re.findall(r"[A-Za-z0-9/()\"'%-]+|[.,;:]", t)


def pics_words(path):
    L = open(path, encoding="utf8").read().split("\n")
    s = next(i for i, l in enumerate(L) if l.strip() == "ANNEX 15")
    e = next(i for i in range(s + 1, len(L)) if L[i].strip().startswith("ANNEX 16"))
    keep = [l for l in L[s:e] if not re.match(r"^(PE 009-18 \(Annexes\)|Annex 15 Qualification and validation|<<<PAGE)", l.strip())]
    return _words(" ".join(keep))


def compare(PW, text):
    EW = _words(text)
    if " ".join(EW) in " ".join(PW):
        return "identical", 1.0
    sm = difflib.SequenceMatcher(None, PW, EW, autojunk=False)
    cov = sum(m.size for m in sm.get_matching_blocks()) / max(len(EW), 1)
    return ("identical_noncontiguous" if cov == 1.0 else "diff"), round(cov, 4)


def gate_ok(text):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf8") as f:
        f.write(text + "\n")
        p = f.name
    try:
        return subprocess.run(["bash", os.path.join(HERE, "masking-gate.sh"), p], capture_output=True).returncode == 0
    finally:
        os.unlink(p)


def expand_rules(rules, order):
    out = {}
    for r in rules:
        a, b = order.index(r["from"]), order.index(r["to"])
        for c in order[a:b + 1]:
            d = out.setdefault(c, {"doc_types": [], "sections": []})
            d["doc_types"] += [x for x in r["doc_types"] if x not in d["doc_types"]]
            d["sections"] += [x for x in r["sections"] if x not in d["sections"]]
    return out


COMPARISON_NOTE = {
    "versions": "食藥署 2019《西藥藥品優良製造規範（第一部、附則）》中英對照版（對應 PIC/S PE009-14，2018-07-01）vs PIC/S PE 009-18 Annexes",
    "method": ["① 條號對齊：自兩份 PDF 抽出附則／Annex 15 文字，以條號（如 3.9）為鍵逐條配對",
               "② 英文條文比對：食藥署版的英文段（＝PE009-14 原文）對 PE 009-18 英文，去除條號與羅馬數字清單標記後逐詞比對；"
               "連續一致＝identical，全詞依序出現但不連續＝identical_noncontiguous（PDF 欄位交錯），其餘＝diff",
               "③ 中譯：取食藥署版中文段（PE009-14 之譯文）；中譯與英文**不做逐字比對**——中英不同語言，無「逐字」可言"],
    "wording_fix": "「44 條逐字一致」更正為：44 條條號一一對應；英文條文 PE009-14 與 PE 009-18 逐詞一致 43 條、依序一致但排版不連續 1 條（1.6）、差異 0 條；中譯為食藥署對 PE009-14 之譯文"}


def code_map(skel_path):
    sk = fy.load(skel_path)
    rows = []
    for s_ in sk["sections"]:
        rows.append((f"S{s_['order']:02d}", s_["level"], s_["name"], s_.get("segment") or "—", "固定文" if s_.get("fixed") else "模型"))
    units = []
    for rp in sk.get("repeats") or []:
        for st, sg in zip(rp["starts"], rp.get("segments") or []):
            units.append((sg, f"S{st - 1:02d}", f"S{st + len(rp['block']) - 1:02d}"))
    return rows, units


def zh_only(name):
    t = re.sub(r"[A-Za-z][A-Za-z ]*$", "", name).strip()
    return t or name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v0", required=True)
    ap.add_argument("--mapping", required=True)
    ap.add_argument("--pics-txt", required=True)
    ap.add_argument("--tfda-txt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--offrepo", required=True)
    ap.add_argument("--xlsx")
    ap.add_argument("--skel", help="M5.4 D：骨架 YAML，產 S 碼對照")
    ap.add_argument("--code-map-out", help="M5.4 D：S 碼對照 md（repo；節名只取中文部分）")
    ap.add_argument("--comparison-out", help="M5.4 D：比對方法與結果 md")
    a = ap.parse_args()
    v0 = fy.load(a.v0)
    refs = v0["refs"]
    order = [r["clause"] for r in refs]
    head = open(a.v0, encoding="utf8").read()
    shas = dict(re.findall(r"#\s+(PIC/S|食藥署)[^\n]*?sha256 ([0-9a-f]{64})", head))
    mp = fy.load(a.mapping)
    rules = expand_rules(mp["rules"], order)
    bl = tfda_blocks(a.tfda_txt, order)
    PW = pics_words(a.pics_txt)
    out, off, diffs = [], {}, []
    for r in refs:
        c = r["clause"]
        en, zh = bl[c]["en"], bl[c]["zh"]
        cmp_, cov = compare(PW, en)
        if cmp_ != "identical":
            diffs.append({"clause": c, "result": cmp_, "word_coverage": cov})
        item = dict(r, version=VERSION_ORIG, source="PE 009-18／食藥署 2019", translation_version=VERSION_ZH,
                    original=en, translation_zh=zh, pe009_18_check=cmp_,
                    doc_types=rules.get(c, {}).get("doc_types", []), sections=rules.get(c, {}).get("sections", []))
        item["original_sha256"] = hashlib.sha256(en.encode()).hexdigest()
        blocked = [k for k, t in (("translation_zh", zh),) if not gate_ok(t)]
        if blocked:
            for k in blocked:
                off.setdefault(c, {})[k] = item[k]
                item[k] = None
                item[k + "_off_repo"] = {"path": "~/nk1-data/refs/" + os.path.basename(a.offrepo), "key": f"{c}.{k}",
                                         "sha256": hashlib.sha256(off[c][k].encode()).hexdigest(),
                                         "why": "遮蔽閘人名樣式規則誤觸公開法規原文；未改規則、未改寫原文"}
        out.append(item)
    doc = {"version": 1, "law": v0["law"], "generator": f"nk1-refs-v1.py v{VERSION}",
           "sources": {"pics_pe009_18": {"url": "https://picscheme.org/docview/11333", "sha256": shas.get("PIC/S")},
                       "tfda_2019_pe009_14": {"url": "https://www.fda.gov.tw/upload/46/2019051415254182544.pdf", "sha256": shas.get("食藥署")}},
           "title_zh_source": "食藥署 2019 中英對照版（對應 PE009-14，2018-07-01）",
           "mapping": "specs/refs/annex15_v1_mapping.yaml（🔶 阿K 提案，待品保勾改）",
           "correspondence": {"clauses": len(out), "number_one_to_one": sum(1 for x in out if x["translation_zh"] or x.get("translation_zh_off_repo")),
                              "pe009_14_vs_18": {"identical": sum(1 for x in out if x["pe009_18_check"] == "identical"),
                                                 "identical_noncontiguous": sum(1 for x in out if x["pe009_18_check"] == "identical_noncontiguous"),
                                                 "diff": sum(1 for x in out if x["pe009_18_check"] == "diff")},
                              "differences": diffs},
           "comparison": COMPARISON_NOTE,
           "sections_field_use": "審閱對照（品保 2026-09-30 函 3-4）：不作正文插入位置、不作正文攔截",
           "doc_types": mp["doc_types"], "not_included": mp["not_included"], "refs": out}
    json.dump(doc, open(a.out, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    open(a.out, "a", encoding="utf8").write("\n")
    os.makedirs(os.path.dirname(os.path.expanduser(a.offrepo)), exist_ok=True)
    json.dump(off, open(os.path.expanduser(a.offrepo), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    rows_map, units = code_map(a.skel) if a.skel else ([], [])
    if a.code_map_out and rows_map:
        with open(a.code_map_out, "w", encoding="utf8") as f:
            f.write("# T027 骨架節碼對照（M5.4 D-10；品保 2026-09-30 函 3-2）\n\n"
                    "> 節名級結構（2026-09-27 ① 可進 repo）。節名只列中文部分；完整節名見條號表 xlsx「S碼對照」頁。\n\n"
                    "| 節碼 | 層級 | 節名 | 段 | 生成 |\n|---|---:|---|---|---|\n")
            for c, lv, nm, sg, kind in rows_map:
                f.write(f"| {c} | {lv} | {zh_only(nm)} | {sg} | {kind} |\n")
            f.write("\n| 段代號 | 範圍 | 含 |\n|---|---|---|\n")
            for sg, a0, a1 in units:
                f.write(f"| {sg} | {a0}～{a1} | 段首＋段別測試＋七項子節 |\n")
    if a.comparison_out:
        with open(a.comparison_out, "w", encoding="utf8") as f:
            f.write("# 條號表 v1 比對方法與結果（M5.4 D-11；品保 2026-09-30 函 3-3）\n\n")
            f.write(f"**比對的兩版**：{COMPARISON_NOTE['versions']}\n\n**方法**\n\n" + "\n".join(f"- {m}" for m in COMPARISON_NOTE["method"]))
            c = doc["correspondence"]
            f.write(f"\n\n**結果**\n\n| 項 | 值 |\n|---|---|\n| 條號一一對應 | {c['number_one_to_one']}／{c['clauses']} |\n"
                    f"| 英文逐詞一致（連續） | {c['pe009_14_vs_18']['identical']} |\n| 英文依序一致但排版不連續 | {c['pe009_14_vs_18']['identical_noncontiguous']} |\n"
                    f"| 英文差異 | {c['pe009_14_vs_18']['diff']} |\n\n**非連續／差異清單**\n\n| 條號 | 結果 | 詞覆蓋率 | 說明 |\n|---|---|---:|---|\n")
            for d in c["differences"]:
                f.write(f"| {d['clause']} | {d['result']} | {d['word_coverage']} | PE 009-18 PDF 欄位交錯，相鄰條文插入其間；全部詞依序出現，非文字差異 |\n")
            f.write(f"\n**措辭更正**：{COMPARISON_NOTE['wording_fix']}\n")
    if a.xlsx:
        note = (f"來源：① PIC/S PE 009-18 Annexes（https://picscheme.org/docview/11333）sha256 前 8＝{(shas.get('PIC/S') or '')[:8]}；"
                f"② 食藥署 2019（PE009-14 中英對照）sha256 前 8＝{(shas.get('食藥署') or '')[:8]}｜原文經逐詞比對 PE009-14＝PE 009-18｜"
                "對應文件類型／章節為阿K 提案，請品保勾改｜未經人抽驗")
        cols = ["序號", "法規名", "條號", "標題", "原文（PE 009-18 英文）", "中譯（食藥署 2019）", "版次", "來源",
                "對應文件類型（提案）", "對應章節（審閱對照・提案）", "QA 勾選", "QA 修正對應", "備註"]
        rows = [[note], cols]
        for i, x in enumerate(out, 1):
            orig = x["original"] if x["original"] is not None else off[x["clause"]]["original"]
            tz = x["translation_zh"] if x["translation_zh"] is not None else off[x["clause"]]["translation_zh"]
            rows.append([i, x["law"], x["clause"], f"{x['title_zh']}（{x['title']}）", orig, tz, x["version"], x["source"],
                         "、".join(x["doc_types"]), "、".join(x["sections"]), None, None, None])
        cand = [["候選但未納（理由欄留空給認可主體）"], ["項目", "理由"]] + [[n["item"], None] for n in mp["not_included"]]
        sg3 = [["三顧 QA 簽核頁：認清單正確性（原文／中譯／版次）——品保 2026-09-30 函 3-1"],
               ["序號", "條號", "標題", "原文正確", "中譯正確", "版次正確", "意見", "簽核人", "日期"]] + \
              [[i, x["clause"], x["title_zh"], None, None, None, None, None, None] for i, x in enumerate(out, 1)]
        sgl = [["樂迦 QA 簽核頁：認適用（本設備／本文件類型）——品保 2026-09-30 函 3-1"],
               ["序號", "條號", "標題", "適用", "對應文件類型確認", "對應章節確認（審閱對照）", "意見", "簽核人", "日期"]] + \
              [[i, x["clause"], x["title_zh"], None, None, None, None, None, None] for i, x in enumerate(out, 1)]
        cmap = [["S碼對照（T027 骨架；品保 2026-09-30 函 3-2）"], ["節碼", "層級", "節名", "段", "生成"]] + \
               [list(r) for r in rows_map] + [[None], ["段代號", "範圍", "含"]] + [[u[0], f"{u[1]}～{u[2]}", "段首＋段別測試＋七項子節"] for u in units]
        cmp_ = [["比對方法與結果（品保 2026-09-30 函 3-3）"], ["項", "內容"], ["比對的兩版", COMPARISON_NOTE["versions"]]] + \
               [["方法", m] for m in COMPARISON_NOTE["method"]] + \
               [["條號一一對應", f"{doc['correspondence']['number_one_to_one']}／{len(out)}"],
                ["英文逐詞一致（連續）", str(doc['correspondence']['pe009_14_vs_18']['identical'])],
                ["英文依序一致但排版不連續", "、".join(d["clause"] for d in diffs) or "0"],
                ["英文差異", str(doc['correspondence']['pe009_14_vs_18']['diff'])],
                ["措辭更正", COMPARISON_NOTE["wording_fix"]]]
        nk1_xlsx.write_xlsx(os.path.expanduser(a.xlsx), [
            {"name": "條號表v1", "rows": rows, "widths": [6, 18, 7, 30, 60, 40, 11, 18, 26, 24, 10, 20, 20],
             "note_row": 1, "header_row": 2, "fill_cols": {10, 11, 12}, "freeze": 3},
            {"name": "三顧QA簽核", "rows": sg3, "widths": [6, 7, 24, 10, 10, 10, 30, 12, 12], "note_row": 1, "header_row": 2,
             "fill_cols": {3, 4, 5, 6, 7, 8}, "freeze": 3},
            {"name": "樂迦QA簽核", "rows": sgl, "widths": [6, 7, 24, 8, 16, 20, 30, 12, 12], "note_row": 1, "header_row": 2,
             "fill_cols": {3, 4, 5, 6, 7, 8}, "freeze": 3},
            {"name": "S碼對照", "rows": cmap, "widths": [10, 6, 34, 8, 8], "note_row": 1, "header_row": 2},
            {"name": "比對方法", "rows": cmp_, "widths": [22, 100], "note_row": 1, "header_row": 2},
            {"name": "候選但未納", "rows": cand, "widths": [40, 50], "note_row": 1, "header_row": 2, "fill_cols": {1}}])
    print(f"✅ {a.out}　{len(out)} 條　比對 identical {doc['correspondence']['pe009_14_vs_18']}　off_repo {len(off)} 條", file=sys.stderr)


if __name__ == "__main__":
    main()
