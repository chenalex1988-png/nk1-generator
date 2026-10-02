#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 引用驗證器 CLI v1 — 設計包 §7／§6.1。

用法：
  nk1-verify.py --kb <kb.jsonl> --claims <claims.json> --out <dir> [--fuzzy 0.90]

🔑 三條設計原則：
  ① **零依賴、確定性、無 LLM**：同一組輸入永遠得到同一組輸出，才能當驗收基準。
  ② **不信任輸入端的 text_norm**：一律用本工具的 normalize() 重算——
     兩邊各自正規化，「找不到」會變成正規化差異造成的假陰性。
  ③ **保留主張、標狀態**：找不到依據的 claim **不丟、不補**，標 unsupported／uncited。

exit：0＝全 supported　1＝任一 partial／unsupported／uncited　2＝輸入格式錯或 KB 讀不到

v1.1.0（薄管線 v0.2 契約）：
  - kb.jsonl 增 `status`；**非 effective 者判 unsupported，reason 寫「引用作廢版」**
    🔑 與「ref_id 不存在」分開的理由：**兩者的處置完全不同**——
       前者去換版本，後者去查模型幻覺。折疊成同一句就把 D5 的價值丟掉了。
  - KB 以 **(ref_id, version)** 聯合索引：同一條文的多個版次可並存
  - `clause` 可由 `clause_no` 供應（薄管線 export_kb 直出即可餵，不必改名）
"""
import argparse
import difflib
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nk1_normalize import normalize_with_map, NORMALIZE_VERSION  # noqa: E402

VALIDATOR_VERSION = "1.1.0"
ANCHOR_MIN, ANCHOR_MAX = 3, 8
KB_FIELDS = ("ref_id", "kind", "version", "text_raw", "status")
# `clause` 可由 `clause_no` 供應（薄管線 v0.2：clause←clause_no），兩者至少要有一個
CLAUSE_FIELDS = ("clause", "clause_no")
EFFECTIVE = "effective"


class InputError(Exception):
    """輸入格式錯 → exit 2。與『驗不過』（exit 1）是兩回事，不可混。"""


# ───────────────────────── 載入 ─────────────────────────

def load_kb(path):
    if not os.path.isfile(path):
        raise InputError("KB 檔不存在：%s" % path)
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    kb = {}
    with open(path, encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError as ex:
                raise InputError("KB 第 %d 行不是合法 JSON：%s" % (ln, ex))
            for f in KB_FIELDS:
                if f not in e:
                    raise InputError("KB 第 %d 行缺欄位 %s" % (ln, f))
            if not any(f in e for f in CLAUSE_FIELDS):
                raise InputError("KB 第 %d 行缺 clause（或 clause_no）" % ln)
            e.setdefault("clause", e.get("clause_no"))
            key = (e["ref_id"], e["version"])
            if key in kb:
                raise InputError("KB (ref_id, version) 重複：%s／%s（第 %d 行）"
                                 % (key[0], key[1], ln))
            raw = e["text_raw"]
            norm, imap = normalize_with_map(raw)
            # 🔴 輸入端的 text_norm 一律忽略、重算
            e["text_norm"] = norm
            e["_map"] = imap
            kb[key] = e
    if not kb:
        raise InputError("KB 是空的：%s" % path)
    return kb, sha


def load_claims(path):
    if not os.path.isfile(path):
        raise InputError("claims 檔不存在：%s" % path)
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except ValueError as ex:
        raise InputError("claims 不是合法 JSON：%s" % ex)
    if not isinstance(doc, dict) or "claims" not in doc:
        raise InputError("claims 檔缺頂層 'claims' 陣列")
    if not isinstance(doc["claims"], list):
        raise InputError("'claims' 不是陣列")
    for i, c in enumerate(doc["claims"]):
        if not isinstance(c, dict) or "claim_id" not in c or "text" not in c:
            raise InputError("第 %d 個 claim 缺 claim_id 或 text" % i)
        if "refs" in c and not isinstance(c["refs"], list):
            raise InputError("claim %s 的 refs 不是陣列" % c["claim_id"])
    return doc


# ───────────────────────── 定位三級 ─────────────────────────

def locate(anchor, entry, fuzzy_threshold):
    """回傳 (level, start, end, ratio)；level ∈ exact／normalized／fuzzy／none。
    start／end 一律是 **text_raw 的座標**——回填給人看的是原文，不是正規化字串。"""
    raw = entry["text_raw"]
    pos = raw.find(anchor)
    if pos >= 0:
        return "exact", pos, pos + len(anchor), 1.0

    a_norm, _ = normalize_with_map(anchor)
    t_norm, imap = entry["text_norm"], entry["_map"]
    if not a_norm:
        return "none", None, None, 0.0
    j = t_norm.find(a_norm)
    if j >= 0:
        return "normalized", imap[j], imap[j + len(a_norm) - 1] + 1, 1.0

    # fuzzy：長度 ±2 的滑動視窗，取最佳 ratio
    best = (0.0, None, None)
    L = len(a_norm)
    sm = difflib.SequenceMatcher(autojunk=False)
    sm.set_seq2(a_norm)
    for w in range(max(1, L - 2), L + 3):
        for k in range(0, max(0, len(t_norm) - w) + 1):
            sm.set_seq1(t_norm[k:k + w])
            r = sm.ratio()
            if r > best[0]:
                best = (r, k, k + w)
    if best[1] is not None and best[0] >= fuzzy_threshold:
        s, e = best[1], best[2] - 1
        return "fuzzy", imap[s], imap[min(e, len(imap) - 1)] + 1, best[0]
    return "none", None, None, best[0]


def verify_ref(ref, kb, fuzzy_threshold):
    """單一 ref → (status, 回填欄位 dict)。"""
    out = {"status": "unsupported", "offset_start": None, "offset_end": None,
           "quote": None, "reason": None, "match": None, "ratio": None}
    rid = ref.get("id")
    versions = sorted(v for (r, v) in kb if r == rid)
    if not versions:
        out["reason"] = "ref_id 不存在於 KB：%s" % rid
        return out
    ver = ref.get("version")
    if ver is None:
        if len(versions) > 1:
            out["reason"] = "version 未給，但 KB 有多個版次：%s" % "／".join(versions)
            return out
        ver = versions[0]
    if (rid, ver) not in kb:
        out["reason"] = "version 不符：claim 給 %s，KB 有 %s" % (ver, "／".join(versions))
        return out
    entry = kb[(rid, ver)]
    if entry.get("status") != EFFECTIVE:
        # 🔴 與「不存在」分開：這是版本問題，不是幻覺問題
        out["reason"] = "引用作廢版（status=%s；KB 現有版次 %s）" % (
            entry.get("status"), "／".join(versions))
        return out
    anchor = ref.get("anchor") or ""
    if not (ANCHOR_MIN <= len(anchor) <= ANCHOR_MAX):
        out["reason"] = "錨點長度 %d 不在 %d–%d 之間" % (len(anchor), ANCHOR_MIN, ANCHOR_MAX)
        return out

    level, s, e, ratio = locate(anchor, entry, fuzzy_threshold)
    out["match"], out["ratio"] = level, round(ratio, 4)
    if level in ("exact", "normalized"):
        out["status"] = "supported"
    elif level == "fuzzy":
        out["status"] = "partial"
        out["reason"] = "僅 fuzzy 命中（ratio %.4f ≥ 門檻）" % ratio
    else:
        out["reason"] = "錨點在該條文中找不到（最佳 ratio %.4f）" % ratio
        return out
    out["offset_start"], out["offset_end"] = s, e
    out["quote"] = entry["text_raw"]          # 該條整句
    return out


WORST = {"supported": 0, "partial": 1, "unsupported": 2}


def run(kb_path, claims_path, out_dir, fuzzy_threshold):
    kb, kb_sha = load_kb(kb_path)
    doc = load_claims(claims_path)
    os.makedirs(out_dir, exist_ok=True)

    tally = {"supported": 0, "partial": 0, "unsupported": 0, "uncited": 0}
    rows = []
    for c in doc["claims"]:
        refs = c.get("refs") or []
        if not refs:
            c["status"] = "uncited"
            tally["uncited"] += 1
            rows.append((c["claim_id"], "uncited", "—", "無 ref"))
            continue
        worst = "supported"
        for ref in refs:
            res = verify_ref(ref, kb, fuzzy_threshold)
            ref.update(res)
            if WORST[res["status"]] > WORST[worst]:
                worst = res["status"]
            rows.append((c["claim_id"], res["status"], ref.get("id"),
                         res["reason"] or res["match"]))
        c["status"] = "cited"
        c["ref_status"] = worst
        tally[worst] += 1

    doc["validator_version"] = VALIDATOR_VERSION
    doc["normalize_version"] = NORMALIZE_VERSION
    doc["kb_sha256"] = kb_sha
    doc["fuzzy_threshold"] = fuzzy_threshold
    with open(os.path.join(out_dir, "verified.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2, sort_keys=True)

    total = sum(tally.values())
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as fh:
        w = fh.write
        w("# 引用驗證報告\n\n")
        w("| 標頭 | 值 |\n|---|---|\n")
        w("| validator_version | `%s` |\n" % VALIDATOR_VERSION)
        w("| normalize_version | `%s` |\n" % NORMALIZE_VERSION)
        w("| kb sha256 | `%s` |\n" % kb_sha)
        w("| fuzzy 門檻 | %.2f |\n" % fuzzy_threshold)
        w("| claim 總數 | %d |\n\n" % total)
        w("## 覆蓋率\n\n| 狀態 | 數 | 比例 |\n|---|---:|---:|\n")
        for k in ("supported", "partial", "unsupported", "uncited"):
            pct = (100.0 * tally[k] / total) if total else 0.0
            w("| %s | %d | %.1f%% |\n" % (k, tally[k], pct))
        w("\n## 逐條清單\n\n| claim_id | 狀態 | ref_id | 說明 |\n|---|---|---|---|\n")
        for r in rows:
            w("| %s | %s | %s | %s |\n" % r)
        w("\n> 🔴 **保留主張、標狀態**：unsupported／uncited 的 claim **不丟、不補**。\n")

    if tally["supported"] == total and total > 0:
        return 0, tally
    return 1, tally


def main(argv=None):
    ap = argparse.ArgumentParser(description="NK1 引用驗證器 v%s" % VALIDATOR_VERSION)
    ap.add_argument("--kb", required=True)
    ap.add_argument("--claims", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fuzzy", type=float, default=0.90)
    a = ap.parse_args(argv)
    try:
        rc, tally = run(a.kb, a.claims, a.out, a.fuzzy)
    except InputError as ex:
        sys.stderr.write("🔴 輸入錯誤（exit 2）：%s\n" % ex)
        return 2
    print("supported %(supported)d／partial %(partial)d／unsupported %(unsupported)d／uncited %(uncited)d" % tally)
    print("→ %s/verified.json、%s/report.md（exit %d）" % (a.out, a.out, rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
