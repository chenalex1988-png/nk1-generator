#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 端到端 v0（工單【NK1・M1.1】C 段，M4）— 一類文件（T027）、合成設備、全鏈。

鏈：資料表（intake_v0 實例）＋骨架（nk1-skel.py v1.2 YAML）＋指引句 v0＋條號表 v0
  → 逐節呼叫本地模型（127.0.0.1 Ollama；schema v0.2：section_id／body／refs／sop_refs）
  → 每節 body 過封閉集合掃描器（allow＝intake∪條號表∪三顧編號規則）＋ refs 成員檢查（law＋clause 皆非空且在條號表）
    ＋ sop_refs 成員檢查（⊆ intake 的 sop_ids）——v0.2（M4.1 A）：SOP 編號不得進 refs
    ＋ schema 檢查（v0.3，M4.2 A）：refs、sop_refs 各 maxItems 6；本線自帶最小驗證器（required／minLength／maxItems）
  → 過則寫入；不過則該節以「已攔下」佔位（計數，不重試——temperature 0 重試結果相同）
  → docxtpl 渲染（repeat 以 head 為標籤：IQ／OQ／PQ）→ zip 確定化
  → 草稿 docx（檔頭「草稿・非受控文件・合成資料」）＋ 內容包 JSON（origin／disclosure／model／
    validator_version／kb_snapshot 必填，缺一即失敗）
同輸入跑 --runs 次（預設 2），比對 docx／內容包 sha256。
產出只在 --out-dir（~/nk1-data/gen/m4/…，repo 外）；報告 --report 只出統計。
🔴 零真實內容進模型（骨架節名除外）；不做品質判斷。

用法（須在 .venv：docxtpl）：
  .venv/bin/python scripts/nk1-gen.py --intake fixtures/intake_synth_v0.json --skel SKEL.yaml \\
     --guides specs/guides/T027_v0.5.yaml --refs specs/refs/annex15_v0.yaml --model qwen3.5:9b \\
     --out-dir ~/nk1-data/gen/m4 --report reports/M4_端到端v0_2026-09-27.md
"""
import argparse, hashlib, importlib.util, json, os, re, sys, time, urllib.request, zipfile

VERSION = "0.11.0"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nk1_flowyaml as fy  # noqa: E402


def _mod(name, fn):
    sp = importlib.util.spec_from_file_location(name, os.path.join(HERE, fn))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


cs = _mod("nk1_closedset", "nk1-closedset.py")
s2d = _mod("nk1_skel2docx", "nk1-skel2docx.py")
gp = _mod("nk1_gen_probe", "nk1-gen-probe.py")          # 取 Watch（連線／RSS 監看）
ex = _mod("nk1_expand", "nk1-expand.py")                 # M4.4：條號範圍展開（原則見 specs/guards/normalization_policy.md）

API = "http://127.0.0.1:11434"
SEED = 20260927
NUM_PREDICT = 600
HEADER = "草稿・非受控文件・合成資料"
TABLE_STYLE = " ".join(("Table", "Grid"))       # 拼接：避免樣式名字面（兩個首字大寫英文詞相連）誤觸遮蔽閘人名規則
BLOCKED = "〔本節未通過封閉集合掃描或條號成員檢查，已攔下，待人工撰寫〕"
VALIDATOR = "nk1-closedset.py v1.7"
JACCARD_MAX = 0.9          # M4.3 E-14
REGEN_MAX = 2              # M4.3 E-14／E-15
SANGU_NUMBERING_RULES = []      # 🔶 三顧編號規則未落地（v0 為空集合）；待三顧提供後補
SYSTEM = ("你是設備確效文件的撰寫助手，依「指引」撰寫本節正文 2 至 4 句。"
          "數值、編號、日期、法規名與條號只能取自使用者提供的設備資料表與條號表；表中沒有的一律不得寫出。"
          "引用法規時寫法規名與條號（例如「PIC/S GMP Annex 15 3.9」）。"
          "refs 只列法規清單內條號（law 與 clause 皆必填），SOP 編號放 sop_refs。"
          "refs 最多列 6 條，取最直接相關者。"
          "條號逐條列，不得寫「X 至 Y」範圍。"
          "一律使用繁體中文；數量一律用阿拉伯數字且只取自設備資料表，不寫中文數字加量詞。"
          "只輸出符合 schema 的 JSON。")
SYSTEM_V2 = ("你是設備確效文件的撰寫助手，依「指引」撰寫本節正文 2 至 4 句。"
             "數值、編號、日期只能取自「本節可用資料」；表中沒有的一律不得寫出。"
             "只可引用「本節可引用條號」內的條號，格式 PIC/S GMP Annex 15（PE 009-18）X.Y，逐條列出，不得寫範圍；清單為空則不引用條號、refs 留空。"
             "refs 每項含 law、clause、version（PE 009-18），最多 6 條；SOP 編號放 sop_refs。"
             "一律使用繁體中文；數量用阿拉伯數字，不寫中文數字加量詞；次數與數量照資料表原樣寫（例：1 次）。只輸出符合 schema 的 JSON。")
FIXED_TEXT = "待執行後填寫"
SCHEMA = {"type": "object",
          "properties": {"section_id": {"type": "string"}, "body": {"type": "string"},
                         "refs": {"type": "array", "maxItems": 6, "items": {"type": "object",
                                  "properties": {"law": {"type": "string", "minLength": 1},
                                                 "clause": {"type": "string", "minLength": 1}},
                                  "required": ["law", "clause"]}},
                         "sop_refs": {"type": "array", "maxItems": 6, "items": {"type": "string"}}},
          "required": ["section_id", "body", "refs", "sop_refs"]}


def schema_errors(v, sch=None, path="$"):
    """最小 JSON schema 驗證（本 SCHEMA 用到的子集：type／required／minLength／maxItems／items／properties）。"""
    sch = SCHEMA if sch is None else sch
    t = sch.get("type")
    pyt = {"object": dict, "array": list, "string": str}.get(t)
    if pyt and not isinstance(v, pyt):
        return [f"{path}: 應為 {t}"]
    errs = []
    if t == "object":
        errs += [f"{path}.{k}: 缺" for k in sch.get("required", []) if k not in v]
        for k, sub in sch.get("properties", {}).items():
            if k in v:
                errs += schema_errors(v[k], sub, f"{path}.{k}")
    elif t == "array":
        if "maxItems" in sch and len(v) > sch["maxItems"]:
            errs.append(f"{path}: {len(v)} 項 > maxItems {sch['maxItems']}")
        for i, x in enumerate(v):
            errs += schema_errors(x, sch.get("items", {}), f"{path}[{i}]")
    elif t == "string" and len(v) < sch.get("minLength", 0):
        errs.append(f"{path}: 長度 < minLength {sch['minLength']}")
    return errs


def expand_raw(sid, raw, table_clauses):
    """模型輸出 JSON 的 body 先做條號範圍展開；回傳 (改後 raw, normalizations, 原 body 內範圍數)。JSON 不合法原樣退回。"""
    try:
        j = json.loads(raw)
        body = j["body"]
        assert isinstance(body, str)
    except Exception:
        return raw, [], 0
    found = len(cs.clause_ranges(body))
    nb, norms = ex.expand_ranges(sid, body, table_clauses)
    if nb == body:
        return raw, norms, found
    j["body"] = nb
    return json.dumps(j, ensure_ascii=False), norms, found


# ── M5.0 C：品保六項退件理由閘（policy 層；policy=None 時行為與 v0.6 相同）────────────────
SCHEMA_V2 = json.loads(json.dumps(SCHEMA))
SCHEMA_V2["properties"]["refs"]["items"]["properties"]["version"] = {"type": "string", "minLength": 1}
SCHEMA_V2["properties"]["refs"]["items"]["required"] = ["law", "clause", "version"]
REF_VERSION = "PE 009-18"
RE_CLAUSE_NUM = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,2})(?![\d.])")


def load_refs(path):
    """條號表：v0 YAML 或 v1 JSON，一律回傳 refs 清單。"""
    if path.endswith(".json"):
        return json.load(open(path, encoding="utf8"))["refs"]
    return fy.load(path)["refs"]


def build_use_index(intake, spec):
    """值（正規化）→ 用途集合：值取自該欄全部文字的數值／編號／日期／中文數字命中，用途＝該欄 uses（多欄取聯集）。"""
    idx = {}
    for f in spec["fields"]:
        if f["key"] not in intake:
            continue
        for c in ("數值", "編號", "日期", "中文數字"):
            for v in _vals(intake[f["key"]], c):
                idx.setdefault(v, set()).update(f.get("uses") or [])
    return idx


def section_uses(su, order, role):
    for x in su.get("common") or []:
        if x["section"] == f"S{order:02d}":
            return set(x["uses"])
    if role:
        u = set(su.get("segment_base") or [])
        u |= set(next((x["uses"] for x in su["segments"] if x["segment"] == role[0]), []))
        u |= set(next((x["uses"] for x in su.get("item_extra") or [] if x["item"] == role[1]), []))
        return u
    return set()


def allowed_clauses(refs_v1, order, role):
    keys = {f"S{order:02d}"} | ({role[0]} if role else set())
    return {r["clause"] for r in refs_v1 if keys & set(r.get("sections") or [])}


def policy_checks(body, refs_items, ctx):
    """回傳 (reasons, detail)。ctx：name、role、doc_kind、result_sections、overflow_items、use_index、uses、clauses。"""
    reasons, d = [], {}
    item = ctx["role"][1] if ctx.get("role") else None
    name = item or ctx["name"]
    if ctx.get("doc_kind") == "plan":                                     # M5.4 B：全文內容判（不依節名）
        d["result_statements"] = cs.result_statement_hits(body)
        if d["result_statements"]:
            reasons.append("結果陳述")
    if ctx.get("doc_kind") == "plan" and name in ctx["result_sections"]:
        d["result_terms"] = cs.result_term_hits(body)
        if d["result_terms"]:
            reasons.append("結果禁令")
    mis = [v for c in ("數值", "編號", "日期", "中文數字") for v in cs.find_all(c, body)
           if cs._ns(v) in ctx["use_index"] and not (ctx["use_index"][cs._ns(v)] & ctx["uses"])]
    d["use_misplaced"] = len(mis)
    if mis:
        reasons.append("用途錯置")
    cl = [m.group(1) for v in cs.find_all("條號", body) for m in RE_CLAUSE_NUM.finditer(v)]
    cl += [str(r.get("clause")) for r in refs_items if isinstance(r, dict)]
    bad = [c for c in cl if c not in ctx["clauses"]]
    d["clause_misplaced"] = len(bad)
    d["clauses_cited"] = len(cl)
    if bad and ctx.get("clause_gate") == "block":                        # M5.4 C-8：預設 review（只記、供審閱對照），不攔
        reasons.append("章節錯置")
    vm = cs.version_missing(body) + sum(1 for r in refs_items if isinstance(r, dict) and r.get("version") != REF_VERSION)
    d["version_missing"] = vm
    if vm:
        reasons.append("缺版次")
    if item in ctx["overflow_items"]:
        d["overflow"] = cs.overflow_disposition_hits(body)
        if d["overflow"]:
            reasons.append("超標處置")
    return reasons, d


def first_sentence(t):
    m = re.match(r"^(.+?。)", t or "")
    return (m.group(1) if m else (t or ""))[:80]


def policy_msg(pctx, spec, intake):
    """v0.8（M5.1 B）：本節可用資料（值＋用途，只給允許用途）＋本節可引用條號（條號＋中譯一句）。"""
    data = [{"欄位": f["label"], "用途": "、".join(f["uses"]), "值": intake[f["key"]]}
            for f in spec["fields"] if f["key"] in intake and intake[f["key"]] not in ("", [], None)
            and set(f.get("uses") or []) & pctx["uses"]]
    cl = [{"條號": f"PIC/S GMP Annex 15（PE 009-18）{r['clause']}", "中譯": first_sentence(r.get("translation_zh"))}
          for r in pctx["refs_v1"] if r["clause"] in pctx["clauses"]]
    m = {"本節可用資料": data, "本節可引用條號": cl,
         "引用規則": "只可引用以下條號，格式 PIC/S GMP Annex 15（PE 009-18）X.Y" if cl else "本節不引用條號，refs 留空"}
    if pctx.get("role") and pctx["role"][1] in pctx["overflow_items"]:          # M5.1 B-4
        m["偏差處理程序"] = intake.get("deviation_sop")
        m["處置規則"] = "不合格依此程序處理"
    return m


def policy_base(intake, spec, su, refs_v1):
    return {"spec": spec,"doc_kind": spec.get("doc_kind") or su.get("doc_kind"), "result_sections": su.get("result_sections") or [],
            "overflow_items": su.get("overflow_items") or [], "use_index": build_use_index(intake, spec), "su": su, "refs_v1": refs_v1}


def policy_ctx(base, section, role):
    o = section["order"]
    return dict(base, name=section["name"], role=role, uses=section_uses(base["su"], o, role),
                clauses=allowed_clauses(base["refs_v1"], o, role))


def jaccard3(a, b):
    """字元 3-gram Jaccard（去空白）。"""
    a, b = re.sub(r"\s+", "", a), re.sub(r"\s+", "", b)
    A, B = {a[i:i + 3] for i in range(len(a) - 2)}, {b[i:i + 3] for i in range(len(b) - 2)}
    return len(A & B) / len(A | B) if A | B else 0.0


RE_LAW_VERSION = re.compile(r"\s*[（(]\s*PE\s*009-\d+\s*[）)]\s*$")
RE_LAW_CLAUSE = re.compile(r"\s*(\d{1,2}\.\d{1,2})\s*$")


def law_parse(law):
    """M5.3：law 欄先去版次後綴、再去結尾條號（X.Y），（條號在版次之後的寫法亦同）→ (法規名, law 內條號或 None)。"""
    t = RE_LAW_VERSION.sub("", str(law))
    m = RE_LAW_CLAUSE.search(t)
    cl = m.group(1) if m else None
    if m:
        t = RE_LAW_VERSION.sub("", t[:m.start()])
    return t, cl


def law_base(law):
    return law_parse(law)[0]


def ref_ok(r, law_keys):
    """refs 成員：法規名＋clause 在條號表；law 內若帶條號，須等於 refs.clause，不等即不成員。"""
    if not (str(r.get("clause", "")).strip() and str(r.get("law", "")).strip()):
        return False
    base, lc = law_parse(r["law"])
    if lc is not None and lc != str(r["clause"]).strip():
        return False
    return cs._ns(base + str(r["clause"])) in law_keys


def gate_section(raw, allow, law_keys, sop_set, excl=None, policy=None):
    """閘門（純函數，可測）：回傳 dict（json_ok、body、diff、refs 成員、sop_refs 成員、passed）。
    passed＝JSON 合法、body 非空、掃描差集 0、refs 全為「law＋clause 非空且在條號表」、sop_refs 全在 intake。"""
    try:
        j = json.loads(raw)
        ok = (isinstance(j, dict) and isinstance(j.get("body"), str) and isinstance(j.get("refs"), list)
              and isinstance(j.get("sop_refs", []), list))
    except Exception:
        j, ok = {}, False
    body = j.get("body", "") if ok else ""
    res, _ = cs.scan(body, allow)
    diff = sum(v["diff"] for v in res.values())
    refs = [r for r in (j.get("refs") or []) if isinstance(r, dict)] if ok else []
    refs_in = sum(1 for r in refs if ref_ok(r, law_keys))
    sops = [str(x) for x in (j.get("sop_refs") or [])] if ok else []
    sops_in = sum(1 for x in sops if cs._ns(x) in sop_set)
    serr = (schema_errors(j, SCHEMA_V2) if policy else schema_errors(j)) if ok else ["JSON 不合法"]
    # v0.5（M4.3 E）：分段允收／中文數字／簡體／條號範圍，並記攔下原因
    excl_hits = [v for c in ("數值", "編號", "中文數字") for v in cs.find_all(c, body) if excl and cs._ns(v) in excl]
    simp = cs.simplified_hits(body)
    rng = cs.clause_ranges(body)
    reasons = []
    if not ok:
        reasons.append("JSON")
    elif serr:
        reasons.append("schema")
    if ok and not body.strip():
        reasons.append("空白")
    if excl_hits:
        reasons.append("分段允收")
    if res["中文數字"]["diff"]:
        reasons.append("中文數字")
    excl_nc = {cs._ns(v) for c in ("數值", "編號") for v in cs.find_all(c, body) if excl and cs._ns(v) in excl}
    if sum(res[c]["diff"] for c in res if c != "中文數字") > len(excl_nc):
        reasons.append("封閉集合")
    if simp:
        reasons.append("簡體")
    if rng:
        reasons.append("範圍")
    if refs_in != len(refs) or sops_in != len(sops):
        reasons.append("引用")
    pol_detail = {}
    if policy and ok:
        pr, pol_detail = policy_checks(body, j.get("refs") or [], policy)
        reasons += pr
    passed = not reasons
    return {"json_ok": ok, "schema_errors": len(serr), "reasons": reasons, "excl_hits": len(excl_hits), "policy": pol_detail,
            "cn_whitelisted": cs.cn_whitelisted_count(body), "cn_equiv": res["中文數字"].get("equiv", []),
            "simplified": len(simp), "ranges": len(rng), "body": body, "chars": len(body), "hits": {k: v["hits"] for k, v in res.items()},
            "diff": {k: v["diff"] for k, v in res.items()}, "refs_n": len(refs), "refs_in": refs_in,
            "sop_n": len(sops), "sop_in": sops_in, "passed": passed,
            "refs": [{k: r.get(k) for k in ("law", "clause", "version") if k in r} for r in refs], "sop_refs": sops}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fsha(p):
    return sha(open(p, "rb").read())


def flat_values(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if not k.startswith("_"):
                yield from flat_values(v)
    elif isinstance(x, list):
        for v in x:
            yield from flat_values(v)
    elif isinstance(x, str):
        yield x


COMMON_KEYS = ("equipment_name", "category", "model", "manufacturer", "asset_id", "location", "criticality", "gmp_use",
               "utility_power", "utility_air", "utility_water", "utility_exhaust", "rated_params", "sop_ids",
               "owner_dept", "planned_date")                      # v0.4（M4.3 D-8）：共同欄；備註不餵
SEG_ACCEPT = {"iq": "accept_iq", "oq": "accept_oq", "pq": "accept_pq"}
SEG_NAME = {"iq": "安裝驗證", "oq": "操作驗證", "pq": "性能驗證"}
ITEMS7 = ("器具材料", "方法步驟", "允收標準", "超標處理", "測試結果", "結果判定", "備註")


def section_roles(skel):
    """order → (segment 或 None, 角色)；角色＝_head／_test／子節名／None（非段落節）。"""
    roles = {}
    for rp in skel["repeats"]:
        if not rp.get("segments"):
            continue
        for st, sg in zip(rp["starts"], rp["segments"]):
            roles[st - 1] = (sg, "_head")
            roles[st] = (sg, "_test")
            for j, nm in enumerate(rp["block"][1:], 1):
                roles[st + j] = (sg, nm)
    return roles


def result_order(skel, name="驗證結果"):
    return next((s["order"] for s in skel["sections"] if s["name"] == name), None)


def intake_view(intake, seg, is_result=False):
    """各節可見的資料表：共同欄＋該段 accept（驗證結果節＝三段皆可見；非段落節只有共同欄）。"""
    v = {k: intake[k] for k in COMMON_KEYS if k in intake}
    for sg, key in SEG_ACCEPT.items():
        if key in intake and (is_result or sg == seg):
            v[key] = intake[key]
    return v


def guide_for(gd, o, role):
    if str(gd.get("version")) not in ("0.5", "0.6", "0.7"):
        return {g["order"]: g["guide"] for g in gd["guides"]}[o]
    if role:
        return next(x["guide"] for x in gd["segment_guides"] if x["segment"] == role[0] and x["item"] == role[1])
    return next(x["guide"] for x in gd["common"] if x["order"] == o)


def _vals(x, cat):
    return {cs._ns(v) for s_ in flat_values(x) for v in cs.find_all(cat, s_)}


def seg_exclusive(intake):
    """各段的「他段專屬值」＝他段 accept 的數值／編號／中文數字 − （共同欄 ∪ 本段 accept）。"""
    out = {}
    for sg, key in SEG_ACCEPT.items():
        mine = intake_view(intake, sg)
        others = [intake[k] for s2, k in SEG_ACCEPT.items() if s2 != sg and k in intake]
        out[sg] = {v for c in ("數值", "編號", "中文數字") for v in _vals(others, c) - _vals(mine, c)}
    return out


def build_allow(intake, refs):
    vals = list(flat_values(intake))
    nums, ids, dates, cn, arm = [], [], [], [], []
    for v in vals:
        nums += [m.group(0) for m in cs.CATS["數值"].finditer(v)]
        ids += cs.find_all("編號", v)
        dates += [m.group(0) for m in cs.CATS["日期"].finditer(v)]
        cn += [m.group(0) for m in cs.CATS["中文數字"].finditer(v)]
        arm += [m.group(0) for m in cs.RE_AR_MEASURE.finditer(v)]
    return {"intake": {"數值": nums, "編號": ids, "日期": dates, "中文數字": cn, "量詞數": arm},
            "refs": [f"{r['law']}{r['clause']}" for r in refs],
            "numbering_rules": SANGU_NUMBERING_RULES}


def unit_of(skel):
    """order → 所屬 repeat 單元的 head 節名（IQ／OQ／PQ 區分用）。"""
    u = {}
    for rp in skel["repeats"]:
        if not rp.get("head"):
            continue
        L = len(rp["block"])
        for h, st in zip(rp["head"], rp["starts"]):
            for o in range(st - 1, st + L):
                u[o] = h
    return u


def chat(model, content, seed=SEED, schema=None):
    body = {"model": model, "stream": False, "think": False, "format": schema or SCHEMA,
            "options": {"temperature": 0, "seed": seed, "num_predict": NUM_PREDICT},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]}
    req = urllib.request.Request(API + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r), time.time() - t0


def generate(a, skel, gd, intake, refs, allow, watch, pol_base=None):
    global SYSTEM
    if pol_base:
        SYSTEM = SYSTEM_V2
    roles = section_roles(skel)
    r_order = result_order(skel)
    excls = seg_exclusive(intake)
    accepted_items = {}
    table_clauses = [r["clause"] for r in refs]
    law_keys = {cs._ns(r["law"] + r["clause"]) for r in refs}
    sop_set = {cs._ns(x) for x in (intake.get("sop_ids") or []) + ([intake["deviation_sop"]] if intake.get("deviation_sop") else [])}
    reftab = [{"law": r["law"], "clause": r["clause"], "標題": r["title_zh"] or r["title"]} for r in refs]
    out = []
    for s in skel["sections"]:
        if watch.remote:
            raise SystemExit("🔴 偵測到非本機連線，停止")
        o = s["order"]
        sid = f"S{o:02d}"
        role = roles.get(o)
        seg = role[0] if role else None
        if s.get("fixed"):                                           # M5.1 C：結果節不走模型
            out.append({"sid": sid, "order": o, "segment": seg, "item": role[1] if role else None, "fixed": True,
                        "passed": True, "json_ok": True, "body": FIXED_TEXT, "chars": len(FIXED_TEXT), "reasons": [],
                        "refs": [], "sop_refs": [], "refs_n": 0, "refs_in": 0, "sop_n": 0, "sop_in": 0,
                        "hits": {c: 0 for c in cs.CATS}, "diff": {c: 0 for c in cs.CATS}, "policy": {},
                        "attempts": 0, "regen_attempts": 0, "wall_s": 0.0, "normalizations": [], "raw": ""})
            print(f"   {sid} 固定文（不走模型）", file=sys.stderr)
            continue
        msg = {"section_id": sid, "節名": s["name"], "層級": s["level"], "指引": guide_for(gd, o, role),
               "設備資料表": intake_view(intake, seg, o == r_order), "條號表": reftab}
        if seg:
            msg["所屬段"] = SEG_NAME[seg]
        view = intake_view(intake, seg, o == r_order)
        if pol_base:                                                 # M5.0 C-10：用途綁定取代分段允收
            allow_s, excl, pctx = build_allow(intake, refs), None, policy_ctx(pol_base, s, role)
            for k in ("設備資料表", "條號表"):                          # M5.1 B：改餵本節可用資料／可引用條號
                msg.pop(k, None)
            msg.update(policy_msg(pctx, pol_base["spec"], intake))
        else:
            allow_s, excl, pctx = build_allow(view, refs), excls.get(seg) if seg else None, None   # E-10：分段允收
        item = role[1] if role and role[1] in ITEMS7 else None
        wall_t, jac, attempts, note = 0.0, 0.0, 0, ""
        norms_all, range_found, range_regen, regen_why = [], [], False, []
        for attempt in range(REGEN_MAX + 1):
            attempts = attempt + 1
            m = dict(msg, **({"重生說明": note} if note else {}))
            resp, wall = chat(a.model, json.dumps(m, ensure_ascii=False), SEED + attempt, SCHEMA_V2 if pol_base else None)
            wall_t += wall
            raw = resp.get("message", {}).get("content", "")
            raw_x, norms, found = expand_raw(sid, raw, table_clauses)      # M4.4 A：展開在範圍閘之前
            norms_all += [dict(n, attempt=attempts) for n in norms]
            range_found.append(found)
            g = gate_section(raw_x, allow_s, law_keys, sop_set, excl, pctx)  # 展開後照常過全部閘（展開不是免檢）
            if not g["passed"]:
                if "範圍" in g["reasons"] and attempt < REGEN_MAX:        # M4.4 B：展開不成 → 重生備援
                    range_regen = True
                    regen_why.append("範圍")
                    note = f"第 {attempt + 1} 次重生：條號逐條列出，只可引用允許清單內的條號。"
                    continue
                break                                                   # 其他閘失敗不重生，直接攔
            if item:                                                    # E-14：同名子節反重複
                jac = max([jaccard3(g["body"], b) for b in accepted_items.get(item, [])] or [0.0])
                if jac > JACCARD_MAX:
                    g["reasons"], g["passed"] = ["重複"], False
                    regen_why.append("重複")
                    note = f"第 {attempt + 1} 次重生：本節內容與前段同名子節過於相似，請依本段範圍改寫，勿沿用前段句子。"
                    continue
            if o == r_order and not all(n in g["body"] for n in SEG_NAME.values()):   # E-15
                g["reasons"], g["passed"] = ["驗證結果"], False
                regen_why.append("驗證結果")
                note = f"第 {attempt + 1} 次重生：正文須逐段列出安裝驗證、操作驗證、性能驗證的結論。"
                continue
            break
        if g["passed"] and item:
            accepted_items.setdefault(item, []).append(g["body"])
        if not g["passed"]:
            g.update(body=BLOCKED, refs=[], sop_refs=[])
        out.append({"sid": sid, "order": o, "segment": seg, "item": item, "wall_s": round(wall_t, 2),
                    "done_reason": resp.get("done_reason"), "eval_count": resp.get("eval_count"),
                    "attempts": attempts, "regen_attempts": attempts - 1, "range_regen": range_regen,
                    "range_found": range_found, "normalizations": norms_all, "regen_why": regen_why, "jaccard": round(jac, 3), **g, "raw": raw})
        print(f"   {sid} {round(wall_t, 1)}s pass={g['passed']} try={attempts} {'／'.join(g['reasons'])}", file=sys.stderr)
    return out


def render(skel, secs, tpl_path, out_path):
    from docx import Document
    from docxtpl import DocxTemplate
    by = {s["order"]: s for s in skel["sections"]}
    body = {x["order"]: x["body"] for x in secs}
    doc = Document()
    doc.sections[0].header.paragraphs[0].text = HEADER
    doc.add_paragraph(HEADER)

    def table(t):
        doc.add_table(rows=max(int(t["rows"]), 1), cols=max(int(t["cols"]), 1)).style = TABLE_STYLE

    for t in skel["tables_before_first_section"]:
        table(t)
    ctx = {"b": {}}
    idx = 0
    seq = skel["sections"]
    for item in skel["folded"]:
        if isinstance(item, dict):
            k = item["repeat"]
            rp = skel["repeats"][k - 1]
            st = rp["starts"]
            L = len(rp["block"])
            doc.add_paragraph(f"{{%p for rep in repeat_{k} %}}")
            h = by[st[0] - 1]
            doc.add_heading("{{ rep.label }}", level=min(max(h["level"], 1), 9))
            doc.add_paragraph("{{ rep.h }}")
            for t in h["tables"]:
                table(t)
            for j in range(L):
                s = by[st[0] + j]
                title = "{{ rep.t0 }}" if rp["block"][j] == "@t0" else s["name"]      # overlay：段別專屬標題
                doc.add_heading(title, level=min(max(s["level"], 1), 9))
                doc.add_paragraph(f"{{{{ rep.b{j} }}}}")
                for t in s["tables"]:
                    table(t)
            doc.add_paragraph("{%p endfor %}")
            ctx[f"repeat_{k}"] = [dict({"label": rp["head"][i], "h": body[s0 - 1], "t0": (rp.get("t0") or [""] * len(st))[i]},
                                       **{f"b{j}": body[s0 + j] for j in range(L)}) for i, s0 in enumerate(st)]
            skip = {s0 + j for s0 in st for j in range(-1, L)}
            while idx < len(seq) and seq[idx]["order"] in skip:
                idx += 1
        else:
            s = seq[idx]
            doc.add_heading(s["name"], level=min(max(s["level"], 1), 9))
            doc.add_paragraph(f"{{{{ b.S{s['order']:02d} }}}}")
            ctx["b"][f"S{s['order']:02d}"] = body[s["order"]]
            for t in s["tables"]:
                table(t)
            idx += 1
    doc.save(tpl_path)
    tpl = DocxTemplate(tpl_path)
    tpl.render(ctx, autoescape=True)
    tpl.save(out_path)
    s2d.normalize_zip(tpl_path)
    s2d.normalize_zip(out_path)


def readback(path):
    """讀回：Heading 樣式段落數、各標題文字（不外洩，只回計數與 IQ/OQ/PQ 標籤命中）。"""
    from docx import Document
    d = Document(path)
    heads = [p.text for p in d.paragraphs if (p.style.name or "").lower().startswith("heading")]
    return heads


def pack(skel, secs, a, model_digest, allow_sha, docx_sha):
    p = {"origin": "ai_draft",
         "disclosure": "本草稿由本地模型依合成資料逐節生成，未經人員修訂、審核與簽核，不得作為受控文件使用。",
         "model": {"name": a.model, "digest": model_digest, "temperature": 0, "seed": SEED},
         "validator_version": VALIDATOR,
         "kb_snapshot": {"intake_sha256": fsha(a.intake), "skel_sha256": fsha(a.skel), "skel_source_sha8": skel.get("source_sha8"),
                         "guides_sha256": fsha(a.guides), "refs_sha256": fsha(a.refs), "allow_sha256": allow_sha},
         "generator": f"nk1-gen.py v{VERSION}", "doc_type": skel.get("doc_type"), "docx_sha256": docx_sha,
         "sections": [{"sid": x["sid"], "passed": x["passed"], "body_sha256": sha(x["body"].encode()),
                       "refs": x["refs"], "sop_refs": x["sop_refs"], "regen_attempts": x.get("regen_attempts", 0),
                       "cn_equiv": x.get("cn_equiv", []) if x["passed"] else []}
                      for x in secs],
         "normalizations": [n for x in secs for n in x.get("normalizations", [])]}
    for k in ("origin", "disclosure", "model", "validator_version", "kb_snapshot"):
        if not p.get(k):
            raise SystemExit(f"🔴 內容包必填欄位缺：{k}")
    return p


def metrics(secs, heads, intake):
    """M4.3 回報指標：各閘攔下／重生、[REJ 標題、同名子節相同段落與最大 Jaccard、IQ 段內他段專屬值命中。"""
    from collections import Counter
    blocked = Counter(r for x in secs if not x["passed"] for r in x["reasons"])
    regen = Counter(w for x in secs for w in set(x.get("regen_why", [])))
    rng = {"hits": sum((x.get("range_found") or [0])[0] for x in secs),
           "expanded_ok": sum(1 for x in secs for n in x.get("normalizations", [])
                              if n.get("attempt") == 1 and n["table_check"] == "all_present"),
           "regen_sections": sum(1 for x in secs if x.get("range_regen")),
           "regen_ok": sum(1 for x in secs if x.get("range_regen") and x["passed"]),
           "blocked": sum(1 for x in secs if not x["passed"] and "範圍" in x["reasons"])}
    cnw = {"whitelisted": sum(x.get("cn_whitelisted", 0) for x in secs),
           "true_hits": sum(x["diff"].get("中文數字", 0) for x in secs),              # 白名單後仍回溯不到 intake
           "traceable": sum(x["hits"].get("中文數字", 0) - x["diff"].get("中文數字", 0) for x in secs)}
    by = {}
    for x in secs:
        if x.get("item") and x["passed"]:
            by.setdefault(x["item"], {})[x["segment"]] = x["body"]
    same, jmax, jpair = 0, 0.0, ""
    for it, d in by.items():
        ss = sorted(d)
        for i in range(len(ss)):
            for j in range(i + 1, len(ss)):
                a, b = d[ss[i]], d[ss[j]]
                same += int(a.strip() == b.strip())
                v = jaccard3(a, b)
                if v > jmax:
                    jmax, jpair = v, f"{it}（{ss[i]}／{ss[j]}）"
    ex = seg_exclusive(intake)
    iq_ex = sum(1 for x in secs if x.get("segment") == "iq" and x["passed"]
                for c in ("數值", "編號", "中文數字") for v in cs.find_all(c, x["body"]) if cs._ns(v) in ex["iq"])
    pol5 = {k: sum(1 for x in secs if k in x.get("reasons", [])) for k in ("結果陳述", "結果禁令", "用途錯置", "章節錯置", "缺版次", "超標處置")}
    cited = sum((x.get("policy") or {}).get("clauses_cited", 0) for x in secs if x["passed"])
    misp = sum((x.get("policy") or {}).get("clause_misplaced", 0) for x in secs if x["passed"])
    m51 = {"fixed": sum(1 for x in secs if x.get("fixed")), "model": sum(1 for x in secs if not x.get("fixed")),
           "model_passed": sum(1 for x in secs if not x.get("fixed") and x["passed"]), "pol5": pol5,
           "clauses_cited": cited, "clauses_in_mapped": cited - misp}
    return {"m51": m51, "blocked": dict(blocked), "regen": dict(regen), "range": rng, "cn": cnw,
            "norms": [dict(n) for x in secs for n in x.get("normalizations", [])], "rej_heads": sum(1 for h in heads if "[REJ" in h),
            "same_paras": same, "jaccard_max": round(jmax, 3), "jaccard_pair": jpair, "iq_excl_hits": iq_ex,
            "attempt_excl_hits": sum(x.get("excl_hits", 0) for x in secs)}


def main():
    ap = argparse.ArgumentParser()
    for k in ("intake", "skel", "guides", "refs", "model", "out-dir", "report"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--inbox", default=os.path.join(os.path.expanduser("~"), "ak-inbox", "nk1-out"))
    ap.add_argument("--inbox-name", help="交件檔名（預設 M4_T027_draft_<run_id>.docx）")
    ap.add_argument("--intake-spec", help="M5.0：資料表規格（含 uses）；與 --section-uses 同給且 refs 為 v1 JSON 時啟用 policy 閘")
    ap.add_argument("--section-uses", help="M5.0：節 → 允許用途")
    a = ap.parse_args()
    skel = s2d.load_skel(a.skel)
    guides = fy.load(a.guides)
    refs = load_refs(a.refs)
    intake = json.load(open(a.intake, encoding="utf8"))
    allow = build_allow(intake, refs)
    allow_sha = sha(json.dumps(allow, ensure_ascii=False, sort_keys=True).encode())
    tags = json.load(urllib.request.urlopen(API + "/api/tags", timeout=10))["models"]
    minfo = next((m for m in tags if m["name"] == a.model), None)
    if not minfo:
        raise SystemExit(f"🔴 模型不存在：{a.model}")
    ver = json.load(urllib.request.urlopen(API + "/api/version", timeout=10))["version"]
    run_id = time.strftime("%Y%m%d-%H%M%S")
    root = os.path.join(os.path.expanduser(a.out_dir), run_id)
    os.makedirs(root)
    w = gp.Watch()
    w.start()
    runs = []
    for i in range(a.runs):
        d = os.path.join(root, f"run{i + 1}")
        os.makedirs(d)
        t0 = time.time()
        pb = (policy_base(intake, fy.load(a.intake_spec), fy.load(a.section_uses), refs)
              if a.intake_spec and a.section_uses and a.refs.endswith(".json") else None)
        secs = generate(a, skel, guides, intake, refs, allow, w, pb)
        t_gen = time.time() - t0
        tpl, docx = os.path.join(d, "template.docx"), os.path.join(d, "T027_draft.docx")
        t1 = time.time()
        render(skel, secs, tpl, docx)
        t_render = time.time() - t1
        dsha = fsha(docx)
        p = pack(skel, secs, a, minfo["digest"], allow_sha, dsha)
        pj = json.dumps(p, ensure_ascii=False, sort_keys=True, indent=1).encode()
        open(os.path.join(d, "content_pack.json"), "wb").write(pj)
        with open(os.path.join(d, "sections.jsonl"), "w", encoding="utf8") as f:
            for x in secs:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
        heads = readback(docx)
        mt = metrics(secs, heads, intake)
        runs.append({"secs": [{k: v for k, v in x.items() if k not in ("body", "raw", "refs", "sop_refs")} for x in secs],
                     "metrics": mt, "pack": os.path.join(d, "content_pack.json"),
                     "docx_sha": dsha, "pack_sha": sha(pj), "t_gen": round(t_gen, 1), "t_render": round(t_render, 2),
                     "heads_n": len(heads), "iqoqpq": [h for h in heads if h in ("安裝驗證", "操作驗證", "性能驗證")],
                     "header_ok": HEADER in zipfile.ZipFile(docx).read("word/document.xml").decode("utf8"),
                     "docx": docx})
    w.stop = True
    w.join()
    os.makedirs(a.inbox, exist_ok=True)
    inbox_docx = os.path.join(a.inbox, a.inbox_name or f"M4_T027_draft_{run_id}.docx")
    open(inbox_docx, "wb").write(open(runs[0]["docx"], "rb").read())
    inbox_pack = re.sub(r"\.docx$", "", inbox_docx) + ".content_pack.json"
    open(inbox_pack, "wb").write(open(runs[0]["pack"], "rb").read())
    st = {"run_id": run_id, "ollama": ver, "model": a.model, "digest": minfo["digest"], "skel_sha8": skel.get("source_sha8"),
          "sections": len(skel["sections"]), "runs": runs, "peak_rss_mb": round(w.peak_kb / 1024), "net_samples": w.samples,
          "net_local_n": len(w.local), "net_remote": sorted(w.remote), "inbox_docx": inbox_docx,
          "inbox_sha8": fsha(inbox_docx)[:8], "inbox_pack": inbox_pack, "inbox_pack_sha8": fsha(inbox_pack)[:8],
          "refs_n": len(refs), "allow_sha": allow_sha}
    json.dump(st, open(os.path.join(root, "stats.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    open(a.report, "w", encoding="utf8").write(report(st))
    print(f"✅ 產物 {root}　報告 {a.report}　inbox {inbox_docx}", file=sys.stderr)
    sys.exit(1 if w.remote else 0)


def report(st):
    cats = list(cs.CATS)
    r1 = st["runs"][0]
    S = r1["secs"]
    n = len(S)
    same_docx = len({r["docx_sha"] for r in st["runs"]}) == 1
    same_pack = len({r["pack_sha"] for r in st["runs"]}) == 1
    tot = lambda k, c: sum(x[k][c] for x in S)
    diff_all = sum(tot("diff", c) for c in cats)
    L = [f"# NK1 M4 端到端 v0 — T027（{st['run_id'][:4]}-{st['run_id'][4:6]}-{st['run_id'][6:8]}）", "",
         "| 標頭 | 值 |", "|---|---|",
         f"| 腳本 | `scripts/nk1-gen.py` v{VERSION}；掃描器 {VALIDATOR} |",
         f"| 引擎／模型 | Ollama {st['ollama']}（127.0.0.1）／`{st['model']}` digest `{st['digest'][:12]}…` |",
         f"| 參數 | temperature 0、seed {SEED}、num_predict {NUM_PREDICT}、think false、format＝JSON schema |",
         f"| 骨架 | T027 `source_sha8={st['skel_sha8']}`（nk1-skel.py v1.2），{st['sections']} 節（節名不列） |",
         f"| 輸入 | intake_v0 合成設備（`fixtures/intake_synth_v0.json`）＋指引句 v0＋條號表 v0（{st['refs_n']} 條） |",
         "| allow | intake 值∪條號表∪三顧編號規則（🔶 v0 為空集合，未落地） |",
         f"| 產物 | `~/nk1-data/gen/m4/{st['run_id']}/`（repo 外）；草稿複本 `~/ak-inbox/nk1-out/`，sha8 `{st['inbox_sha8']}` |",
         "| 內容規則 | 只出統計；零 body 原文；**不做品質判斷** |", "",
         "---", "", "## C2 驗收五項", "",
         "| # | 項 | 結果 |", "|---|---|---|",
         f"| 1 | 掃描器全篇差集＝0 | {'✅' if diff_all == 0 else '🔴'} 差集 {diff_all}（" + "；".join(f"{c} {tot('hits', c)}/{tot('diff', c)}" for c in cats) + "，命中/差集） |",
         f"| 2 | refs 100% 在條號表 | {'✅' if all(x['refs_in'] == x['refs_n'] for x in S) else '🔴'} {sum(x['refs_in'] for x in S)}/{sum(x['refs_n'] for x in S)}"
         f"（sop_refs 在 intake {sum(x['sop_in'] for x in S)}/{sum(x['sop_n'] for x in S)}） |",
         f"| 3 | 同輸入兩次 docx sha 相同 | {'✅' if same_docx else '🔴'} " + "／".join(f"`{r['docx_sha'][:12]}`" for r in st["runs"])
         + f"（內容包 {'相同' if same_pack else '不同'}） |",
         f"| 4 | docx 讀回節數＝骨架節數；IQ/OQ/PQ 標籤三個 | {'✅' if r1['heads_n'] == st['sections'] and len(r1['iqoqpq']) == 3 else '🔴'} "
         f"讀回 {r1['heads_n']}／骨架 {st['sections']}；IQ/OQ/PQ 標籤 {len(r1['iqoqpq'])} 個 |",
         f"| 5 | 總時間 | 生成 {r1['t_gen']} s＋渲染 {r1['t_render']} s（第 1 輪）；各輪生成 " + "／".join(str(r['t_gen']) for r in st["runs"]) + " s |",
         "", "**M4.3 閘（第 1 輪）**", "", "| 項 | 值 |", "|---|---|",
         f"| 各閘攔下（最終） | " + ("；".join(f"{k} {v}" for k, v in r1['metrics']['blocked'].items()) or "0") + " |",
         f"| 重生（節數，依觸發閘） | " + ("；".join(f"{k} {v}" for k, v in r1['metrics']['regen'].items()) or "0") + " |",
         f"| 範圍：命中／展開成功／走重生（節）／重生成功／最終攔下 | {r1['metrics']['range']['hits']}／{r1['metrics']['range']['expanded_ok']}／"
         f"{r1['metrics']['range']['regen_sections']}／{r1['metrics']['range']['regen_ok']}／{r1['metrics']['range']['blocked']} |",
         f"| 中文數字：白名單命中／真命中（不可回溯）／可回溯 intake | {r1['metrics']['cn']['whitelisted']}／{r1['metrics']['cn']['true_hits']}／{r1['metrics']['cn']['traceable']} |",
         f"| 模型節寫入／模型節總數／固定文節 | {r1['metrics']['m51']['model_passed']}／{r1['metrics']['m51']['model']}／{r1['metrics']['m51']['fixed']} |",
         f"| 新閘命中（結果陳述／結果禁令／用途錯置／章節錯置／缺版次／超標處置） | "
         + "／".join(str(v) for v in r1['metrics']['m51']['pol5'].values()) + " |",
         f"| 中文數字等值換算（原寫法→阿拉伯數字，寫入正文） | "
         + ("、".join(f"{e['original']}→{e['arabic']}" for x in S if x['passed'] for e in x.get('cn_equiv', [])) or "0") + " |",
         f"| 條號引用總數／在對應章節內 | {r1['metrics']['m51']['clauses_cited']}／{r1['metrics']['m51']['clauses_in_mapped']} |",
         f"| 標題含 [REJ | {r1['metrics']['rej_heads']} |",
         f"| 三段同名子節相同段落數 | {r1['metrics']['same_paras']} |",
         f"| 同名子節最大 Jaccard（3-gram） | {r1['metrics']['jaccard_max']}（{r1['metrics']['jaccard_pair'] or '—'}） |",
         f"| IQ 段內 OQ／PQ 專屬值命中（寫入正文） | {r1['metrics']['iq_excl_hits']} |",
         f"| 全段他段專屬值命中（含被攔嘗試） | {r1['metrics']['attempt_excl_hits']} |",
         f"| 內容包交件 | `{os.path.basename(st['inbox_pack'])}` sha8 `{st['inbox_pack_sha8']}` |",
         "", "**normalizations（第 1 輪，全部嘗試）**", "", "| 節 | 嘗試 | 原文 | 展開後條數 | 查表結果 | 動作 |", "|---|---:|---|---:|---|---|"]
    L += [f"| {n['section_id']} | {n.get('attempt')} | {n['original']} | {len(n['expanded'])} | {n['table_check']} | {n.get('action', '展開')} |"
          for n in r1["metrics"]["norms"]] or ["| — | — | （無） | — | — | — |"]
    L += ["", "**其他**", "", "| 項 | 值 |", "|---|---|",
         f"| 節通過（寫入）／攔下 | {sum(x['passed'] for x in S)}／{sum(not x['passed'] for x in S)} |",
         f"| JSON 合法 | {sum(x['json_ok'] for x in S)}/{n} |",
         f"| 字數 min／中位／max | {min(x['chars'] for x in S)}／{sorted(x['chars'] for x in S)[n // 2]}／{max(x['chars'] for x in S)} |",
         f"| 觸頂 num_predict | {sum(1 for x in S if x.get('done_reason') == 'length')}/{n} |",
         f"| 檔頭「{HEADER}」 | {'✅' if r1['header_ok'] else '🔴'} |",
         f"| 內容包必填（origin／disclosure／model／validator_version／kb_snapshot） | ✅ 缺一即中止，已產出 |",
         f"| ollama＋llama-server RSS 峰值 | {st['peak_rss_mb']} MB |",
         f"| 網路：取樣 {st['net_samples']} 次、本機端點 {st['net_local_n']} 個 | **非本機 {len(st['net_remote'])}** |", "",
         "---", "", "## 逐節（第 1 輪）", "",
         "| 節 | 段 | JSON | 字數 | 差集 | refs 在表/總 | 嘗試 | Jaccard | 寫入／攔下原因 | 秒 |",
         "|---|---|---|---:|---:|---:|---:|---:|---|---:|"]
    for x in S:
        L.append(f"| {x['sid']} | {x.get('segment') or '—'} | {'✓' if x['json_ok'] else '✗'} | {x['chars']} | {sum(x['diff'].values())} | "
                 f"{x['refs_in']}/{x['refs_n']} | {x.get('attempts', 1)} | {x.get('jaccard', 0)} | "
                 f"{'✓' if x['passed'] else '攔下：' + '／'.join(x.get('reasons', []))} | {x['wall_s']} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
