#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 schema 驗證器（工單【NK1・M1.1】B2／B3）— 零依賴。

  nk1-intake-validate.py --spec specs/intake_v0.yaml [--data 實例.json]     # 資料表規格（＋實例）
  nk1-intake-validate.py --guides specs/guides/T027_v0.yaml --sections 37
  nk1-intake-validate.py --refs specs/refs/annex15_v0.yaml
輸出只列錯誤類型與欄位鍵，不回顯欄位值。exit：0＝通過　1＝不合規　2＝讀檔失敗
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nk1_flowyaml as fy  # noqa: E402

VERSION = "1.2.0"
TYPES = {"str", "date", "list_str", "params", "acceptance", "accept", "method", "method_pq"}
METHOD_KEYS = ("measure_points", "instruments_calibration", "sampling_frequency", "runs")
METHOD_PQ_KEYS = METHOD_KEYS + ("load_definition",)
ITEM_KEYS = {"params": ("name", "value", "unit", "range"), "acceptance": ("item", "method", "criteria"),
             "accept": ("item", "criterion")}
FIELD_COUNT = {"0": 18, "0.5": 20, "0.6": 26}           # 版本 → 應有欄數
V06_REQUIRED = ("accept_iq", "accept_oq", "accept_pq", "method_iq", "method_oq", "method_pq", "deviation_sop")
SEGMENT_FIELDS = ("accept_iq", "accept_oq", "accept_pq")  # v0.5：三段允收，缺一即拒
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def check_spec(spec):
    errs = []
    fields = spec.get("fields") or []
    n = int(spec.get("skel_sections") or 0)
    want = FIELD_COUNT.get(str(spec.get("version")), 18)
    if len(fields) != want:
        errs.append(f"欄數 {len(fields)}≠{want}")
    if str(spec.get("version")) in ("0.5", "0.6"):
        keyset = {f.get("key") for f in fields}
        for k in (V06_REQUIRED if str(spec.get("version")) == "0.6" else SEGMENT_FIELDS):
            if k not in keyset:
                errs.append(f"缺必要欄：{k}")
    if str(spec.get("version")) == "0.6":
        for f in fields:
            if not f.get("uses"):
                errs.append(f"{f.get('key')}: 缺 uses（用途標籤）")
    keys = [f.get("key") for f in fields]
    if len(set(keys)) != len(keys):
        errs.append("key 重複")
    for f in fields:
        k = f.get("key")
        if f.get("type") not in TYPES:
            errs.append(f"{k}: type 不合法")
        if f.get("type") in ITEM_KEYS and not isinstance(f.get("max"), int):
            errs.append(f"{k}: 缺 max")
        secs = f.get("sections")
        if not secs or not all(isinstance(s, int) and 1 <= s <= n for s in secs):
            errs.append(f"{k}: sections 缺或超出 1..{n}")
    return errs


def check_data(spec, data):
    errs = []
    for f in spec["fields"]:
        k, t, v = f["key"], f["type"], data.get(f["key"])
        empty = v is None or v == "" or v == []
        if empty:
            if f.get("required"):
                errs.append(f"{k}: 必填缺")
            continue
        if t in ("str",) and not isinstance(v, str):
            errs.append(f"{k}: 應為字串")
        elif t == "date" and not (isinstance(v, str) and RE_DATE.match(v)):
            errs.append(f"{k}: 日期格式應為 YYYY-MM-DD")
        elif t == "list_str" and not (isinstance(v, list) and all(isinstance(x, str) and x for x in v)):
            errs.append(f"{k}: 應為非空字串清單")
        elif t in ("method", "method_pq"):
            need = METHOD_PQ_KEYS if t == "method_pq" else METHOD_KEYS
            miss = [x for x in need if not (isinstance(v, dict) and isinstance(v.get(x), str) and v.get(x))]
            if miss:
                errs.append(f"{k}: 缺 {','.join(miss)}")
        elif t in ITEM_KEYS:
            if not isinstance(v, list) or len(v) > f["max"] or len(v) < f.get("min", 0):
                errs.append(f"{k}: 應為清單且 {f.get('min', 0)}–{f['max']} 組")
            else:
                for i, it in enumerate(v, 1):
                    miss = [x for x in ITEM_KEYS[t] if not (isinstance(it, dict) and isinstance(it.get(x), str) and it.get(x))]
                    if miss:
                        errs.append(f"{k}[{i}]: 缺 {','.join(miss)}")
    extra = set(data) - {f["key"] for f in spec["fields"]} - {"_note"}
    if extra:
        errs.append(f"未定義欄位：{','.join(sorted(extra))}")
    return errs


def check_guides(g, n):
    errs = []
    orders = [x.get("order") for x in g.get("guides") or []]
    if sorted(orders) != list(range(1, n + 1)):
        errs.append(f"order 應恰為 1..{n} 各一句（實得 {len(orders)} 句）")
    for x in g.get("guides") or []:
        s = x.get("guide") or ""
        if not s.startswith("本節說明"):
            errs.append(f"order {x.get('order')}: 應以「本節說明」開頭")
        if len(s) > 40 or s.count("。") != 1 or not s.endswith("。"):
            errs.append(f"order {x.get('order')}: 應為一句（≤40 字、句號結尾）")
    return errs


ITEMS7 = ("器具材料", "方法步驟", "允收標準", "超標處理", "測試結果", "結果判定", "備註")
SEGS = {"iq": "安裝驗證", "oq": "操作驗證", "pq": "性能驗證"}
RE_CN_NUM = re.compile(r"[一二三四五六七八九十百千萬零兩]+[點區個項次批組段層道]")


def check_guides_v05(g, common_orders=(1, 2, 3, 4, 5, 6, 34, 35, 36, 37), result_order=34):
    """v0.5 分段索引：common 恰為指定 order；三段各 _head／_test／七項子節；驗證結果節明列三段名；段別定義齊。"""
    errs = []
    com = {x.get("order"): x.get("guide", "") for x in g.get("common") or []}
    if sorted(com) != sorted(common_orders):
        errs.append(f"common order 應為 {list(common_orders)}")
    sg = {}
    for x in g.get("segment_guides") or []:
        sg.setdefault(x.get("segment"), {})[x.get("item")] = x.get("guide", "")
    for s in SEGS:
        need = ("_head", "_test") + ITEMS7
        miss = [k for k in need if k not in sg.get(s, {})]
        if miss:
            errs.append(f"{s}: 缺 {','.join(miss)}")
        extra = [k for k in sg.get(s, {}) if k not in need]
        if extra:
            errs.append(f"{s}: 多出 {','.join(extra)}")
    defs = {x.get("segment") for x in g.get("segment_defs") or []}
    if defs != set(SEGS):
        errs.append("segment_defs 應恰含 iq／oq／pq")
    allg = list(com.values()) + [v for d in sg.values() for v in d.values()]
    for t in allg:
        if not t.startswith("本節說明") or not t.endswith("。") or len(t) > 90:
            errs.append("指引句應以「本節說明」開頭、句號結尾、≤90 字")
            break
    if any(RE_CN_NUM.search(t) for t in allg):
        errs.append("指引句含中文數字＋量詞（會觸發中文數字閘）")
    r = com.get(result_order, "")
    if not all(n in r for n in SEGS.values()) or "逐段" not in r:
        errs.append(f"order {result_order}（驗證結果）應明列三段名並要求逐段結論")
    return errs


def check_refs_v1(d, offrepo=None):
    """條號表 v1（JSON）：v0 欄位＋版次／來源／原文／中譯／對應；repo 外原文須 sha256 相符。"""
    errs = check_refs(d)
    import hashlib
    off = json.load(open(os.path.expanduser(offrepo), encoding="utf8")) if offrepo else {}
    for x in d.get("refs") or []:
        c = x.get("clause")
        for k in ("version", "source", "translation_version", "doc_types", "sections", "pe009_18_check"):
            if not x.get(k):
                errs.append(f"{c}: 缺 {k}")
        if x.get("original") is not None and x.get("original_sha256") != hashlib.sha256(x["original"].encode()).hexdigest():
            errs.append(f"{c}: original_sha256 不符")
        for k in ("original", "translation_zh"):
            if x.get(k) is None:
                o = x.get(k + "_off_repo")
                if not o:
                    errs.append(f"{c}: {k} 缺且無 repo 外指標")
                elif offrepo and hashlib.sha256((off.get(c, {}).get(k) or "").encode()).hexdigest() != o.get("sha256"):
                    errs.append(f"{c}: {k} repo 外全文 sha256 不符")
    if not d.get("not_included"):
        errs.append("缺「候選但未納」段")
    return errs


def check_refs(r):
    errs = []
    refs = r.get("refs") or []
    if len(refs) < 30:
        errs.append(f"條數 {len(refs)}<30")
    seen = set()
    for x in refs:
        for k in ("law", "clause", "title", "stage"):
            if not x.get(k):
                errs.append(f"{x.get('clause')}: 缺 {k}")
        if not re.fullmatch(r"\d{1,2}\.\d{1,2}", str(x.get("clause", ""))):
            errs.append(f"{x.get('clause')}: 條號格式")
        if len(str(x.get("title", ""))) > 80:
            errs.append(f"{x.get('clause')}: 標題超過一行（>80 字元）")
        seen.add(x.get("stage"))
    miss = {"URS", "DQ", "IQ", "OQ", "PQ", "變更", "再確效"} - seen
    if miss:
        errs.append(f"缺階段：{','.join(sorted(miss))}")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec")
    ap.add_argument("--data")
    ap.add_argument("--guides")
    ap.add_argument("--sections", type=int)
    ap.add_argument("--refs")
    ap.add_argument("--offrepo", help="條號表 v1 的 repo 外全文檔（驗 sha256）")
    a = ap.parse_args()
    errs, done = [], []
    try:
        if a.spec:
            spec = fy.load(a.spec)
            errs += check_spec(spec)
            done.append("spec")
            if a.data:
                errs += check_data(spec, json.load(open(a.data, encoding="utf8")))
                done.append("data")
        if a.guides:
            gd = fy.load(a.guides)
            errs += check_guides_v05(gd) if str(gd.get("version")) in ("0.5", "0.6", "0.7") else check_guides(gd, a.sections)
            if str(gd.get("version")) == "0.7":
                nf = sum(1 for x in gd["segment_guides"] if x.get("fixed")) + sum(1 for x in gd["common"] if x.get("fixed"))
                if nf != 7:
                    errs.append(f"v0.7 應有 7 個 fixed（三段×測試結果／結果判定＋驗證結果），實得 {nf}")
            if str(gd.get("version")) in ("0.6", "0.7"):
                bad = [x["segment"] for x in gd["segment_guides"] if x["item"] == "超標處理" and "偏差處理" not in x["guide"]]
                if bad:
                    errs.append(f"v0.6 超標處理指引未指向偏差處理 SOP：{bad}")
            done.append("guides")
        if a.refs:
            errs += (check_refs_v1(json.load(open(a.refs, encoding="utf8")), a.offrepo) if a.refs.endswith(".json")
                     else check_refs(fy.load(a.refs)))
            done.append("refs")
    except Exception as e:
        print(f"🔴 讀檔失敗：{type(e).__name__}", file=sys.stderr)
        sys.exit(2)
    for e in errs:
        print(f"   ✗ {e}")
    print(f"{'✅ 通過' if not errs else '🔴 不合規'}（{'＋'.join(done)}；錯誤 {len(errs)}）")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
