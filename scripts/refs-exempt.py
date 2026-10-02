#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 遮蔽閘例外：specs/refs/ 公開法規原文免人名樣式規則（工單【M5.1】A；Alex 裁）。

用法：refs-exempt.py DIFF --out FILTERED_DIFF [--all]（--all＝全樹模式，M5.8）
  1. 讀 staged（無 staged 則工作樹）的 specs/refs/*.json；逐條檢查例外條件：
       version == "PE 009-18"、source 含 "PE 009-18"、original_sha256 == sha256(original)。
     條件不符的條目**不給例外**（其原文照常留在 diff 內受完整遮蔽閘檢查）。
  2. 符合條件者：其 `"original": …` 新增行自 diff 移出（輸出 FILTERED_DIFF 給 masking-gate.sh 做完整檢查），
     原文另以「遮蔽清單扣除人名樣式規則」單獨檢查——**只免人名規則，其餘規則照擋**。
     人名樣式規則＝清單中會命中正向樣本（兩個首字大寫英文詞相連）的規則，程式自動辨識、不印規則內容。
exit：0＝例外處理完成且扣除後規則 0 命中　1＝原文命中其他規則　2＝故障（fail-closed）
"""
import argparse, hashlib, json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_LIST = os.path.join(os.path.expanduser("~"), "nk1-data", "denylist.txt")
EXAMPLE_LIST = os.path.join(REPO, "scripts", "denylist.example.txt")
# 人名樣式規則的正向樣本（以拼接產生：字面本身就會觸發該規則）
CANARY = [" ".join(p) for p in (("Quality", "Assurance"), ("Process", "Validation"), ("Design", "Qualification"))]
VERSION = "PE 009-18"


def rules():
    path = REAL_LIST if os.path.exists(REAL_LIST) else EXAMPLE_LIST
    rs = [l.rstrip("\n") for l in open(path, encoding="utf8") if l.strip() and not l.lstrip().startswith("#")]
    if not rs:
        raise SystemExit(2)
    return rs


def grep_hit(pattern, text):
    r = subprocess.run(["grep", "-qE", "-e", pattern], input=text, text=True, capture_output=True)
    return r.returncode == 0


def eligible(refs):
    """例外條件：version／source 為 PE 009-18 且 original_sha256 相符 → [(clause, original)]。"""
    out = []
    for r in refs:
        o = r.get("original")
        if isinstance(o, str) and o and r.get("version") == VERSION and VERSION in str(r.get("source", "")) \
                and r.get("original_sha256") == hashlib.sha256(o.encode()).hexdigest():
            out.append((r.get("clause"), o))
    return out


def filter_diff(diff, exempt):
    ex_lines = {"+" + (" " * n) + '"original": ' + json.dumps(o, ensure_ascii=False) + c
                for _, o in exempt for n in range(0, 9) for c in (",", "")}
    kept = [l for l in diff.split("\n") if l not in ex_lines]
    return "\n".join(kept), len(diff.split("\n")) - len(kept)


def check_exempt(exempt, rs):
    name_rules = {p for p in rs if any(grep_hit(p, c) for c in CANARY)}
    others = [p for p in rs if p not in name_rules]
    return [c for c, o in exempt if any(grep_hit(p, o) for p in others)], len(name_rules), len(others)


def git(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("diff")
    ap.add_argument("--out", required=True)
    ap.add_argument("--all", action="store_true", help="全樹模式（M5.8）：對所有 tracked 的 specs/refs/*.json 判例外，供全樹／全歷史重掃")
    a = ap.parse_args()
    diff = open(a.diff, encoding="utf8").read()
    staged = bool(git("diff", "--cached", "--name-only").strip()) and not a.all
    names = git("ls-files") if a.all else (git("diff", "--cached", "--name-only") if staged else git("diff", "--name-only"))
    files = [f for f in names.split() if re.match(r"^specs/refs/.+\.json$", f)]
    exempt = []
    for f in files:
        content = git("show", f":{f}") if staged else open(os.path.join(REPO, f), encoding="utf8").read()
        try:
            refs = json.loads(content).get("refs") or []
        except Exception:
            print(f"🔴 refs 例外：{f} 不是合法 JSON（fail-closed）", file=sys.stderr)
            sys.exit(2)
        exempt += eligible(refs)
    filtered, removed = filter_diff(diff, exempt)
    open(a.out, "w", encoding="utf8").write(filtered)
    bad, nn, no = check_exempt(exempt, rules())
    print(f"🔍 refs 例外：條件符合 {len(exempt)} 條、自 diff 移出 {removed} 行；原文另以扣除人名樣式規則 {nn} 條後的 {no} 條規則檢查")
    if bad:
        print(f"🔴 refs 例外：原文命中其他遮蔽規則：{bad}", file=sys.stderr)
        sys.exit(1)
    print("✅ refs 例外：扣除人名規則後 0 命中")


if __name__ == "__main__":
    main()
