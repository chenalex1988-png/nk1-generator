#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 骨架抽取器 — docx → 骨架 YAML（節名／層級／順序／表格形／repeat 摺疊）。

規則 v1.1（工單【NK1・M1】B 段；v1.0＝夜跑二 B 段）：
  節＝Heading 樣式段落（Heading N／標題 N）或 w:outlineLvl ≤2（段落直設或樣式鏈繼承）→ 層級＝outlineLvl＋1。
    純文字編號段落（1. ／一、）**只在零 Heading／outlineLvl 文件當後備，且限第一層**；
    Word 自動編號 numPr 本身不再算節（v1.0 算）。
  **表格內儲存格一律不算節**（規則 1）——只走 body 層段落（含 body 層 sdt 內容控制項）。
  規則 4（v1.2，M1.1 A3）：Word 自動編號段落（numPr，任何 ilvl）若文字正規化後在詞彙表內 → 視為節，層級＝ilvl＋1。
  規則 3：表格首列為**跨欄合併**的單一儲存格（gridSpan＝全欄、欄數 ≥2），文字 ≤20 字且過句子閘（含詞彙表）
    → 視為節標記（第一層節，該表歸此節）。
  表：rows×cols、所在節、首列是否表頭（tblHeader 或首列非空格全粗體）。
  repeat（規則 2）：
    無 head：連續 ≥3 個節名的子序列在同文件出現 ≥2 次（不重疊）。
    有 head：`{head:[…], block:[…], count:N}`——每次出現＝1 個 head 節＋相同 block，單元首尾相接、
      head 同層且層級淺於 block 首節；**判準 block 相同即可**（head 可變）。block 長度 ≥1（🔶 阿K 口徑）。
    → repeats[]，並在 folded[] 摺疊。
  v1.3（M4.3 B）：**節標題一律不過詞彙表閘**（標題是結構層），只過啟發式；
    規則 3／4 仍以詞彙表**判定「是否成節」**（偵測，不是閘）。
    CLI：任一節名產生 `[REJ-n]` → **失敗停止、不出檔**（exit 3）。
  --overlay：repeat head → segment（iq／oq／pq），block 首節改為該段專屬標題（repeats[].segments／t0；sections[].segment）。

用法：nk1-skel.py DOCX [--doc-type X] [--out FILE.yaml]
🔴 真文件的骨架只准輸出到 ~/nk1-data/ 下，**不進 repo**。
零依賴、確定性：同輸入同輸出（無時間戳）。
"""
import argparse, hashlib, importlib.util, os, re, sys, zipfile
from xml.etree import ElementTree as ET

VERSION = "1.4.0"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sentence_gate", os.path.join(HERE, "sentence-gate.py"))
_sg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sg)

RE_HEADSTYLE = re.compile(r"^(?:heading|標題)\s*([1-9])$", re.I)
RE_NUM_TOP = re.compile(r"^\s*\d{1,2}(?:[\.、．]\s*|\s+)(?=[^\d\s.])(.*)$")      # 後備：只收第一層「1. 」
RE_NUM_CN = re.compile(r"^\s*[一二三四五六七八九十]+[、．.]\s*(.*)$")
MAX_OUTLINE = 2
LABEL_MAX = 20


def _text(el):
    return "".join(t.text or "" for t in el.iter(W + "t"))


def _body_items(body):
    """body 層的段落與表格（展開 body 層 sdt），依文件順序。"""
    for el in list(body):
        if el.tag == W + "sdt":
            c = el.find(W + "sdtContent")
            if c is not None:
                yield from _body_items(c)
        elif el.tag in (W + "p", W + "tbl"):
            yield el


def _styles(z):
    """styleId → (名稱, outlineLvl 或 None)；outlineLvl 沿 basedOn 鏈繼承。"""
    raw = {}
    if "word/styles.xml" in z.namelist():
        for s in ET.fromstring(z.read("word/styles.xml")).iter(W + "style"):
            n, o, b = s.find(W + "name"), s.find(f"{W}pPr/{W}outlineLvl"), s.find(W + "basedOn")
            raw[s.get(W + "styleId")] = ((n.get(W + "val") if n is not None else "") or "",
                                        int(o.get(W + "val")) if o is not None else None,
                                        b.get(W + "val") if b is not None else None)
    out = {}
    for sid, (name, ol, base) in raw.items():
        seen = {sid}
        while ol is None and base and base in raw and base not in seen:
            seen.add(base)
            ol, base = raw[base][1], raw[base][2]
        out[sid] = (name, ol)
    return out


def classify_para(p, styles):
    """結構層判定：回傳 (level, 節名) 或 None（Heading 樣式或 outlineLvl ≤2）。"""
    t = re.sub(r"\s+", " ", _text(p)).strip()
    if not t:
        return None
    ps = p.find(f"{W}pPr/{W}pStyle")
    sid = ps.get(W + "val") if ps is not None else ""
    name, sol = styles.get(sid, (sid, None))
    m = RE_HEADSTYLE.match(name or "") or RE_HEADSTYLE.match(sid or "")
    if m:
        return int(m.group(1)), t
    ol = p.find(f"{W}pPr/{W}outlineLvl")
    lvl = int(ol.get(W + "val")) if ol is not None else sol
    if lvl is not None and lvl <= MAX_OUTLINE:
        return lvl + 1, t
    return None


def classify_plain(p):
    """後備（零 Heading 文件）：純文字編號段落，限第一層。"""
    t = re.sub(r"\s+", " ", _text(p)).strip()
    for rx in (RE_NUM_TOP, RE_NUM_CN):
        m = rx.match(t)
        if m and m.group(1).strip():
            return 1, m.group(1).strip()
    return None


def classify_numbered(p, gate):
    """規則 4：自動編號段落（任何 ilvl），文字正規化後在詞彙表內 → (level, 節名)。"""
    num = p.find(f"{W}pPr/{W}numPr")
    if num is None or gate.lex is None:
        return None
    t = re.sub(r"\s+", " ", _text(p)).strip()
    if not t or _sg.lex_key(t) not in gate.lex:
        return None
    il = num.find(W + "ilvl")
    return (int(il.get(W + "val")) + 1 if il is not None else 1), t


def merged_label(tbl):
    """規則 3：首列為跨欄合併單一儲存格（欄數 ≥2）→ 回傳其文字，否則 None。"""
    rows = tbl.findall(W + "tr")
    cols = len(tbl.findall(f"{W}tblGrid/{W}gridCol"))
    if not rows or cols < 2:
        return None
    tcs = rows[0].findall(W + "tc")
    if len(tcs) != 1:
        return None
    gs = tcs[0].find(f"{W}tcPr/{W}gridSpan")
    if gs is None or int(gs.get(W + "val")) != cols:
        return None
    t = re.sub(r"\s+", " ", _text(tcs[0])).strip()
    return t if t and len(t) <= LABEL_MAX else None


def table_shape(tbl):
    rows = tbl.findall(W + "tr")
    grid = tbl.findall(f"{W}tblGrid/{W}gridCol")
    cols = len(grid) or max((len(r.findall(W + "tc")) for r in rows), default=0)
    header = False
    if rows:
        if rows[0].find(f"{W}trPr/{W}tblHeader") is not None:
            header = True
        else:
            runs = [r for r in rows[0].iter(W + "r") if _text(r).strip()]
            header = bool(runs) and all(r.find(f"{W}rPr/{W}b") is not None for r in runs)
    return {"rows": len(rows), "cols": cols, "header": header}


def find_repeats(seq, min_len=3, levels=None):
    """回傳 [(block, starts, has_head)]，starts 為 block 起點（0 起）；有 head 時 head 在 start-1。
    ① 無 head：最長優先、左起優先；非重疊出現 ≥2 次、長度 ≥min_len 的連續子序列。
    ② ① 的結果若各次出現恰以 1 節相隔且該節可當 head → 升為有 head。
    ③ 其餘位置再找有 head 的短 block（長度 1..min_len-1）。"""
    plain = _find_plain(seq, min_len)
    if levels is None:
        return [(b, st, False) for b, st in plain]
    used = [False] * len(seq)
    for b, st in plain:
        for s in st:
            for k in range(s, s + len(b)):
                used[k] = True
    out = []
    for b, st in plain:
        ok = _head_ok(st, len(b), levels, used)
        if ok:
            for s in st:
                used[s - 1] = True
        out.append((b, st, ok))
    for L in range(min_len - 1, 0, -1):
        i = 1
        while i + L <= len(seq):
            st = [i]
            while st[-1] + L + 1 + L <= len(seq) and seq[st[-1] + L + 1:st[-1] + 2 * L + 1] == seq[i:i + L]:
                st.append(st[-1] + L + 1)
            span = range(st[0] - 1, st[-1] + L)
            if len(st) >= 2 and not any(used[k] for k in span) and _head_ok(st, L, levels, used):
                for k in span:
                    used[k] = True
                out.append((seq[i:i + L], st, True))
                i = st[-1] + L + 1
            else:
                i += 1
    return sorted(out, key=lambda x: x[1][0])


def _head_ok(starts, L, levels, used):
    """各次出現首尾相接（間隔 L+1）、head 未被占用、head 同層且淺於 block 首節。"""
    if starts[0] < 1 or any(b - a != L + 1 for a, b in zip(starts, starts[1:])):
        return False
    heads = [s - 1 for s in starts]
    if any(used[h] for h in heads):
        return False
    hl = {levels[h] for h in heads}
    return len(hl) == 1 and hl.pop() < levels[starts[0]]


def _find_plain(seq, min_len):
    used = [False] * len(seq)
    found = []
    for L in range(len(seq) // 2, min_len - 1, -1):
        i = 0
        while i + L <= len(seq):
            if any(used[i:i + L]):
                i += 1
                continue
            blk = seq[i:i + L]
            starts, j = [], i
            while j + L <= len(seq):
                if not any(used[j:j + L]) and seq[j:j + L] == blk:
                    starts.append(j)
                    j += L
                else:
                    j += 1
            if len(starts) >= 2:
                for s in starts:
                    for k in range(s, s + L):
                        used[k] = True
                found.append((blk, starts))
                i += L
            else:
                i += 1
    return sorted(found, key=lambda x: x[1][0])


def default_gate():
    return _sg.Gate(_sg.load_rules(_sg.DEFAULT_RULES), _sg.load_lexicon(_sg.DEFAULT_LEXICON))


def extract(path, doc_type, gate=None):
    gate = gate or default_gate()
    z = zipfile.ZipFile(path)
    styles = _styles(z)
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    items = list(_body_items(body))
    fallback = not any(classify_para(el, styles) for el in items if el.tag == W + "p")
    sections, pre_tables, rej = [], [], 0

    def add(lvl, raw):
        nonlocal rej
        shown = raw
        if gate.check(raw, use_lex=False):
            rej += 1
            shown = f"[REJ-{rej}]"
        sections.append({"order": len(sections) + 1, "level": lvl, "raw": raw, "name": shown, "tables": []})

    for el in items:
        if el.tag == W + "p":
            c = (classify_plain(el) if fallback else classify_para(el, styles)) or classify_numbered(el, gate)
            if c:
                add(*c)
        else:
            lab = merged_label(el)
            if lab is not None and not gate.check(lab):
                add(1, lab)
            (sections[-1]["tables"] if sections else pre_tables).append(table_shape(el))
    reps = find_repeats([s["raw"] for s in sections], levels=[s["level"] for s in sections])
    repeats, folded, i = [], [], 0
    rep_at = {}
    for k, (blk, starts, has_head) in enumerate(reps, 1):
        r = {"block": [sections[starts[0] + j]["name"] for j in range(len(blk))],
             "count": len(starts), "starts": [s + 1 for s in starts]}
        if has_head:
            r = {"head": [sections[s - 1]["name"] for s in starts], **r}
        repeats.append(r)
        off = 1 if has_head else 0
        for s in starts:
            rep_at[s - off] = (k, len(blk) + off, s == starts[0])
    while i < len(sections):
        if i in rep_at:
            k, L, first = rep_at[i]
            if first:
                folded.append({"repeat": k, "count": repeats[k - 1]["count"]})
            i += L
        else:
            folded.append(sections[i]["name"])
            i += 1
    ntab = len(pre_tables) + sum(len(s["tables"]) for s in sections)
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()[:8]
    return {"doc_type": doc_type, "source_sha8": sha, "extractor": f"nk1-skel.py {VERSION}",
            "stats": {"sections": len(sections), "tables": ntab, "repeats": len(repeats), "rejected": rej},
            "tables_before_first_section": pre_tables, "sections": sections, "repeats": repeats, "folded": folded}


def apply_overlay(d, ov):
    """overlay：依 head 名對應 segment 與 block 首節專屬標題；對不上即失敗（不猜）。"""
    m = {x["head"]: x for x in ov["segments"]}
    by = {s["order"]: s for s in d["sections"]}
    hit = 0
    for r in d["repeats"]:
        if not r.get("head"):
            continue
        if not all(h in m for h in r["head"]):
            raise ValueError("overlay：repeat head 對不上")
        r["segments"] = [m[h]["segment"] for h in r["head"]]
        r["t0"] = [m[h]["block0_title"] for h in r["head"]]
        r["block"] = ["@t0"] + r["block"][1:]
        L = len(r["block"])
        for st, h in zip(r["starts"], r["head"]):
            for o in range(st - 1, st + L):
                by[o]["segment"] = m[h]["segment"]
            by[st]["name"] = by[st]["raw"] = m[h]["block0_title"]
        hit += 1
    if hit == 0:
        raise ValueError("overlay：無可套用的 repeat")
    fi, fs = set(ov.get("fixed_items") or []), set(ov.get("fixed_sections") or [])     # v1.4（M5.1 C）：結果節 fixed
    for sct in d["sections"]:
        if (sct.get("segment") and sct["name"] in fi) or (not sct.get("segment") and sct["name"] in fs):
            sct["fixed"] = True
    d["overlay"] = f"{ov.get('doc_type')} v{ov.get('version')}"
    return d


def _q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _tbls(ts):
    return "[" + ", ".join(f"{{rows: {t['rows']}, cols: {t['cols']}, header: {'true' if t['header'] else 'false'}}}" for t in ts) + "]"


def to_yaml(d):
    L = [f"doc_type: {_q(d['doc_type'])}", f"source_sha8: {_q(d['source_sha8'])}", f"extractor: {_q(d['extractor'])}",
         "stats: {" + ", ".join(f"{k}: {v}" for k, v in d["stats"].items()) + "}",
         f"tables_before_first_section: {_tbls(d['tables_before_first_section'])}", "sections:"]
    if d.get("overlay"):
        L.insert(3, f"overlay: {_q(d['overlay'])}")
    for s in d["sections"]:
        seg = f"segment: {_q(s['segment'])}, " if s.get("segment") else ""
        seg += "fixed: true, " if s.get("fixed") else ""
        L.append(f"  - {{order: {s['order']}, level: {s['level']}, name: {_q(s['name'])}, {seg}tables: {_tbls(s['tables'])}}}")
    L.append("repeats:" + ("" if d["repeats"] else " []"))
    for r in d["repeats"]:
        head = f"head: [{', '.join(_q(x) for x in r['head'])}], " if "head" in r else ""
        if r.get("segments"):
            head += f"segments: [{', '.join(_q(x) for x in r['segments'])}], t0: [{', '.join(_q(x) for x in r['t0'])}], "
        L.append(f"  - {{{head}block: [{', '.join(_q(x) for x in r['block'])}], count: {r['count']}, starts: {r['starts']}}}")
    L.append("folded:")
    for f in d["folded"]:
        L.append(f"  - {{repeat: {f['repeat']}, count: {f['count']}}}" if isinstance(f, dict) else f"  - {_q(f)}")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--doc-type")
    ap.add_argument("--out")
    ap.add_argument("--lexicon", default=_sg.DEFAULT_LEXICON)
    ap.add_argument("--overlay", help="段別 overlay YAML（specs/overlays/）")
    a = ap.parse_args()
    dt = a.doc_type
    if not dt:
        m = re.match(r"^([A-Z]+(?:[-+][A-Z]+)*-?\d*|[A-Z]\+)", os.path.basename(os.path.dirname(os.path.abspath(a.docx))))
        dt = m.group(1) if m else "unknown"
    try:
        gate = _sg.Gate(_sg.load_rules(_sg.DEFAULT_RULES), _sg.load_lexicon(a.lexicon))
        d = extract(a.docx, dt, gate)
        if d["stats"]["rejected"]:
            print(f"🔴 節名產生 [REJ-n] 佔位 {d['stats']['rejected']} 個 → 失敗停止、不出檔", file=sys.stderr)
            sys.exit(3)
        if a.overlay:
            sys.path.insert(0, HERE)
            import nk1_flowyaml as fy
            d = apply_overlay(d, fy.load(a.overlay))
        y = to_yaml(d)
    except Exception as e:
        print(f"🔴 骨架抽取失敗：{type(e).__name__}: {str(e)[:80]}", file=sys.stderr)
        sys.exit(2)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, "w", encoding="utf8").write(y)
    else:
        sys.stdout.write(y)


if __name__ == "__main__":
    main()
