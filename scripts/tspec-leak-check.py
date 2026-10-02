#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 T-spec 原句洩漏檢查 — 被 nk1-guard.sh 第 5 道呼叫。

規則：specs/T-spec/ 下任一檔，若含【連續 ≥30 字元】與 ~/nk1-data/templates 任一
json 的 content 相同 → 擋。

🔑 設計原則：
  ① **fail-closed**：語料找不到、讀不了 → 回非 0。查不了不等於沒問題。
  ② **本腳本不印任何 prompt 內容**——只印檔名、命中數、命中位移。
     ——阿K 不讀 prompt 全文，判準是誰的眼睛看到文字，不是檔案在哪台機器。
  ③ 比對前**移除所有空白**：換行重排、縮排不同都逃不掉（寧可嚴，不可鬆）。

exit：0＝通過　1＝命中（有原句洩漏）　2＝閘自身故障
"""
import json, os, re, sys

WIN = 30                      # 連續字元門檻
CORPUS = os.path.expanduser("~/nk1-data/templates")
WS = re.compile(r"\s+")

def norm(s):
    return WS.sub("", s)

def load_corpus():
    if not os.path.isdir(CORPUS):
        print(f"🔴 T-spec 洩漏閘故障：語料目錄不存在（{CORPUS}）", file=sys.stderr)
        sys.exit(2)
    shingles, nfile, nmsg = set(), 0, 0
    for d, _, fs in os.walk(CORPUS):
        for f in fs:
            if not f.endswith(".json"):
                continue
            try:
                data = json.load(open(os.path.join(d, f), encoding="utf-8"))
            except Exception as e:
                print(f"🔴 T-spec 洩漏閘故障：json 讀取失敗（{f}：{type(e).__name__}）", file=sys.stderr)
                sys.exit(2)
            nfile += 1
            msgs = data if isinstance(data, list) else [data]
            for m in msgs:
                if not isinstance(m, dict):
                    continue
                t = norm(str(m.get("content", "")))
                nmsg += 1
                for i in range(0, max(0, len(t) - WIN + 1)):
                    shingles.add(t[i:i + WIN])
    if nfile == 0:
        print(f"🔴 T-spec 洩漏閘故障：語料目錄內 0 份 json（{CORPUS}）", file=sys.stderr)
        sys.exit(2)
    return shingles, nfile, nmsg

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "specs/T-spec"
    if not os.path.isdir(target):
        print(f"   ⏸ {target}/ 不存在，跳過（尚未產出 T-spec）")
        return 0
    files = [os.path.join(d, f) for d, _, fs in os.walk(target) for f in fs
             if not f.startswith(".")]
    if not files:
        print(f"   ⏸ {target}/ 為空，跳過")
        return 0
    shingles, nfile, nmsg = load_corpus()
    print(f"🔍 T-spec 洩漏閘：語料 {nfile} 份 json／{nmsg} 則 content　"
          f"指紋 {len(shingles)} 枚（{WIN} 字元窗）　對象 {len(files)} 檔")
    bad = 0
    for p in files:
        try:
            raw = open(p, encoding="utf-8", errors="strict").read()
        except UnicodeDecodeError:
            print(f"🔴 T-spec 洩漏閘故障：{p} 非 UTF-8 文字檔，無法比對", file=sys.stderr)
            return 2
        t = norm(raw)
        hits, first = 0, None
        for i in range(0, max(0, len(t) - WIN + 1)):
            if t[i:i + WIN] in shingles:
                hits += 1
                if first is None:
                    first = i
        if hits:
            bad += 1
            # 🔴 只印數字與位移，絕不印命中的文字
            print(f"🔴 FAIL：{p} 含 prompt 原句——命中窗數 {hits}，"
                  f"首次於去空白後第 {first} 字元", file=sys.stderr)
        else:
            print(f"   ✅ {p}：0 命中")
    if bad:
        print(f"🔴 T-spec 洩漏閘【拒絕】：{bad} 檔含 ≥{WIN} 字元 prompt 原句", file=sys.stderr)
        return 1
    print("✅ T-spec 洩漏閘【通過】：0 命中")
    return 0

if __name__ == "__main__":
    sys.exit(main())
