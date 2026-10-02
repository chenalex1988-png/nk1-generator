#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 條號表 v0 產生器（工單【NK1・M1.1】B1）— 公開來源 → specs/refs/annex15_v0.yaml。

只抽【法規名、條號、標題一行】，**不抄條文全文**：
  標題＝該條所屬的小節標題（如 URS／DQ／IQ），無小節者取章標題。
範圍（設備確效）：Annex 15 第 1（組織與規劃）、2（文件）、3（確認階段：URS／DQ／FAT-SAT／IQ／OQ／PQ）、
  4（再確認）、8（公用系統確認）、11（變更管制）章。
來源文字由 PDF 以 macOS PDFKit 抽出（repo 外，~/nk1-data/refs/）；PDF 內多個條號黏成一行者（「1.4 1.5 …」）逐一展開。
中文標題（選配）：--zh-txt 給食藥署中英對照版抽出的文字；章標題依章號、小節標題依【英文】對應，缺者留空。

用法：nk1-refs-build.py --pics-txt pics_annexes.txt --pics-url URL --pics-sha SHA [--zh-txt tfda.txt --zh-url URL --zh-sha SHA] --out specs/refs/annex15_v0.yaml
零依賴、確定性。
"""
import argparse, re, sys

VERSION = "1.0.0"
LAW = "PIC/S GMP Annex 15"
CHAPTERS = {1, 2, 3, 4, 8, 11}
STAGE = {                                   # 小節／章 → 確效階段標籤（覆蓋率檢查用）
    "User requirements specification (URS)": "URS", "Design qualification (DQ)": "DQ",
    "Factory acceptance testing (FAT) /Site acceptance testing (SAT)": "FAT/SAT",
    "Installation qualification (IQ)": "IQ", "Operational qualification (OQ)": "OQ",
    "Performance qualification (PQ)": "PQ",
}
CH_STAGE = {1: "規劃", 2: "文件", 3: "確認通則", 4: "再確效", 8: "公用系統", 11: "變更"}
RE_CH = re.compile(r"^(\d{1,2})\.\s+([A-Z][A-Z ,/()\-]+)$")
RE_CLAUSES = re.compile(r"^((?:\d{1,2}\.\d{1,2}(?:\.\d)?\s+)+)")
RE_SUB = re.compile(r"^[A-Z][A-Za-z ()/,\-]{3,80}$")


def parse(lines):
    start = next(i for i, l in enumerate(lines) if l.strip() == "ANNEX 15")
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip().startswith("ANNEX 16"))
    body = [l.strip() for l in lines[start:end]]
    ch, ch_title, sub, out, seen = None, "", None, [], set()
    for i, l in enumerate(body):
        m = RE_CH.match(l)
        if m and int(m.group(1)) <= 12:
            ch, ch_title, sub = int(m.group(1)), m.group(2).strip(), None
            nxt = body[i + 1] if i + 1 < len(body) else ""
            if re.fullmatch(r"[A-Z][A-Z ,/()\-]+\.?", nxt):      # 章標題折行（尾句點去掉）
                ch_title += " " + nxt.rstrip(".")
            continue
        m = RE_CLAUSES.match(l + " ")
        if m and ch in CHAPTERS:
            nums = m.group(1).split()
            if all(n.split(".")[0] == str(ch) for n in nums):
                prev = body[i - 1] if i else ""
                if RE_SUB.match(prev) and not prev.isupper():
                    sub = prev
                for n in nums:
                    if n not in seen:
                        seen.add(n)
                        out.append({"clause": n, "chapter": ch, "chapter_title": re.sub(r"\bvmp\b", "VMP", ch_title.capitalize()),
                                    "sub": sub if ch == 3 and n != "3.1" else None})
    return out


def parse_zh(lines):
    """食藥署附則 15：章號 → 中文章名；小節英文 → 中文小節名。"""
    start = next(i for i, l in enumerate(lines) if re.match(r"^附則 *15 ", l) and "..." not in l)
    ch, sub, prev = {}, {}, ""
    for l in lines[start + 1:]:
        l = l.strip()
        if re.match(r"^附則 *1[6-9]", l):
            break
        m = re.match(r"^(\d{1,2})\. (.+?)\s*（[A-Z]", l)
        if m and int(m.group(1)) not in ch:
            ch[int(m.group(1))] = re.sub(r"\s+", "", m.group(2))
        m = re.match(r"^(.*?)【(.+)】$", l)
        if m:
            sub[m.group(2).strip()] = (m.group(1).strip() or prev).strip()
        prev = l
    return ch, sub


def _q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pics-txt", required=True)
    ap.add_argument("--pics-url", required=True)
    ap.add_argument("--pics-sha", required=True)
    ap.add_argument("--zh-txt")
    ap.add_argument("--zh-url", default="")
    ap.add_argument("--zh-sha", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = parse(open(a.pics_txt, encoding="utf8").read().splitlines())
    zh_ch, zh_sub = parse_zh(open(a.zh_txt, encoding="utf8").read().splitlines()) if a.zh_txt else ({}, {})
    stages = {}
    L = ["# NK1 條號表 v0 — 設備確效（工單【NK1・M1.1】B1；產生器 scripts/nk1-refs-build.py v" + VERSION + "）",
         "# 只有【法規名、條號、標題一行】；不含條文全文。標題＝該條所屬小節／章標題。",
         f"# 來源①（英文、條號依據）：{a.pics_url}",
         f"#   PIC/S GMP Guide (PE 009-18) Annexes，sha256 {a.pics_sha}",
         (f"# 來源②（中文標題對照）：{a.zh_url}\n#   食藥署 西藥藥品優良製造規範（第一部、附則），sha256 {a.zh_sha}"
          if a.zh_txt else "# 來源②（中文標題）：未取得，title_zh 留空"),
         "# 🔴 人抽驗（J-17：每節條號指到實際條文）由 Alex／三顧 QA 執行，本檔未經人抽驗。",
         "version: 0", f"law: {_q(LAW)}", "refs:"]
    for r in rows:
        title = r["sub"] or r["chapter_title"]
        st = STAGE.get(r["sub"]) if r["sub"] else CH_STAGE.get(r["chapter"])
        st = st or CH_STAGE.get(r["chapter"])
        stages[st] = stages.get(st, 0) + 1
        L.append(f"  - {{law: {_q(LAW)}, clause: {_q(r['clause'])}, title: {_q(title)}, "
                 f"title_zh: {_q(zh_sub.get(r['sub'], '') if r['sub'] else zh_ch.get(r['chapter'], ''))}, stage: {_q(st)}}}")
    open(a.out, "w", encoding="utf8").write("\n".join(L) + "\n")
    print(f"✅ {a.out}　條數 {len(rows)}　階段分布 " + "、".join(f"{k} {v}" for k, v in stages.items()), file=sys.stderr)
    need = {"URS", "DQ", "IQ", "OQ", "PQ", "變更", "再確效"}
    miss = need - set(stages)
    if len(rows) < 30 or miss:
        print(f"🔴 未達標：條數 {len(rows)}（需 ≥30）／缺階段 {sorted(miss)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
