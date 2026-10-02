#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 封閉集合掃描器 — 文件裡的數值／編號／日期／法規／條號，必須 ⊆ allow.json。

用法：nk1-closedset.py INPUT(.docx|.txt|.md) --allow allow.json [--keep-placeholders]
  allow.json：{"intake": {"數值": [...], "日期": [...], "編號": [...]},
               "refs": ["法規名＋條號", ...], "numbering_rules": ["regex", ...]}
  缺鍵視為空集合；allow 檔可為 {}（＝全部進差集，當基準線用）。

五類（工單【NK1・夜跑二】C 段；逐字照列，下列口徑為阿K 補）：
  ① 數值＋單位　② 文件編號樣式　③ 日期　④ 法規名　⑤ 條號
  口徑：單位依長度降冪比對（避免 min 被 m 先吃）、英文單位後不得緊接**小寫**英文字母
        （v1.1：緊接大寫不排除；單位表加「秒／s」）；
        ② 三式（MB 式／SOP 式／通用式）各自比對後**以 span 去重**（重疊取最長、同長取左），前面不得緊接英數；
           v1.1：通用式首段接受 [A-Z]+\d+（如 AB1-…）；
        ⑤ v1.1：裸 X.Y 只在**同句**含法規名或「第／§／Clause」時才算（句界＝。！？；與換行）；
           v1.2（M1.1 A4）：裸 X.Y **後接單位／±／%** 或**位於表格儲存格內**者不算；
           第N條／§／Clause 式照舊一律算；
        v1.7（M5.4 B）：result_statement_hits——計畫類文件全文逐句判結果陳述（規範式句白名單）＋核准日不得進敘述句
        v1.6（M5.2 b）：中文數字不在 intake 原文時，一～十換算為阿拉伯數字＋同量詞，與 intake 值相等即視為可回溯；
          原寫法與換算值記於結果 cn_equiv（正文不改）。
        v1.5（M5.0 C）：另加 result_term_hits／version_missing／overflow_disposition_hits（閘門呼叫，不入五類計數）
        ⑥ v1.4（M4.4 C）：先遮 specs/guards/cn_numeral_whitelist.yaml 固定語（任一、一致…），命中白名單者不計。
        ⑥ v1.3（M4.3 E-11）中文數字：[一二…萬零兩]＋量詞（點區個項次批組段層道）；比 intake.中文數字（須可回溯 intake 原文）。
  另兩個檢查函數（不入五類計數，由閘門呼叫）：
        simplified_hits(text)：命中 specs/guards/simplified_chars.yaml 任一字（E-12）
        clause_ranges(text)：條號範圍「X.Y 至 X.Y」「X.Y–X.Y」「第 N 至 M 條」（E-13）
        判斷允許：①③ 比 intake 同類；② 比 intake.編號 或 numbering_rules 任一 fullmatch；
        ④⑤ 為 refs 任一條的子字串（兩邊去空白後比）。
  預設先剔除佔位符（YYYY、XX…、OO…、${…}、底線串），剔除數另計；--keep-placeholders 關閉。

輸出：每類 命中（相異值）／允許／差集；差集只列「類型＋遮蔽後樣式」，**不列原值**。
exit：0＝差集 0　1＝差集 >0　2＝輸入或 allow 讀不到
"""
import argparse, json, os, re, sys, zipfile
from collections import Counter, OrderedDict
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_UNITS = ["°C", "℃", "%", "μS/cm", "mm", "cm", "m", "kg", "g", "mg", "mL", "L", "min", "h", "hr", "rpm",
          "Pa", "kPa", "bar", "psi", "ppm", "CFU", "lux", "Hz", "V", "A", "W", "次", "天", "年", "秒", "s"]
_U = "|".join(re.escape(u) + (r"(?![a-z])" if re.match(r"[A-Za-z]", u[-1]) else "")
              for u in sorted(_UNITS, key=len, reverse=True))
_MON = "JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC"
CATS = OrderedDict([
    ("數值", re.compile(r"\d+(?:\.\d+)?\s*(?:" + _U + ")")),
    ("編號", [re.compile(r"(?<![A-Za-z0-9])" + x) for x in (
        r"MB[A-Z]+-[A-Z]-[A-Z]+\d+", r"SOP-?[A-Z]*-?\d+", r"[A-Z]{1,6}\d{0,4}-[A-Z0-9]{1,6}(?:-\d{2,4})?")]),
    ("日期", re.compile(r"\d{4}/\d{1,2}/\d{1,2}|\d{4}-\d{1,2}-\d{1,2}|\d{1,2}(?:" + _MON + r")\d{4}|民國\d+年", re.I)),
    ("法規", re.compile(r"PIC/S(?:\s*GMP)?|Annex\s*\d+|ICH\s*Q\d+(?:\(R\d\))?|21\s*CFR\s*Part\s*\d+|ISO\s*\d+|GAMP\s?5|藥品優良製造規範|衛授食字第\d+號")),
    ("條號", re.compile(r"第\d+條|§\s?\d+(?:\.\d+)*|Clause\s*\d+(?:\.\d+)*")),
    ("中文數字", re.compile(r"[一二三四五六七八九十百千萬零兩]+[點區個項次批組段層道]")),
])
CN_DIGIT = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
RE_CN_SINGLE = re.compile(r"^([一二三四五六七八九十])([點區個項次批組段層道])$")
RE_AR_MEASURE = re.compile(r"\d+\s*[點區個項次批組段層道]")


def cn_to_arabic(v):
    """M5.2 b：「一～十」單字＋量詞 → 「N量詞」；其他形式回 None（不換算）。"""
    m = RE_CN_SINGLE.match(v)
    return f"{CN_DIGIT[m.group(1)]}{m.group(2)}" if m else None


RE_CLAUSE_RANGE = re.compile(r"\d+(?:\.\d+)+\s*(?:至|到|~|～|–|—|－|-)\s*\d+(?:\.\d+)+"
                             r"|第\s*\d+\s*(?:條)?\s*(?:至|到|~|～|–|—|－|-)\s*(?:第\s*)?\d+\s*條")
WHITELIST_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "specs", "guards", "cn_numeral_whitelist.yaml")
_WHITELIST = None


def cn_whitelist(path=WHITELIST_PATH):
    global _WHITELIST
    if _WHITELIST is None:
        ph = re.findall(r'^\s+-\s+"([^"]+)"', open(path, encoding="utf8").read(), re.M)
        if not ph:
            raise ValueError("中文數字白名單讀不到或為空")
        _WHITELIST = sorted(ph, key=len, reverse=True)
    return _WHITELIST


def mask_whitelist(text):
    for p in cn_whitelist():
        text = text.replace(p, "□" * len(p))
    return text


def cn_whitelisted_count(text):
    """白名單遮掉的中文數字命中數＝遮前命中 − 遮後命中。"""
    rx = CATS["中文數字"]
    return len(rx.findall(text)) - len(rx.findall(mask_whitelist(text)))


SIMPLIFIED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "specs", "guards", "simplified_chars.yaml")
_SIMPLIFIED = None


def simplified_hits(text, path=SIMPLIFIED_PATH):
    """回傳命中的簡體字（相異、依出現序）；對照表讀不到＝故障（fail-closed，拋例外）。"""
    global _SIMPLIFIED
    if _SIMPLIFIED is None:
        chars = re.findall(r'\{s: "(.)"', open(path, encoding="utf8").read())
        if len(chars) < 100:
            raise ValueError("簡體對照表過短或讀不到")
        _SIMPLIFIED = set(chars)
    seen = []
    for c in text:
        if c in _SIMPLIFIED and c not in seen:
            seen.append(c)
    return seen


RESULT_TERMS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "specs", "guards", "result_terms.yaml")
RE_VERSION_MISSING = re.compile(r"Annex\s*15(?!\s*[（(]\s*PE\s*009-18\s*[）)])")
OVERFLOW_FORBIDDEN = ("變更管制", "再驗證")
_RESULT = None


def result_term_hits(text, path=RESULT_TERMS_PATH):
    """M5.0 C-9：結果禁令判定語（字面＋句型）命中清單；表讀不到＝故障（拋例外）。"""
    global _RESULT
    if _RESULT is None:
        raw = open(path, encoding="utf8").read()
        terms = re.findall(r'^\s+-\s+"([^"]+)"', raw.split("patterns:")[0], re.M)
        pats = [re.compile(p.replace("\\\\", "\\")) for p in re.findall(r'^\s+-\s+"([^"]+)"', raw.split("patterns:")[1], re.M)]
        if not terms:
            raise ValueError("結果禁令語表讀不到或為空")
        _RESULT = (terms, pats)
    terms, pats = _RESULT
    return [t for t in terms if t in text] + [m.group(0) for p in pats for m in p.finditer(text)]


RESULT_STMT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "specs", "guards", "result_statement_lexicon.yaml")
_RSTMT = None


def _load_rstmt(path=RESULT_STMT_PATH):
    global _RSTMT
    if _RSTMT is None:
        raw = open(path, encoding="utf8").read()

        def block(name):
            m = re.search(r"^" + name + r":\n((?:\s+-\s+.*\n)+)", raw, re.M)
            return [x.replace("\\\\", "\\") for x in re.findall(r'^\s+-\s+"([^"]+)"', m.group(1), re.M)] if m else []
        da = re.search(r'^date_approval:\s*"(.+)"\s*$', raw, re.M)
        terms, pats, norm = block("terms"), [re.compile(x) for x in block("patterns")], [re.compile(x) for x in block("normative")]
        if not terms or not pats or not norm or not da:
            raise ValueError("結果陳述詞表讀不到或不完整")
        _RSTMT = (terms, pats, norm, re.compile(da.group(1).replace("\\\\", "\\")))
    return _RSTMT


def result_statement_hits(text):
    """M5.4 B：逐句判結果陳述（全文內容判，不依節名）。回傳 [(句首 12 字, 命中詞, 類型)]。
    類型：結果陳述（詞表／句型命中且非規範式句）／核准日（同句日期＋核准）。"""
    terms, pats, norm, da = _load_rstmt()
    out = []
    for sent in re.findall(r"[^。；！？\n]+[。；！？]?", text):
        s = sent.strip()
        if not s:
            continue
        if da.search(s):
            out.append((s[:12], "日期＋核准", "核准日"))
            continue
        hit = next((t for t in terms if t in s), None) or next((m.group(0) for p in pats for m in [p.search(s)] if m), None)
        if hit and not any(n.search(s) for n in norm):
            out.append((s[:12], hit, "結果陳述"))
    return out


def version_missing(text):
    """M5.0 C-12：正文引用 Annex 15 須帶版次「（PE 009-18）」；回傳缺版次的次數。"""
    return len(RE_VERSION_MISSING.findall(text))


def overflow_disposition_hits(text):
    """M5.0 C-13：超標處理節以「變更管制」「再驗證」作為不合格處置（🔶 口徑：出現即算）。"""
    return [w for w in OVERFLOW_FORBIDDEN if w in text]


def clause_ranges(text):
    return [m.group(0) for m in RE_CLAUSE_RANGE.finditer(text)]
RE_BARE_XY = re.compile(r"第\d+條|§\s?\d+(?:\.\d+)*|Clause\s*\d+(?:\.\d+)*|(?<![\d.])\d+\.\d+(?:\.\d+)*(?![\d.])(?!\s*(?:[±%]|" + _U + "))")
RE_SENT = re.compile(r"[^。！？；\n]+")
RE_CLAUSE_CUE = re.compile(r"第|§|Clause")


def find_all(cat, text):
    """回傳該類命中字串清單。編號＝多式 span 去重；條號＝裸 X.Y 限同句有法規名或 第／§／Clause。"""
    rx = CATS[cat]
    if cat == "編號":
        spans = sorted({(m.start(), m.end()) for r in rx for m in r.finditer(text)}, key=lambda x: (x[0], -(x[1] - x[0])))
        out = []
        for a, b in sorted(spans, key=lambda x: (-(x[1] - x[0]), x[0])):
            if all(b <= a2 or a >= b2 for a2, b2 in out):
                out.append((a, b))
        return [text[a:b] for a, b in sorted(out)]
    if cat == "條號":
        res = []
        for sm in RE_SENT.finditer(text):
            sent = sm.group(0)
            ok = CATS["法規"].search(sent) or RE_CLAUSE_CUE.search(sent)
            res += [m.group(0) for m in (RE_BARE_XY if ok else rx).finditer(sent)]
        return res
    if cat == "中文數字":
        return [m.group(0) for m in rx.finditer(mask_whitelist(text))]
    return [m.group(0) for m in rx.finditer(text)]
RE_PLACEHOLDER = re.compile(r"\$\{[^}]{0,40}\}|[A-Za-z0-9\-/_.]*(?:X{2,}|O{2,}|YYYY|DDMMMYYYY)[A-Za-z0-9\-/_.]*|○{2,}|＿{3,}|_{3,}")


def read_text(path):
    """回傳 str（txt／md）或 [(段落文字, 是否在表格儲存格內)]（docx；v1.2 供條號規則排除儲存格）。"""
    if path.lower().endswith(".docx"):
        z = zipfile.ZipFile(path)
        root = ET.fromstring(z.read("word/document.xml"))
        in_cell = {id(p) for tc in root.iter(W + "tc") for p in tc.iter(W + "p")}
        return [("".join(t.text or "" for t in p.iter(W + "t")), id(p) in in_cell) for p in root.iter(W + "p")]
    with open(path, encoding="utf8") as f:
        return f.read()


def _ns(s):
    return re.sub(r"\s+", "", s)


def mask(cat, v):
    if cat == "數值":
        m = re.match(r"(\d+(?:\.\d+)?)\s*(.*)$", v)
        num = "N.N" if "." in m.group(1) else "N"
        return f"{num} {m.group(2)}"
    if cat == "編號":
        return re.sub(r"\d", "9", re.sub(r"[A-Za-z]+", "X", v))
    if cat == "日期":
        return re.sub(r"\d", "9", re.sub(r"(?i)" + _MON, "MMM", v))
    return re.sub(r"\d", "9", v)


def scan(text, allow, strip_placeholders=True):
    """text＝str，或 [(段落文字, 在儲存格內)]；後者的儲存格段落不參與裸 X.Y 條號判定（其餘類照常）。"""
    segs = text if isinstance(text, list) else [(text, False)]
    ph = 0
    if strip_placeholders:
        segs2 = []
        for t, c in segs:
            t, n = RE_PLACEHOLDER.subn(" ", t)
            ph += n
            segs2.append((t, c))
        segs = segs2
    text = "\n".join(t for t, _ in segs)
    cell_text = "\n".join(t for t, c in segs if c)
    intake = allow.get("intake", {}) or {}
    refs = [_ns(r) for r in allow.get("refs", []) or []]
    rules = [re.compile(r) for r in allow.get("numbering_rules", []) or []]
    sets = {"數值": {_ns(x) for x in intake.get("數值", [])},
            "日期": {_ns(x) for x in intake.get("日期", [])},
            "編號": {_ns(x) for x in intake.get("編號", [])},
            "中文數字": {_ns(x) for x in intake.get("中文數字", [])},
            "量詞數": {_ns(x) for x in intake.get("量詞數", [])} | {_ns(x) for x in intake.get("數值", [])}}
    cn_equiv = []

    def allowed(cat, v):
        n = _ns(v)
        if cat == "中文數字":
            if n in sets[cat]:
                return True
            ar = cn_to_arabic(n)
            if ar and ar in sets["量詞數"]:
                cn_equiv.append({"original": v, "arabic": ar})
                return True
            return False
        if cat in ("數值", "日期"):
            return n in sets[cat]
        if cat == "編號":
            return n in sets["編號"] or any(r.fullmatch(v) for r in rules)
        return any(n in r for r in refs)
    res = OrderedDict()
    for cat in CATS:
        if cat == "條號":                     # 儲存格內只算明示式（第N條／§／Clause），不算裸 X.Y
            found = find_all(cat, "\n".join(t for t, c in segs if not c)) + [m.group(0) for m in CATS[cat].finditer(cell_text)]
        else:
            found = find_all(cat, text)
        vals = Counter(_ns(v) for v in found)
        ok = {v for v in vals if allowed(cat, v)}
        diff = sorted(set(vals) - ok)
        res[cat] = {"hits": len(vals), "allowed": len(ok), "diff": len(diff),
                    "diff_masked": Counter(mask(cat, v) for v in diff)}
    res["中文數字"]["equiv"] = cn_equiv
    return res, ph


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--allow", required=True)
    ap.add_argument("--keep-placeholders", action="store_true")
    a = ap.parse_args()
    try:
        text = read_text(a.input)
        allow = json.load(open(a.allow, encoding="utf8"))
    except Exception as e:
        print(f"🔴 封閉集合掃描器：輸入或 allow 讀不到（{type(e).__name__}）", file=sys.stderr)
        sys.exit(2)
    res, ph = scan(text, allow, not a.keep_placeholders)
    total = sum(r["diff"] for r in res.values())
    print(f"| 類別 | 命中（相異） | 允許 | 差集 |")
    print(f"|---|---:|---:|---:|")
    for cat, r in res.items():
        print(f"| {cat} | {r['hits']} | {r['allowed']} | {r['diff']} |")
    print(f"\n佔位符剔除：{ph} 處　差集合計：{total}")
    for cat, r in res.items():
        for m, n in sorted(r["diff_masked"].items()):
            print(f"- {cat}｜{m}｜×{n}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
