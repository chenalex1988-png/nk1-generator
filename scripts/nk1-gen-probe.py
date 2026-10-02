#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 模型形狀驗證（工單【NK1・M3】B 段）— 本地 Ollama 逐節生成，量「形狀」不量品質。

輸入全合成（本檔內建）：
  - 骨架：nk1-skel.py 產的 YAML（只用節序／層級／表格形；節名只送模型、不進報告）
  - 指引句：每節一句合成指引（同一模板）
  - 設備資料表：一台虛構設備 15 欄（值全部虛構）
  - 條號表：5 條虛構法規名＋條號＋合成摘要
呼叫：POST 127.0.0.1:11434/api/chat，format＝JSON schema，temperature 0、seed 固定、num_predict 600、think false。
量：① JSON 合法／body 非空／字數 ② 掃描器 v1.1 五類命中與差集（allow＝資料表∪條號表）
    ③ refs 成員檢查 ④ 同輸入重跑 N 次 body sha256 是否相同 ⑤ 每節秒數、總秒數、ollama 程序 RSS 峰值
    對照（B4）：拿掉資料表再跑一輪。網路（B5）：生成期間取樣 ollama 程序連線，非本機位址即停。
產出：生成品＋原始統計 → ~/nk1-data/gen/<run_id>/（repo 外）；報告 --report（只有數字與表）。
🔴 零真實內容進模型（骨架節名除外，工單明定）；不做品質判斷。

用法：nk1-gen-probe.py --skel SKEL.yaml --model qwen3.5:9b --report reports/X.md [--runs 3]
      nk1-gen-probe.py --report-only ~/nk1-data/gen/<run_id> --report reports/X.md   # 由既有生成品重算並重出報告
"""
import argparse, hashlib, importlib.util, json, os, re, subprocess, sys, threading, time, urllib.request

VERSION = "1.1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
API = "http://127.0.0.1:11434"
SEED = 20260927
NUM_PREDICT = 600
GEN_ROOT = os.path.join(os.path.expanduser("~"), "nk1-data", "gen")

_spec = importlib.util.spec_from_file_location("nk1_closedset", os.path.join(HERE, "nk1-closedset.py"))
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)
_spec2 = importlib.util.spec_from_file_location("nk1_skel2docx", os.path.join(HERE, "nk1-skel2docx.py"))
s2d = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(s2d)

# ── 合成資料（全部虛構）──────────────────────────────────────────
EQUIP = [                                   # 15 欄：7 基本＋5 額定參數（含單位）＋3 驗收項目
    ("名稱", "合成恆溫培養箱"), ("型號", "ZQ-900"), ("資產編號", "SYN-EQ7-042"), ("位置", "合成廠房第三區"),
    ("關鍵性", "高"), ("公用系統", "合成純水迴路"), ("供應商", "虛構儀器股份有限公司"),
    ("額定溫度", "37 ℃"), ("額定轉速", "150 rpm"), ("額定容量", "80 L"), ("額定電壓", "220 V"), ("額定功率", "900 W"),
    ("驗收項目一", "溫度均勻性 ±0.5 ℃"), ("驗收項目二", "升溫時間 30 min"), ("驗收項目三", "警報延遲 10 s"),
]
LAWS = [                                    # 5 條虛構法規：法規名＋條號＋合成摘要
    ("合成規範甲", "第12條", "設備應於使用前完成確認"),
    ("合成規範甲", "第15條", "確認紀錄應予保存"),
    ("合成指引乙", "§ 4.2", "關鍵參數應設定允收範圍"),
    ("合成指引乙", "§ 5.1", "偏差應予調查"),
    ("合成標準丙", "Clause 7.3", "量測儀器應經校正"),
]
GUIDE = "說明本節的目的、適用範圍與執行要點。"
SYSTEM = ("你是設備確效文件的撰寫助手。只根據使用者提供的設備資料表與條號表撰寫；"
          "數值、編號、日期、法規名與條號只能取自這兩張表，表中沒有的不得自行編造。"
          "refs 只能列條號表內的條目。只輸出符合 schema 的 JSON。")
SCHEMA = {"type": "object",
          "properties": {"section_id": {"type": "string"}, "body": {"type": "string"},
                         "refs": {"type": "array", "items": {"type": "object",
                                  "properties": {"law": {"type": "string"}, "clause": {"type": "string"}},
                                  "required": ["law", "clause"]}}},
          "required": ["section_id", "body", "refs"]}


def allow_set(with_table):
    """掃描器 allow：資料表（數值／編號）∪ 條號表（refs）。對照組同樣帶條號表（因為提示也帶）。"""
    nums, ids = [], []
    for _, v in EQUIP:
        nums += [m.group(0) for m in cs.CATS["數值"].finditer(v)]
        ids += cs.find_all("編號", v)
    a = {"refs": [f"{law}{cl}" for law, cl, _ in LAWS]}
    if with_table:
        a["intake"] = {"數值": nums, "編號": ids, "日期": []}
    return a


def user_msg(sid, name, level, tables, with_table):
    d = {"section_id": sid, "節名": name, "層級": level, "本節表格數": len(tables), "指引": GUIDE,
         "條號表": [{"law": l, "clause": c, "摘要": s} for l, c, s in LAWS]}
    if with_table:
        d["設備資料表"] = {k: v for k, v in EQUIP}
    return json.dumps(d, ensure_ascii=False)


def chat(model, content):
    body = {"model": model, "stream": False, "think": False, "format": SCHEMA,
            "options": {"temperature": 0, "seed": SEED, "num_predict": NUM_PREDICT},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]}
    req = urllib.request.Request(API + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        resp = json.load(r)
    return resp, time.time() - t0


# ── 監看：RSS 峰值＋ollama 連線取樣（B3⑤／B5）──────────────────────
class Watch(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.stop, self.peak_kb, self.samples, self.remote, self.local = False, 0, 0, set(), set()

    def run(self):
        while not self.stop:
            ps = subprocess.run(["ps", "-axo", "rss=,comm="], capture_output=True, text=True).stdout
            kb = sum(int(l.split(None, 1)[0]) for l in ps.splitlines() if "ollama" in l.lower() and l.strip())
            self.peak_kb = max(self.peak_kb, kb)
            ls = subprocess.run(["lsof", "-nP", "-i", "-a", "-c", "ollama", "-c", "llama-server"],   # 推論在 llama-server 子程序
                                capture_output=True, text=True).stdout
            self.samples += 1
            for l in ls.splitlines()[1:]:
                m = re.search(r"(TCP|UDP)\s+(\S+)", l)
                if not m:
                    continue
                for ep in re.split(r"->", m.group(2)):
                    host = ep.rsplit(":", 1)[0].strip("[]")
                    (self.local if host in ("127.0.0.1", "::1", "localhost", "*") else self.remote).add(ep)
            if self.remote:
                return
            time.sleep(0.5)


def measure(content, with_table):
    """由模型原始輸出算 ①②③ 欄位（確定性；--report-only 重算用同一支）。"""
    allow = allow_set(with_table)
    law_keys = {cs._ns(l + c) for l, c, _ in LAWS}
    refs_ok = [cs._ns(r) for r in allow["refs"]]
    eq_vals = [cs._ns(v) for _, v in EQUIP] if with_table else []
    try:
        j = json.loads(content)
        ok = isinstance(j, dict) and isinstance(j.get("body"), str) and isinstance(j.get("refs"), list)
    except Exception:
        j, ok = None, False
    body = j.get("body", "") if ok else ""
    row = {"json_ok": ok, "body_nonempty": bool(body.strip()), "chars": len(body),
           "sha": hashlib.sha256(body.encode()).hexdigest()}
    res, _ = cs.scan(body, allow)
    row["hits"] = {k: v["hits"] for k, v in res.items()}
    row["diff"] = {k: v["diff"] for k, v in res.items()}
    # ⑤ 條號差集中「其實是資料表數值的片段」者（如 ±N.N 單位 的 N.N）——掃描器 v1.1 裸 X.Y 規則的誤判，不是模型自編
    cl = {cs._ns(v) for v in cs.find_all("條號", body)}
    row["clause_diff_tblfrag"] = sum(1 for v in cl if not any(v in r for r in refs_ok) and any(v in e for e in eq_vals))
    refs = j.get("refs", []) if ok else []
    row["refs_n"] = len(refs)
    row["refs_in"] = sum(1 for r in refs if isinstance(r, dict)
                         and cs._ns(str(r.get("law", "")) + str(r.get("clause", ""))) in law_keys)
    return row


def run_pass(model, secs, with_table, outdir, tag, watch):
    rows = []
    with open(os.path.join(outdir, f"{tag}.jsonl"), "w", encoding="utf8") as out:
        for s in secs:
            if watch.remote:
                raise SystemExit("🔴 偵測到非本機連線，停止")
            sid = f"S{s['order']:02d}"
            resp, wall = chat(model, user_msg(sid, s["name"], s["level"], s["tables"], with_table))
            content = resp.get("message", {}).get("content", "")
            row = {"sid": sid, "wall_s": round(wall, 2), "eval_count": resp.get("eval_count"),
                   "done_reason": resp.get("done_reason"), **measure(content, with_table)}
            out.write(json.dumps({**row, "raw": content}, ensure_ascii=False) + "\n")
            rows.append(row)
            print(f"   {tag} {sid} {row['wall_s']}s json={ok} chars={row['chars']}", file=sys.stderr)
    return rows


def report_only(gen_dir, report_path):
    """由 stats.json＋各 jsonl 的 raw 重算 ①②③（掃描器現行版），計時與網路沿用 stats.json。"""
    st = json.load(open(os.path.join(gen_dir, "stats.json"), encoding="utf8"))

    def reload(tag, with_table):
        rows = []
        for l in open(os.path.join(gen_dir, f"{tag}.jsonl"), encoding="utf8"):
            r = json.loads(l)
            keep = {k: r[k] for k in ("sid", "wall_s", "eval_count", "done_reason")}
            rows.append({**keep, **measure(r["raw"], with_table)})
        return rows
    st["runs"] = [reload(f"run{i + 1}", True) for i in range(len(st["runs"]))]
    st["control"] = reload("control", False)
    open(report_path, "w", encoding="utf8").write(report(st))
    print(f"✅ 報告重出 {report_path}（來源 {gen_dir}）", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skel")
    ap.add_argument("--model")
    ap.add_argument("--report", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--report-only")
    a = ap.parse_args()
    if a.report_only:
        return report_only(a.report_only, a.report)
    if not (a.skel and a.model):
        ap.error("需 --skel 與 --model（或用 --report-only）")
    skel = s2d.load_skel(a.skel)
    secs = skel["sections"]
    ver = json.load(urllib.request.urlopen(API + "/api/version", timeout=10))["version"]
    tags = json.load(urllib.request.urlopen(API + "/api/tags", timeout=10))["models"]
    minfo = next((m for m in tags if m["name"] == a.model or m["model"] == a.model), None)
    if not minfo:
        raise SystemExit(f"🔴 模型不存在：{a.model}")
    run_id = time.strftime("%Y%m%d-%H%M%S")
    outdir = os.path.join(GEN_ROOT, run_id)
    os.makedirs(outdir)
    w = Watch()
    w.start()
    t0 = time.time()
    runs = [run_pass(a.model, secs, True, outdir, f"run{i + 1}", w) for i in range(a.runs)]
    total_with = time.time() - t0
    t1 = time.time()
    ctrl = run_pass(a.model, secs, False, outdir, "control", w)
    total_ctrl = time.time() - t1
    w.stop = True
    w.join()
    stats = {"run_id": run_id, "ollama": ver, "model": a.model, "digest": minfo.get("digest"),
             "size": minfo.get("size"), "skel_sha8": skel.get("source_sha8"), "sections": len(secs),
             "runs": runs, "control": ctrl, "total_s_per_run": round(total_with / a.runs, 1),
             "total_s_control": round(total_ctrl, 1), "peak_rss_mb": round(w.peak_kb / 1024),
             "net_samples": w.samples, "net_local": sorted(w.local), "net_remote": sorted(w.remote)}
    json.dump(stats, open(os.path.join(outdir, "stats.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    open(a.report, "w", encoding="utf8").write(report(stats))
    print(f"✅ 生成品 {outdir}　報告 {a.report}", file=sys.stderr)
    if w.remote:
        sys.exit(1)


def report(st):
    cats = list(cs.CATS)
    r1, runs, ctrl = st["runs"][0], st["runs"], st["control"]
    same = [len({r[i]["sha"] for r in runs}) == 1 for i in range(len(r1))]
    L = [f"# NK1 模型形狀驗證 — 9B（{st['run_id'][:4]}-{st['run_id'][4:6]}-{st['run_id'][6:8]}）", "",
         "| 標頭 | 值 |", "|---|---|",
         f"| 腳本 | `scripts/nk1-gen-probe.py` v{VERSION}；掃描器 `nk1-closedset.py` v1.1 |",
         f"| 引擎 | Ollama {st['ollama']}（僅綁 127.0.0.1:11434） |",
         f"| 模型 | `{st['model']}`　digest `{st['digest']}`　{st['size'] / 1e9:.2f} GB |",
         f"| 參數 | temperature 0、seed {SEED}、num_predict {NUM_PREDICT}、think false、format＝JSON schema |",
         f"| 骨架 | T027 v1.1 骨架 `source_sha8={st['skel_sha8']}`，{st['sections']} 節（節名不列） |",
         "| 輸入 | 指引句／設備資料表 15 欄／條號表 5 條：**全合成**（值不列） |",
         f"| 生成品 | `~/nk1-data/gen/{st['run_id']}/`（repo 外） |",
         "| 內容規則 | 只有數字與表；零 body 原文、零合成資料表原值；**不做品質判斷** |", "",
         "---", "", "## B3 ①–⑤ 逐節（第 1 輪；④ 為 3 輪比對）", "",
         "| 節 | JSON 合法 | body 非空 | 字數 | " + " | ".join(f"{c} 命中/差集" for c in cats)
         + " | refs 在表/總 | ④ 3 輪 sha 同 | 秒 |",
         "|---|---|---|---:|" + "---:|" * len(cats) + "---:|---|---:|"]
    for i, r in enumerate(r1):
        L.append(f"| {r['sid']} | {'✓' if r['json_ok'] else '✗'} | {'✓' if r['body_nonempty'] else '✗'} | {r['chars']} | "
                 + " | ".join(f"{r['hits'][c]}/{r['diff'][c]}" for c in cats)
                 + f" | {r['refs_in']}/{r['refs_n']} | {'✓' if same[i] else '✗'} | {r['wall_s']} |")
    n = len(r1)
    tot = lambda rows, k, c: sum(x[k][c] for x in rows)
    L += ["", "**合計（第 1 輪）**", "",
          "| 項 | 值 |", "|---|---|",
          f"| ① JSON 合法 | {sum(r['json_ok'] for r in r1)}/{n} |",
          f"| ① body 非空 | {sum(r['body_nonempty'] for r in r1)}/{n} |",
          f"| ① 字數 min／中位／max | {min(r['chars'] for r in r1)}／{sorted(r['chars'] for r in r1)[n // 2]}／{max(r['chars'] for r in r1)} |",
          f"| ① 觸頂 num_predict（done_reason=length） | {sum(1 for r in r1 if r['done_reason'] == 'length')}/{n} |",
          "| ② 五類命中／差集 | " + "；".join(f"{c} {tot(r1, 'hits', c)}/{tot(r1, 'diff', c)}" for c in cats) + " |",
          f"| ② 差集合計 | {sum(tot(r1, 'diff', c) for c in cats)} |",
          f"| ② 其中條號差集＝資料表數值片段（掃描器誤判，非模型自編） | {sum(r['clause_diff_tblfrag'] for r in r1)} |",
          f"| ② **扣除上列後＝模型自編** | **{sum(tot(r1, 'diff', c) for c in cats) - sum(r['clause_diff_tblfrag'] for r in r1)}** |",
          f"| ③ refs 全在條號表的節 | {sum(1 for r in r1 if r['refs_in'] == r['refs_n'])}/{n}（refs 總數 {sum(r['refs_n'] for r in r1)}，在表 {sum(r['refs_in'] for r in r1)}） |",
          f"| ④ {len(runs)} 輪 body sha 全同的節 | {sum(same)}/{n} |",
          f"| ⑤ 每篇總秒數（{len(runs)} 輪平均） | {st['total_s_per_run']} |",
          f"| ⑤ 每節秒數 min／max | {min(r['wall_s'] for r in r1)}／{max(r['wall_s'] for r in r1)} |",
          f"| ⑤ ollama＋llama-server 程序 RSS 峰值（合計） | {st['peak_rss_mb']} MB |", "",
          "---", "", "## B4 對照：拿掉設備資料表（只給骨架＋指引句＋條號表）", "",
          "| 類 | 有資料表 命中/差集 | 無資料表 命中/差集 |", "|---|---:|---:|"]
    for c in cats:
        L.append(f"| {c} | {tot(r1, 'hits', c)}/{tot(r1, 'diff', c)} | {tot(ctrl, 'hits', c)}/{tot(ctrl, 'diff', c)} |")
    fr = lambda rows: sum(r["clause_diff_tblfrag"] for r in rows)
    L += [f"| **差集合計** | **{sum(tot(r1, 'diff', c) for c in cats)}** | **{sum(tot(ctrl, 'diff', c) for c in cats)}** |",
          f"| 其中條號差集＝資料表數值片段（掃描器誤判） | {fr(r1)} | {fr(ctrl)} |",
          f"| **模型自編（扣除誤判）** | **{sum(tot(r1, 'diff', c) for c in cats) - fr(r1)}** | **{sum(tot(ctrl, 'diff', c) for c in cats) - fr(ctrl)}** |",
          f"| 有差集的節數 | {sum(1 for r in r1 if sum(r['diff'].values()))}/{n} | {sum(1 for r in ctrl if sum(r['diff'].values()))}/{n} |",
          f"| JSON 合法 | {sum(r['json_ok'] for r in r1)}/{n} | {sum(r['json_ok'] for r in ctrl)}/{n} |",
          f"| 總秒數 | {st['total_s_per_run']} | {st['total_s_control']} |", "",
          "📌 對照組 allow 只有條號表（資料表不在提示裡，也不在 allow 裡）。", "",
          "---", "", "## B5 網路", "",
          "| 項 | 值 |", "|---|---|",
          f"| 取樣（lsof -i -c ollama -c llama-server，每 0.5 s） | {st['net_samples']} 次 |",
          f"| 本機端點（相異） | {len(st['net_local'])} 個；"
          f"{'全為 127.0.0.1' if all(e.startswith('127.0.0.1:') for e in st['net_local']) else '⚠️ 含非 127.0.0.1 的本機位址'} |",
          f"| **非本機端點** | **{len(st['net_remote'])}** {', '.join(st['net_remote'])} |", ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
