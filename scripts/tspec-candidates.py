#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 T-spec 候選詞表抽取 — 規則抽取，**不做語意判讀、不做合併、不出 schema**。

輸入：~/nk1-data/templates 下 116 份 json 的第 1 則 content。
輸出：三張去重詞表（詞・出現份數），**無來源檔名對應、無上下文**。
  (a) 章節候選：行首樣式（一、／1.／第N章／##／(1)）後 ≤12 字的標題文字
  (b) 欄位候選：命中「欄位／填寫／填入」前後 ≤8 字的名詞片段
  (c) 指令類型計數：格式／章節／欄位／語言／長度／禁止 六類，每類份數

🔴 本腳本是【阿K 不讀 prompt 全文】的實作：全文只進 python 記憶體，
   stdout 只出詞與計數。「本機」不等於「不上雲」，判準是誰的眼睛看到文字。

用法：tspec-candidates.py <輸出目錄>
"""
import json, os, re, sys
from collections import Counter

CORPUS = os.path.expanduser("~/nk1-data/templates")
CUT = re.compile(r"[，。：:；;、！？（）()\[\]【】「」\"'/\\|]")

SEC_MARKERS = [
    re.compile(r"^\s*[一二三四五六七八九十]+、\s*(.+)$"),
    re.compile(r"^\s*\d+\s*[\.、)）]\s*(.+)$"),
    re.compile(r"^\s*第\s*[一二三四五六七八九十百\d]+\s*[章節條]\s*(.+)$"),
    re.compile(r"^\s*#{1,6}\s+(.+)$"),
    re.compile(r"^\s*[（(]\s*\d+\s*[）)]\s*(.+)$"),
]
FIELD_KEYS = ["欄位", "填寫", "填入"]
KINDS = {
    "格式": r"格式|排版|樣式|依下列|如下所示",
    "章節": r"章節|節次|條列|分節|段落",
    "欄位": r"欄位|填寫|填入",
    "語言": r"繁體|中文|英文|語言|中英",
    "長度": r"字數|字以內|字以上|長度|不超過|以內完成",
    "禁止": r"不得|禁止|不可|不要|避免|勿",
}

MD = re.compile(r"^[\s*_`>-]+|[\s*_`]+$")     # markdown 記號不是內容（行首用，不含 #）
GRP = re.compile(r"^[\s*_`>#-]+|[\s*_`#]+$")  # 擷取到的標題文字用（含 #，##4. 這種殘留要剝掉）

def clean(s, cap):
    s = GRP.sub("", s.strip())
    s = CUT.split(s)[0].strip()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"^\d+[\.、)]?", "", s)          # 殘留的層級編號不是標題文字
    return GRP.sub("", s)[:cap]

def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    files = sorted(os.path.join(d, f) for d, _, fs in os.walk(CORPUS)
                   for f in fs if f.endswith(".json"))
    if not files:
        print("🔴 語料 0 份，停手", file=sys.stderr); return 2
    sec, fld = Counter(), Counter()
    kinds = {k: 0 for k in KINDS}
    for p in files:
        d = json.load(open(p, encoding="utf-8"))
        t = str((d[0] if isinstance(d, list) else d).get("content", ""))
        seen_s, seen_f = set(), set()
        for line in t.splitlines():
            line = MD.sub("", line)          # 先剝 markdown 記號，再比行首樣式
            for m in SEC_MARKERS:
                g = m.match(line)
                if g:
                    w = clean(g.group(1), 12)
                    if 2 <= len(w) <= 12: seen_s.add(w)
                    break
        for key in FIELD_KEYS:
            for m in re.finditer(key, t):
                for frag in (t[max(0, m.start()-8):m.start()], t[m.end():m.end()+8]):
                    w = clean(frag[::-1], 8)[::-1] if frag is t[max(0, m.start()-8):m.start()] else clean(frag, 8)
                    w = re.sub(r"^[的之與和及或]+|[的之與和及或]+$", "", w)
                    if not (2 <= len(w) <= 8): continue
                    if re.fullmatch(r"[\d\W_]+", w): continue
                    # 句子碎片濾除：動詞／助詞／連接詞起訖者不是欄位名
                    if re.match(r"^(應|需|請|可|會|要|將|於|在|並|也|即|進行|包含|包括|填|寫|列)", w): continue
                    if re.search(r"(應|需|請|可以|即可|時|了|的)$", w): continue
                    if re.search(r"(也應|應包|應列|並應|以及)", w): continue
                    seen_f.add(w)
        sec.update(seen_s); fld.update(seen_f)
        for k, r in KINDS.items():
            if re.search(r, t): kinds[k] += 1
    n = len(files)
    with open(os.path.join(out, "a_章節候選.tsv"), "w", encoding="utf-8") as fh:
        for w, c in sec.most_common(): fh.write(f"{w}\t{c}\n")
    with open(os.path.join(out, "b_欄位候選.tsv"), "w", encoding="utf-8") as fh:
        for w, c in fld.most_common(): fh.write(f"{w}\t{c}\n")
    with open(os.path.join(out, "c_指令類型.tsv"), "w", encoding="utf-8") as fh:
        for k in KINDS: fh.write(f"{k}\t{kinds[k]}\n")
    print(f"語料 {n} 份　(a) 章節候選 {len(sec)} 列　(b) 欄位候選 {len(fld)} 列　(c) 指令類型 {len(KINDS)} 列")
    return 0

if __name__ == "__main__":
    sys.exit(main())
