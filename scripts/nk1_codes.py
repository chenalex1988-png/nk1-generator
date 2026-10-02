#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 文件代號層（工單 M5.8；Alex 2026-10-02 裁 ①）。

repo 內只留代號（T001～T116）與 sha8；代號↔真號↔原稿資料夾名的對照表在 repo 外：
  ~/nk1-data/refs/doc-codes.tsv（欄：code／folder／number／title；# 開頭為註解）

讀真資料夾的工具（充足度、附件⑤…）在讀檔那一刻用 folder_of() 換回真名，
寫進 repo 的輸出一律先過 encode()。對照表缺席＝fail-closed（exit 2），不猜。

用法（CLI）：nk1_codes.py encode <檔…>   就地把真號／資料夾名換成代號，印每檔替換數與歧義殘留
            nk1_codes.py check  <檔…>   只查不改：有真號殘留回 1
"""
import os, re, sys

MAP = os.path.join(os.path.expanduser("~"), "nk1-data", "refs", "doc-codes.tsv")
# 真號樣式（代號化之後 repo 內應為 0 命中）
NUM_RE = re.compile(r"(?<![A-Za-z0-9])(?:(?:LC-(?:EN|MIS|RD)|F|M|PW|QA|QC|qc)-\d{3}(?!\d)|[FM]\+)")


def load(path=MAP):
    if not os.path.isfile(path):
        print(f"🔴 代號對照表不存在：{path}（repo 外；fail-closed）", file=sys.stderr)
        sys.exit(2)
    rows = []
    for l in open(path, encoding="utf8"):
        if l.startswith("#") or not l.strip():
            continue
        code, folder, number, title = l.rstrip("\n").split("\t")
        rows.append((code, folder, number, title))
    if not rows:
        print(f"🔴 代號對照表為空：{path}", file=sys.stderr)
        sys.exit(2)
    return rows


def code_of(folder, rows=None):
    for c, f, _, _ in rows or load():
        if f == folder:
            return c
    raise KeyError(folder)


def folder_of(code, rows=None):
    for c, f, _, _ in rows or load():
        if c == code:
            return f
    raise KeyError(code)


def _subs(rows):
    """（樣式, 代號）由長到短：資料夾名 → 號＋標題 → 唯一的裸號。歧義裸號不換、留給人看。"""
    lit = []
    for c, f, n, t in rows:
        if not n and "+" not in f:
            continue  # 無編號且無 + 的資料夾名（如 test）是普通字，換了會誤傷
        lit += [(f, c), (f.replace("+", " "), c)]
        if n and t:
            for sep in ("", "+", " ", "　"):
                lit.append((n + sep + t, c))
                lit.append((n + sep + t.replace(" ", "+"), c))
            lit.append((n + " | " + t, c + " | —"))  # 表格「號 | 標題」：保留欄位、標題留白
    lit = sorted(set(lit), key=lambda x: -len(x[0]))
    by_num = {}
    for c, _, n, _ in rows:
        if n:
            by_num.setdefault(n, []).append(c)
    uniq = {n: cs[0] for n, cs in by_num.items() if len(cs) == 1}
    amb = {n: cs for n, cs in by_num.items() if len(cs) > 1}
    return lit, uniq, amb


def encode(text, rows=None):
    """回傳 (新文字, 替換數, 歧義殘留[(號, 候選代號, 行)])"""
    lit, uniq, amb = _subs(rows or load())
    n = 0
    for s, c in lit:
        k = text.count(s)
        if k:
            text, n = text.replace(s, c), n + k

    hit = [0]

    def rep(m):
        if m.group(0) in uniq:
            hit[0] += 1
            return uniq[m.group(0)]
        return m.group(0)
    text = NUM_RE.sub(rep, text)
    left = [(m.group(0), amb.get(m.group(0), []), text.count("\n", 0, m.start()) + 1) for m in NUM_RE.finditer(text)]
    return text, n + hit[0], left


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("encode", "check"):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    rows, bad = load(), 0
    for p in sys.argv[2:]:
        src = open(p, encoding="utf8").read()
        new, n, left = encode(src, rows)
        if sys.argv[1] == "encode" and new != src:
            open(p, "w", encoding="utf8").write(new)
        for num, cs, ln in left:
            print(f"   ⚠️ {p}:{ln} 殘留 {num}（候選 {'/'.join(cs) or '無對照'}）")
        bad += len(left)
        if n or left:
            print(f"{'✏️' if sys.argv[1] == 'encode' else '🔍'} {p}：替換 {n}、殘留 {len(left)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
