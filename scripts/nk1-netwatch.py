#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 連線監看器（工單【NK1・M4 恢復】B）— **先於 ollama 啟動**，全程取樣，事後分段彙整。

律候選（decisions 2026-09-27）：執行期零外連須由 OS 層斷網或「自程序啟動起」的全程監看證明；runtime 設定不算證據。
故本監看器與被監看程序分離：先起監看、後起 ollama、結束時先停 ollama、後停監看。

  nk1-netwatch.py watch --log L.jsonl --stop-file STOP [--interval 0.5]
      每 interval 秒以 `lsof -nP -i -a -c ollama -c llama-server` 取樣，每次一行 JSON：
      {"t": 時間戳, "pids": [...], "conns": [[cmd, pid, 端點], ...]}；STOP 檔出現即結束。
  nk1-netwatch.py mark --phases P.jsonl NAME            # 記一個分段起點
  nk1-netwatch.py summary --log L.jsonl --phases P.jsonl [--md]
      依分段彙整：取樣數、有 ollama 程序的取樣數、本機端點數、**非 127.0.0.1／::1 端點清單**。
限制：取樣式，存活短於 interval 的連線可能漏網（summary 會註明）。
exit（summary）：0＝全段零外連　1＝有外連
"""
import argparse, json, os, re, subprocess, sys, time

LOCAL = ("127.0.0.1", "::1", "localhost", "*")


def sample():
    ls = subprocess.run(["lsof", "-nP", "-i", "-a", "-c", "ollama", "-c", "llama-server"],
                        capture_output=True, text=True).stdout
    conns, pids = [], set()
    for l in ls.splitlines()[1:]:
        f = l.split()
        if len(f) < 9:
            continue
        pids.add(int(f[1]))
        m = re.search(r"(TCP|UDP)\s+(\S+)", l)
        if m:
            conns.append([f[0], int(f[1]), m.group(2)])
    return sorted(pids), conns


def watch(a):
    with open(a.log, "a", encoding="utf8") as out:
        while not os.path.exists(a.stop_file):
            pids, conns = sample()
            out.write(json.dumps({"t": round(time.time(), 2), "pids": pids, "conns": conns}) + "\n")
            out.flush()
            time.sleep(a.interval)


def mark(a):
    with open(a.phases, "a", encoding="utf8") as f:
        f.write(json.dumps({"t": round(time.time(), 2), "phase": a.name}, ensure_ascii=False) + "\n")


def is_remote(ep):
    for side in ep.split("->"):
        host = side.rsplit(":", 1)[0].strip("[]")
        if host not in LOCAL:
            return True
    return False


def summary(a):
    rows = [json.loads(l) for l in open(a.log, encoding="utf8")]
    ph = [json.loads(l) for l in open(a.phases, encoding="utf8")]
    bounds = [(p["phase"], p["t"], ph[i + 1]["t"] if i + 1 < len(ph) else float("inf")) for i, p in enumerate(ph)]
    pre = [r for r in rows if r["t"] < ph[0]["t"]]
    out, total_remote = [], 0
    segs = [("（監看先起、首個分段前）", float("-inf"), ph[0]["t"])] + bounds
    for name, t0, t1 in segs:
        rs = [r for r in rows if t0 <= r["t"] < t1]
        loc, rem = set(), {}
        for r in rs:
            for cmd, pid, ep in r["conns"]:
                if is_remote(ep):
                    rem.setdefault(ep, [cmd, pid, r["t"]])
                else:
                    loc.add(ep)
        total_remote += len(rem)
        span = (rs[-1]["t"] - rs[0]["t"]) if len(rs) > 1 else 0
        out.append({"phase": name, "samples": len(rs), "with_proc": sum(1 for r in rs if r["pids"]),
                    "span_s": round(span), "local_n": len(loc), "remote": rem})
    interval = round((rows[-1]["t"] - rows[0]["t"]) / max(len(rows) - 1, 1), 2) if len(rows) > 1 else None
    if a.md:
        print("| 分段 | 取樣 | 有程序的取樣 | 歷時 s | 本機端點 | **非本機端點** |")
        print("|---|---:|---:|---:|---:|---|")
        for s in out:
            rem = "；".join(f"{ep}（{v[0]} {v[1]}）" for ep, v in s["remote"].items()) or "0"
            print(f"| {s['phase']} | {s['samples']} | {s['with_proc']} | {s['span_s']} | {s['local_n']} | **{rem}** |")
        print(f"\n平均取樣間隔 {interval} s；監看首筆早於首個分段 {len(pre)} 筆。限制：存活短於取樣間隔的連線可能漏網。")
    else:
        print(json.dumps({"segments": out, "interval": interval, "pre_samples": len(pre)}, ensure_ascii=False, indent=1))
    sys.exit(1 if total_remote else 0)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("watch")
    w.add_argument("--log", required=True)
    w.add_argument("--stop-file", required=True)
    w.add_argument("--interval", type=float, default=0.5)
    m = sub.add_parser("mark")
    m.add_argument("--phases", required=True)
    m.add_argument("name")
    s = sub.add_parser("summary")
    s.add_argument("--log", required=True)
    s.add_argument("--phases", required=True)
    s.add_argument("--md", action="store_true")
    a = ap.parse_args()
    {"watch": watch, "mark": mark, "summary": summary}[a.cmd](a)


if __name__ == "__main__":
    main()
