#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 既有草稿重掃（工單【M5.0】D）— 不生成；以 M5.0 policy 閘重掃既有 sections.jsonl（寫入正文＋各節 refs）。

用法：nk1-recheck-v2.py --gen-dir ~/nk1-data/gen/m44/<run_id> --skel SKEL.yaml --intake I.json --intake-spec S.yaml \\
        --section-uses U.yaml --refs specs/refs/annex15_v1.json [--run run1]
輸出：只有統計與逐節計數（零正文）。
"""
import argparse, importlib.util, json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
_sp = importlib.util.spec_from_file_location("nk1_gen", os.path.join(HERE, "nk1-gen.py"))
g = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(g)


def main():
    ap = argparse.ArgumentParser()
    for k in ("gen-dir", "skel", "intake", "intake-spec", "section-uses", "refs"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--run", default="run1")
    ap.add_argument("--qa5", action="store_true", help="M5.4：核對品保 2026-09-30 函 2-1 所列五處位置是否全部命中")
    a = ap.parse_args()
    skel = g.s2d.load_skel(a.skel)
    roles = g.section_roles(skel)
    by = {s["order"]: s for s in skel["sections"]}
    base = g.policy_base(json.load(open(a.intake, encoding="utf8")), g.fy.load(a.intake_spec), g.fy.load(a.section_uses), g.load_refs(a.refs))
    rows, tot, secs_hit = [], Counter(), Counter()
    for l in open(os.path.join(os.path.expanduser(a.gen_dir), a.run, "sections.jsonl"), encoding="utf8"):
        x = json.loads(l)
        if not x.get("passed"):
            continue
        o = x["order"]
        ctx = g.policy_ctx(base, by[o], roles.get(o))
        try:                                                     # refs 取模型原始輸出（含 version）；舊產物存檔時未留 version
            refs = json.loads(x.get("raw") or "{}").get("refs") or x.get("refs") or []
        except Exception:
            refs = x.get("refs") or []
        reasons, d = g.policy_checks(x["body"], refs, ctx)
        for k in ("use_misplaced", "clause_misplaced", "version_missing"):
            tot[k] += d.get(k, 0)
        tot["result_terms"] += len(d.get("result_terms", []))
        tot["result_statements"] += len(d.get("result_statements", []))
        tot["overflow"] += len(d.get("overflow", []))
        for r in reasons:
            secs_hit[r] += 1
        rows.append((x["sid"], (roles.get(o) or (None, None))[0] or "—", d))
    print(f"| 項 | 值 |\n|---|---|\n| 重掃節數（寫入正文） | {len(rows)} |")
    print(f"| **結果陳述命中節數（全文內容判）** | **{secs_hit['結果陳述']}**（命中 {tot['result_statements']} 句） |")
    print(f"| **結果禁令命中節數** | **{secs_hit['結果禁令']}**（判定語命中 {tot['result_terms']} 次） |")
    print(f"| **值用途錯置數** | **{tot['use_misplaced']}**（涉及 {secs_hit['用途錯置']} 節） |")
    print(f"| **條號章節錯置數** | **{tot['clause_misplaced']}**（涉及 {secs_hit['章節錯置']} 節） |")
    print(f"| 缺版次數 | {tot['version_missing']}（涉及 {secs_hit['缺版次']} 節） |")
    print(f"| 超標處置命中 | {tot['overflow']}（涉及 {secs_hit['超標處置']} 節） |")
    if a.qa5:
        hit = {sid for sid, _, d in rows if d.get("result_statements")}
        pos = [("計畫核准", ["S01"]), ("操作驗證（概述）", ["S16"]), ("性能驗證（概述）", ["S25"]),
               ("性能驗證測試、方法步驟、備註", ["S26", "S28", "S33"]), ("安裝驗證・備註", ["S15"])]
        print("\n| 品保 2-1 位置 | 對應節 | 命中 |\n|---|---|---|")
        miss = 0
        for name, sids in pos:
            got = [x for x in sids if x in hit]
            ok = len(got) == len(sids)
            miss += 0 if ok else 1
            print(f"| {name} | {'／'.join(sids)} | {'✅' if ok else '🔴 缺 ' + '／'.join(x for x in sids if x not in hit)} |")
        print(f"\n品保五處：{'✅ 全部命中' if not miss else f'🔴 少 {miss} 處（fail）'}")
    print("\n| 節 | 段 | 結果陳述 | 結果禁令 | 用途錯置 | 章節錯置 | 缺版次 | 超標處置 |\n|---|---|---:|---:|---:|---:|---:|---:|")
    for sid, seg, d in rows:
        print(f"| {sid} | {seg} | {len(d.get('result_statements', []))} | {len(d.get('result_terms', []))} | {d.get('use_misplaced', 0)} | {d.get('clause_misplaced', 0)} | "
              f"{d.get('version_missing', 0)} | {len(d.get('overflow', []))} |")


if __name__ == "__main__":
    main()
