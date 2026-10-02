#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 資料充足度測試（設備確效）v1.1 — 工單【NK1・充足度測試 v1.1 重跑】2026-09-26。

純腳本、零原句：只輸出**數字、分類名、節名、法規名**，不輸出任何段落／句子內文。
同輸入同輸出（無時間戳、無隨機、所有迭代皆排序）。

用法：
  python3 scripts/nk1-sufficiency.py --thresholds specs/充足度測試_定義_v1.1.json [--root DIR] [--out REPORT.md]

  --thresholds  定義檔（群別、範圍、門檻、判定）。**必填**——腳本不內建門檻、不自調。
  --root        預設 ~/nk1-data/templates/NK-templates（repo 外，原檔永不進 repo）
  --out         預設印到 stdout

計算口徑（定義檔未明寫、由阿K 定的部分，逐條見 specs/充足度測試_定義_v1.1.md §三）：
  節名重合率＝Jaccard；R1 兩側節數皆需 ≥ 門檻；R3 欄位候選＝節內「數值＋單位／型號／日期／職稱」
  四計數之和，取兩側較大者；R4「含條號」＝第…條／21 CFR x.y／§。
"""
import argparse, difflib, hashlib, json, os, re, sys, zipfile
from collections import Counter, OrderedDict
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nk1_normalize import normalize, NORMALIZE_VERSION  # noqa: E402
import nk1_codes  # noqa: E402  M5.8：定義檔只寫代號，讀檔時經 repo 外對照表換回真資料夾名

SCRIPT_VERSION = "1.1.0"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# ── 步驟 0：關鍵詞（僅供 E4–E6「只列」的範圍對照）────────────────────
KW = ["設備", "機器", "儀器", "確效", "驗證", "校正", "IQ", "OQ", "PQ", "URS", "DQ"]
HEAD_LINE = re.compile(r"^\s*(#{1,6}\s*\S|[【\[].{1,30}[】\]]|(\d+(\.\d+)*|[一二三四五六七八九十]+)[\.、．)）]\s*\S|第.{1,3}[章節條])")
LIST_ONLY = OrderedDict([                               # 只列不跑（沿用 v1.0 分類規則）
    ("E4 電腦化系統確效", re.compile(r"^(T028|T029|T030) ")),
    ("E5 分析方法確效", re.compile(r"分析方法")),
    ("E6 邊緣命中", re.compile(r".")),
])

# ── R3 變數計數 ─────────────────────────────────────────────────
UNIT = r"(℃|°C|%|mm|cm|μm|um|m³|m3|m|kg|mg|μg|ug|g|mL|ml|μL|uL|L|min|分鐘|小時|hr|h|秒|sec|s|rpm|kPa|MPa|Pa|psi|bar|V|kW|W|Hz|lux|Lux|ppm|ppb|CFU|cfu|次|天|日|個月|週|年|級)"
RE_NUMUNIT = re.compile(r"\d+(?:\.\d+)?\s*(?:[~～\-–]\s*\d+(?:\.\d+)?\s*)?" + UNIT)
RE_MODEL = re.compile(r"\b[A-Z]{1,6}-?\d{2,}[A-Z0-9\-]*\b")
RE_DATE = re.compile(r"\d{4}\s*[/.\-年]\s*\d{1,2}\s*[/.\-月]\s*\d{1,2}|\d{4}年\d{1,2}月")
TITLES = ["總經理", "副總", "廠長", "處長", "經理", "副理", "課長", "組長", "主任", "主管", "工程師", "技術員",
          "專員", "助理", "操作員", "操作人員", "負責人", "品保人員", "品管人員", "文管", "管理代表", "授權人"]
RE_TITLE = re.compile("|".join(sorted(TITLES, key=len, reverse=True)))
RE_PLACEHOLDER = re.compile(r"YYYY|MM/DD|DD/MM|\$\{[^}]{0,40}\}|X{3,}|O{2,}|○{2,}|＿{3,}|_{3,}")

# ── R4 法規樣式 ─────────────────────────────────────────────────
LAWS = [
    re.compile(r"藥事法(?:\s*第\s*[\d一二三四五六七八九十百]+\s*條)?"),
    re.compile(r"(?:西藥)?藥品優良製造(?:作業)?規範(?:\s*第\s*[\d一二三四五六七八九十]+\s*[部章條])?"),
    re.compile(r"PIC/?S(?:\s*GMP)?(?:\s*PE\s*009-\d+)?(?:\s*Annex\s*\d+)?", re.I),
    re.compile(r"EU\s*GMP(?:\s*Annex\s*\d+)?(?:\s*Chapter\s*\d+)?", re.I),
    re.compile(r"(?<!GMP )Annex\s*\d+", re.I),
    re.compile(r"21\s*CFR\s*(?:Part\s*)?\d+(?:\.\d+)?", re.I),
    re.compile(r"ICH\s*Q\d+[A-Z]?(?:\s*\(R\d\))?", re.I),
    re.compile(r"ISO\s*\d{3,5}(?:-\d+)?"),
    re.compile(r"GAMP\s*\d"),
    re.compile(r"USP\s*<\s*\d+\s*>"),
    re.compile(r"WHO\s*TRS\s*\d+"),
    re.compile(r"人體細胞組織優良操作規範"),
    re.compile(r"再生醫療(?:製劑)?(?:條例|法)(?:\s*第\s*[\d一二三四五六七八九十]+\s*條)?"),
]
RE_CLAUSE = re.compile(r"第\S+條|CFR (?:Part )?\d+\.\d+|§")

# ── R5 審閱意見六類（🔶 阿K 自訂關鍵詞；依序先中先歸）──────────────
R5_CATS = [
    ("缺節", re.compile(r"缺少|缺漏|未列|漏列|增加.{0,6}(章節|段落|項目)|新增.{0,6}(章節|段落|項目)|補充|補上|應包含|未包含|遺漏")),
    ("缺數值", re.compile(r"數值|範圍|規格|限值|允收|標準值|溫度|濕度|壓差|時間|頻率|單位|參數")),
    ("格式", re.compile(r"格式|字體|排版|版面|表格|標點|字型|粗體|縮排|樣式")),
    ("編號", re.compile(r"編號|版次|版本|序號|代號|碼")),
    ("引用", re.compile(r"引用|參考|依據|法規|SOP|程序書|附件|出處")),
]
R5_ORDER = ["缺節", "缺數值", "格式", "編號", "引用", "其他"]

# ── 節名：計算用鍵 vs 顯示用名（零原句）───────────────────────────
RE_NUMHEAD = re.compile(r"^\s*(\d+(?:\.\d+){0,3})[\.、．\s]\s*(\S.*)$")
RE_CNHEAD = re.compile(r"^\s*(第[\d一二三四五六七八九十]+[章節]|[一二三四五六七八九十]+[、.．])\s*(\S.*)$")
RE_SENTENCE = re.compile(r"[，,、。；;!?！？]|\.\.|為|請|應|可以|一下|並|之|的|有點|如何|須|需要|撰寫|說明|依照|融入|進行|按下|視情況|可併|如$")
EN_VOCAB = set("""appendix appendices approver approval approved author content date name signature title reviewer
reviewed procedure scope definition definitions purpose references reference policy responsibilities responsibility
forms form attachment remark management specialist manager director upkeep version page department dept distribution
accuracy precision linearity robustness range security risk high low medium negative positive invalid revision history
plan report doc issued user prepared associated documents general requirements cleaning line clearance routine use
questionnaires testing results persona core task context objective role qualification system owner overview matrix
audit trail backup restore changes conclusion deviations category part directory standard operating operation
maintenance installation performance design specification requirement records record list table the and for of""".split())
EN_ABBR = set("QA QC EN OO SOP EM GMP GAMP ICH ISO NTC FAM ROX WFI URS DQ IQ OQ PQ PIC CFR TIC MIS RD NA DDMMMYYYY".split())
RE_ORG = re.compile(r"公司|企業|集團|醫院|大學|Inc|Ltd|Corp", re.I)
RE_DOCNO = re.compile(r"[A-Za-z]{1,6}-[A-Za-z0-9\-]*\d[A-Za-z0-9\-]*")


def section_key(text):
    """標題文字 → 計算用節鍵（去編號、截冒號、遮文件編號、正規化、去數字、1–20 字）。永不直接輸出。"""
    t = text.strip()
    m = RE_NUMHEAD.match(t) or RE_CNHEAD.match(t)
    if m:
        t = m.group(2)
    t = re.split(r"[:：]", t, 1)[0]
    t = RE_DOCNO.sub("", t)
    n = re.sub(r"\d", "", normalize(t)).strip(".-()/#' ")
    if not n or len(n) > 20 or re.search(r"[，,。；;!?！？]", n):
        return None
    return n


def display(k):
    """計算用節鍵 → 可列節名；像句子／過長回 None（只計數不列），機構名與非標題英文詞遮蔽。"""
    core = re.sub(r"\(.*$", "", k)
    if len(re.sub(r"[A-Za-z]", "", core)) > 8 or RE_SENTENCE.search(k):
        return None
    if RE_ORG.search(k):
        return "[遮・機構名]"
    for tok in re.findall(r"[A-Za-z]+", k):
        for w in re.findall(r"[A-Z]{2,}(?![a-z])|[A-Z]?[a-z]+|[A-Z]", tok):
            if len(w) >= 3 and not w.isupper() and w.lower() not in EN_VOCAB:
                return "[遮・英文詞]"
            if len(w) >= 3 and w.isupper() and w not in EN_ABBR:
                return "[遮・英文詞]"
    return k


def names_line(keys):
    shown = sorted({display(k) for k in keys if display(k)})
    hidden = sum(1 for k in set(keys) if display(k) is None)
    return "｜".join(shown) + (f"（另 {hidden} 節名像句子／過長，只計不列）" if hidden else "")


def sha8(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:8]


# ── docx ───────────────────────────────────────────────────────
def classify_docx(path):
    """v1.1：A＝程式輸出（creator 空＋1970）；B＝真人 Word（creator 非空＋時間真實）；C＝其餘。"""
    if "審閱意見回饋" in os.path.basename(path):
        return "C"
    try:
        z = zipfile.ZipFile(path)
    except Exception:
        return "C"                                    # 加密／無法解壓
    if "docProps/core.xml" not in z.namelist():
        return "C"
    x = z.read("docProps/core.xml").decode("utf8", "ignore")
    cr = re.search(r"<dc:creator>([^<]*)<", x)
    d = re.search(r"<dcterms:created[^>]*>([^<]*)<", x)
    cr = cr.group(1).strip() if cr else ""
    epoch = (d.group(1) if d else "")[:4] == "1970"
    if not cr and epoch:
        return "A"
    if cr and d and not epoch:
        return "B"
    return "C"                                        # 待查（creator 空但時間真實等）


def _ptext(p):
    return "".join(t.text or "" for t in p.iter(W + "t"))


def load_docx(path):
    try:
        z = zipfile.ZipFile(path)
        root = ET.fromstring(z.read("word/document.xml"))
    except Exception:
        return None
    names = {}
    if "word/styles.xml" in z.namelist():
        try:
            for s in ET.fromstring(z.read("word/styles.xml")).iter(W + "style"):
                n = s.find(W + "name")
                names[s.get(W + "styleId")] = (n.get(W + "val") if n is not None else "") or ""
        except Exception:
            pass
    # 表格內段落一併攤平、依文件順序（地基 docx 以表格為骨架）
    blocks = []
    for p in root.iter(W + "p"):
        ps = p.find(f"{W}pPr/{W}pStyle")
        sid = ps.get(W + "val") if ps is not None else ""
        style = (names.get(sid, sid) or "").lower()
        if p.find(f"{W}pPr/{W}numPr") is not None:
            style += "|#num"
        runs = [r for r in p.iter(W + "r") if "".join(t.text or "" for t in r.iter(W + "t")).strip()]
        if runs and all(r.find(f"{W}rPr/{W}b") is not None for r in runs):
            style += "|#bold"
        blocks.append((_ptext(p), style))
    empty = sum(1 for tc in root.iter(W + "tc") if not "".join(_ptext(p) for p in tc.iter(W + "p")).strip())
    comments = []
    if "word/comments.xml" in z.namelist():
        try:
            for c in ET.fromstring(z.read("word/comments.xml")).iter(W + "comment"):
                comments.append("".join(_ptext(p) for p in c.iter(W + "p")))
        except Exception:
            pass
    rev = sum(1 for _ in root.iter(W + "ins")) + sum(1 for _ in root.iter(W + "del"))
    text = "\n".join(t for t, _ in blocks)
    return {"blocks": blocks, "text": text, "empty_cells": empty, "comments": comments, "revisions": rev,
            "placeholders": len(RE_PLACEHOLDER.findall(text))}


def is_heading(text, style):
    t = text.strip()
    if not t or len(t) > 40 or t.endswith(("。", "；", ";")) or style.startswith("toc"):
        return False
    if re.search(r"heading|標題|title", style) or re.fullmatch(r"[1-9]", style.split("|")[0] or "x"):
        return True
    if ("#num" in style or "#bold" in style) and len(t) <= 20 and not re.search(r"[，,。；;]", t):
        return True
    return bool(RE_NUMHEAD.match(t) and not re.match(r"^\s*\d+(\.\d+)?\s*(%|℃|°|mm|cm|kg|g|L|mL)", t)) or bool(RE_CNHEAD.match(t))


def sections(doc):
    """OrderedDict 節鍵 → 內文（僅供計算，永不輸出）。"""
    out, cur = OrderedDict(), None
    for text, style in doc["blocks"]:
        if is_heading(text, style):
            k = section_key(text)
            if k:
                cur = k
                out.setdefault(cur, [])
                continue
        if cur is not None:
            out[cur].append(text)
    return OrderedDict((k, "\n".join(v)) for k, v in out.items())


# ── prompt ─────────────────────────────────────────────────────
def prompt_first(path):
    try:
        m = json.load(open(path, encoding="utf8"))
        return m[0]["content"] if isinstance(m, list) and m else ""
    except Exception:
        return ""


def prompt_style1(c):
    """樣式 1：標題樣式行（≤40 字）或冒號結尾行。"""
    return [s.strip() for s in c.splitlines()
            if s.strip() and len(s.strip()) <= 40 and (HEAD_LINE.match(s.strip()) or s.strip().endswith(("：", ":")))]


RE_S2_SPLIT = re.compile(r"(?:^|(?<=[\s。；;，,:：]))(?:\d{1,2}(?:\.\d{1,2}){1,3}[\.、]?(?![\d.])|\d{1,2}[\.、)）](?!\d)|[\(（]\d{1,2}[\)）]|[一二三四五六七八九十]+、|[•●■▪◆◦・]|-\s)")
RE_S2_COLON = re.compile(r"(?:^|(?<=[。；;，,\n\s]))([^。；;，,\n\s：:]{1,20})[：:]")


def prompt_style2(c):
    """樣式 2（v1.1 改動 1）：條列符號／編號行（含行內、含 X.Y 多層編號）／冒號前段 → 節候選文字。"""
    cands = []
    parts = RE_S2_SPLIT.split(c)
    if len(parts) > 1:
        for seg in parts[1:]:
            cands.append(re.split(r"[：:，,。；;\n]", seg.strip(), 1)[0])
    cands += RE_S2_COLON.findall(c)
    return cands


# ── 比對 ───────────────────────────────────────────────────────
def strip_vars(s):
    s = normalize(s)
    s = RE_DATE.sub("", s)
    s = re.sub(r"\(\s*[\da-zA-Z]{1,3}\s*\)|\b[a-zA-Z]\)", "", s)
    return re.sub(r"\d+", "", s)


def ratio(a, b):
    a, b = a[:20000], b[:20000]
    if not a or not b:
        return None
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def varcount(s):
    return (len(RE_NUMUNIT.findall(s)), len(RE_MODEL.findall(s)), len(RE_DATE.findall(s)), len(RE_TITLE.findall(s)))


def jac(x, y):
    x, y = set(x), set(y)
    return None if not (x and y) else len(x & y) / len(x | y)


def _canon_law(h):
    h = re.sub(r"\s+", " ", h).strip()
    h = re.sub(r"(?i)^pic/?s", "PIC/S", h)
    h = re.sub(r"(?i)\bpart\b", "Part", h)
    h = re.sub(r"(?i)\bannex\b", "Annex", h)
    h = re.sub(r"GAMP ?(\d)", r"GAMP \1", h)
    h = re.sub(r"ISO ?(\d)", r"ISO \1", h)
    h = re.sub(r"(?i)^ich ?q", "ICH Q", h)
    h = re.sub(r"(?i)^21 ?cfr ?", "21 CFR ", h)
    h = re.sub(r"Part ?(\d)", r"Part \1", h)
    h = re.sub(r"PIC/S ?GMP", "PIC/S GMP", h)
    return re.sub(r"第 ?(\S+?) ?([條章部])", r"第\1\2", h)


def laws(s):
    return {_canon_law(m.group(0)) for rx in LAWS for m in rx.finditer(s)}


def r5(comments):
    c = Counter({k: 0 for k in R5_ORDER})
    for t in comments:
        for k, rx in R5_CATS:
            if rx.search(t):
                c[k] += 1
                break
        else:
            c["其他"] += 1
    return c


def pct(x):
    return "—" if x is None else f"{round(x * 100)}%"


def med(xs):
    xs = sorted(xs)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * (len(xs) - 1) + 0.5))] if xs else None


# ── 每夾 ───────────────────────────────────────────────────────
def analyze_folder(root, d, style2_prefixes, T):
    fp = os.path.join(root, d)
    files = sorted(os.listdir(fp))
    docx = [f for f in files if f.lower().endswith(".docx")]
    js = [f for f in files if f.lower().endswith(".json")]
    pdf = [f for f in files if f.lower().endswith(".pdf")]
    grp = {f: classify_docx(os.path.join(fp, f)) for f in docx}
    docs = {f: load_docx(os.path.join(fp, f)) for f in docx}
    ptxt = "\n".join(prompt_first(os.path.join(fp, j)) for j in js)
    s1 = prompt_style1(ptxt)
    k1 = sorted({k for k in map(section_key, s1) if k})
    k2 = []
    if not s1 and any(d.startswith(p) for p in style2_prefixes):
        k2 = sorted({k for k in map(section_key, prompt_style2(ptxt)) if k})
    pk = k1 or k2
    secs = {f: sections(docs[f]) for f in docx if docs[f]}
    A = [f for f in docx if grp[f] == "A" and docs[f]]
    B = [f for f in docx if grp[f] == "B" and docs[f]]
    C = [f for f in docx if grp[f] == "C"]
    ak = sorted({k for f in A for k in secs[f]})
    bk = sorted({k for f in B for k in secs[f]})

    def pair(a, b):
        rows = []
        for k in [k for k in secs[a] if k in secs[b]]:
            rows.append((k, ratio(strip_vars(secs[a][k]), strip_vars(secs[b][k])),
                         varcount(secs[a][k]), varcount(secs[b][k])))
        return {"a": a, "b": b, "rows": rows}

    def r23(pairs):
        """每對算 R2 固定節數、R3 變數節數；回傳 (R2 過?, R3 過?)。"""
        r2 = r3 = False
        for pr in pairs:
            fixed = sum(1 for _, x, _, _ in pr["rows"] if x is not None and x * 100 >= T["R2_sim_min_pct"])
            var = sum(1 for _, x, va, vb in pr["rows"] if x is not None and x * 100 <= T["R3_sim_max_pct"]
                      and max(sum(va), sum(vb)) >= T["R3_fields_min"])
            r2 = r2 or fixed >= T["R2_sections_min"]
            r3 = r3 or var >= T["R3_sections_min"]
        return r2, r3

    p1 = [pair(a, b) for a in A for b in B]                                  # (i) A→B 同夾
    p3 = [pair(B[i], B[j]) for i in range(len(B)) for j in range(i + 1, len(B))]  # (iii) B 群內版本
    # (ii) prompt 節→B 節（結構重合率，逐份 B）
    p2 = [(b, len(pk), len(secs[b]), jac(pk, secs[b].keys())) for b in B] if pk else []

    def r1_ok(n1, n2, ov):
        return n1 >= T["R1_sections_min"] and n2 >= T["R1_sections_min"] and ov is not None and ov * 100 >= T["R1_overlap_min_pct"]
    r1_i = any(r1_ok(len(secs[pr["a"]]), len(secs[pr["b"]]), jac(secs[pr["a"]].keys(), secs[pr["b"]].keys())) for pr in p1)
    r1_ii = any(r1_ok(n1, n2, ov) for _, n1, n2, ov in p2)
    r2_i, r3_i = r23(p1)
    r2_iii, r3_iii = r23(p3)
    lh = {"prompt": laws(ptxt)}
    for g, lst in (("A", A), ("B", B), ("C", [f for f in C if docs[f]])):
        lh[g] = set().union(*[laws(docs[f]["text"]) for f in lst]) if lst else set()
    rv = [f for f in docx if "審閱意見回饋" in f and docs[f]]
    return {
        "dir": d, "n": Counter(grp.values()), "prompt": bool(js), "pdf": len(pdf),
        "review": sum(1 for f in docx if "審閱意見回饋" in f),
        "kw": sorted({k for k in KW if k in d} | {k for s in s1 for k in KW if k in s}),
        "s1": len(k1), "s2": len(k2), "pk": pk, "ak": ak, "bk": bk,
        "secs": secs, "A": A, "B": B, "docs": docs,
        "p1": p1, "p2": p2, "p3": p3,
        "R1": (r1_i or r1_ii, "i" if r1_i else ("ii" if r1_ii else "")),
        "R2": (r2_i or r2_iii, "i" if r2_i else ("iii" if r2_iii else "")),
        "R3": (r3_i or r3_iii, "i" if r3_i else ("iii" if r3_iii else "")),
        "R4": lh, "R4c": sorted(h for v in lh.values() for h in v if RE_CLAUSE.search(h)),
        "R5": {"files": len(rv), "comments": sum(len(docs[f]["comments"]) for f in rv),
               "revisions": sum(docs[f]["revisions"] for f in rv),
               "cats": r5([c for f in rv for c in docs[f]["comments"]])},
        "R6": len(p1),
        "fields": {g: sum(sum(varcount(docs[f]["text"])) for f in docx if grp[f] == g and docs[f]) for g in "ABC"},
    }


# ── 報告 ───────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thresholds", required=True)
    ap.add_argument("--root", default=os.path.expanduser("~/nk1-data/templates/NK-templates"))
    ap.add_argument("--out")
    a = ap.parse_args()
    D = json.load(open(a.thresholds, encoding="utf8"))
    T = D["thresholds"]
    root = a.root
    if not os.path.isdir(root):
        print(f"🔴 找不到資料根：{root}", file=sys.stderr)
        sys.exit(2)
    zipf = os.path.join(os.path.dirname(os.path.dirname(root.rstrip("/"))), "NK-templates_20260918.zip")
    dirs = sorted(x for x in os.listdir(root) if os.path.isdir(os.path.join(root, x)))
    CR = nk1_codes.load()
    S2 = [nk1_codes.folder_of(c, CR) for c in D.get("prompt_style2_prefixes", [])]

    def folders(prefixes):
        return [nk1_codes.folder_of(p, CR) for p in prefixes]  # 代號＝單一資料夾（原前綴比對已由代號取代）
    run_cls = OrderedDict()
    for tier, tag in (("core", "核心"), ("second", "第二圈")):
        for c, pre in D["scope"][tier].items():
            run_cls[c] = (tag, folders(pre))
    run_dirs = [x for _, fs in run_cls.values() for x in fs]
    res = {x: analyze_folder(root, x, S2, T) for x in run_dirs}

    L = []
    P = L.append
    rp = lambda x: os.path.join(root, x)
    P("# NK1 資料充足度測試 — 設備確效 v1.1（2026-09-26）")
    P("")
    P("| 標頭 | 值 |")
    P("|---|---|")
    P(f"| 腳本 | `scripts/nk1-sufficiency.py` v{SCRIPT_VERSION}（normalize v{NORMALIZE_VERSION}）；同輸入同輸出 |")
    P(f"| 定義檔 | `specs/充足度測試_定義_v1.1.json` sha256 前 8＝`{sha8(a.thresholds)}`；口徑說明 `specs/充足度測試_定義_v1.1.md` |")
    P(f"| 資料根 | `~/nk1-data/templates/NK-templates/`（**repo 外**）；來源包 sha256 前 8＝`{sha8(zipf) if os.path.isfile(zipf) else '查不到'}` |")
    P("| 內容規則 | **零原句**：只出數字、分類名、節名（≤20 字；像句子者只計不列；機構名／非標題英文詞遮蔽）、法規名 |")
    P("| 群別 | " + "；".join(f"**{k}**＝{v}" for k, v in D["groups"].items()) + " |")
    P("| 門檻 | " + "、".join(f"{k}={v}" for k, v in T.items()) + "（**不自調**） |")
    P("| 判定 | " + D["verdict"] + " |")
    P("")
    P("---")
    P("")
    P("## 步驟 0：範圍")
    P("")
    P("| 圈 | 類 | 資料夾 | A 程式輸出 | B 真人 Word | C 其餘 | prompt | pdf | 審閱回饋 |")
    P("|---|---|---|---:|---:|---:|---|---:|---:|")
    for c, (tag, fs) in run_cls.items():
        for x in fs:
            r = res[x]
            P(f"| {tag} | {c.split(' ')[0]} | `{x}` | {r['n']['A']} | {r['n']['B']} | {r['n']['C']} | "
              f"{'有' if r['prompt'] else '無'} | {r['pdf']} | {r['review']} |")
    P("")
    P("**只列不跑**（E4／E5／E6，沿用 v1.0 關鍵詞命中規則，不出 R1–R6）：")
    lo = OrderedDict((k, []) for k in LIST_ONLY)
    for x in dirs:
        if x in run_dirs:
            continue
        js = [f for f in os.listdir(rp(x)) if f.lower().endswith(".json")]
        ptxt = "\n".join(prompt_first(os.path.join(rp(x), j)) for j in sorted(js))
        first = re.split(r"[。，,；;\n]", ptxt.strip(), 1)[0][:60] if ptxt.strip() else ""
        if not ({k for k in KW if k in x} | {k for s in [first] + prompt_style1(ptxt) for k in KW if k in s}):
            continue
        for k, rx in LIST_ONLY.items():
            if rx.search(f"{nk1_codes.code_of(x, CR)} {x}"):  # 代號＋真名：E4 比代號，E5／E6 比名稱
                lo[k].append(x)
                break
    for k, v in lo.items():
        P(f"- {k}（{len(v)}）：" + "、".join(f"`{x}`" for x in v))
    P("")
    P("---")
    P("")
    P("## 改動 1：prompt 兩種樣式抽節數")
    P("")
    P("| 資料夾 | 樣式 1（標題樣式行） | 樣式 2（條列／編號／冒號，僅 LC-EN 且樣式 1＝0 時） | 採用 |")
    P("|---|---:|---:|---|")
    for x in run_dirs:
        r = res[x]
        P(f"| `{x}` | {r['s1']} | {r['s2'] if any(x.startswith(p) for p in S2) and not r['s1'] else '—'} | "
          f"{'樣式 1' if r['s1'] else ('樣式 2' if r['s2'] else '無')} |")
    P(f"\n合計：樣式 1 {sum(res[x]['s1'] for x in run_dirs)} 節、樣式 2 {sum(res[x]['s2'] for x in run_dirs)} 節。")
    P("")
    P("---")
    P("")
    P("## 步驟 1：每夾 R1–R6 與三種配對")
    P("")
    for c, (tag, fs) in run_cls.items():
        P(f"### {c}（{tag}）")
        P("")
        for x in fs:
            r = res[x]
            P(f"#### `{x}`")
            P("")
            P(f"**R1 骨架**　節數 prompt／A／B＝{len(r['pk'])}／{len(r['ak'])}／{len(r['bk'])}")
            for g, ks in (("prompt", r["pk"]), ("A", r["ak"]), ("B", r["bk"])):
                if ks:
                    P(f"- {g}：{names_line(ks)}")
            fl = r["fields"]
            P(f"- 全文欄位候選（數值單位＋型號＋日期＋職稱）：A {fl['A']}／B {fl['B']}／C {fl['C']}")
            if tag == "第二圈":
                for f in r["A"]:
                    P(f"- 「三顧模板樣本」A[{sha8(os.path.join(rp(x), f))}]：節 {len(r['secs'][f])}・佔位符 {r['docs'][f]['placeholders']}・空表格格 {r['docs'][f]['empty_cells']}")
            P("")
            P("**(i) A→B 同夾**　" + ("無配對" if not r["p1"] else ""))
            for pr in r["p1"]:
                P(f"- A[{sha8(os.path.join(rp(x), pr['a']))}]→B[{sha8(os.path.join(rp(x), pr['b']))}]：節名重合 "
                  f"{pct(jac(r['secs'][pr['a']].keys(), r['secs'][pr['b']].keys()))}・同名節 {len(pr['rows'])}")
            _rows(P, r["p1"])
            P("")
            P("**(ii) prompt 節→B 節**　" + ("無（prompt 0 節或無 B）" if not r["p2"] else ""))
            for b, n1, n2, ov in r["p2"]:
                P(f"- prompt({n1} 節)→B[{sha8(os.path.join(rp(x), b))}]({n2} 節)：結構重合率 {pct(ov)}")
            P("")
            P("**(iii) B 群內版本對版本**（客戶成品版本間，非三顧模板配對）　" + ("無（B <2 份）" if not r["p3"] else ""))
            for pr in r["p3"]:
                rs = [z[1] for z in pr["rows"] if z[1] is not None]
                P(f"- B[{sha8(os.path.join(rp(x), pr['a']))}]↔B[{sha8(os.path.join(rp(x), pr['b']))}]：同名節 {len(pr['rows'])}・"
                  f"可比 {len(rs)}・中位 {pct(med(rs))}")
            _rows(P, r["p3"])
            P("")
            allh = sorted(set().union(*r["R4"].values()))
            P(f"**R4 法規**　{'、'.join(allh) if allh else '0 命中'}；含條號 {len(r['R4c'])}" + (f"（{'、'.join(r['R4c'])}）" if r['R4c'] else ""))
            R5 = r["R5"]
            P("**R5 審閱回饋**　" + (f"檔 {R5['files']}・批註 {R5['comments']}・修訂標記 {R5['revisions']}；"
                                    + "／".join(f"{k} {R5['cats'][k]}" for k in R5_ORDER) if R5["files"] else "無"))
            src = lambda t: f"（{ {'i': '來自 (i)', 'ii': '來自 (ii)', 'iii': '來自 (iii)'}[t] }）" if t else ""
            P(f"**夾內門檻**　R1 {'過' if r['R1'][0] else '未過'}{src(r['R1'][1])}・R2 {'過' if r['R2'][0] else '未過'}{src(r['R2'][1])}・"
              f"R3 {'過' if r['R3'][0] else '未過'}{src(r['R3'][1])}・R6 配對 {r['R6']} 組")
            P("")

    # 步驟 2
    P("---")
    P("")
    P("## 步驟 2：每類判定")
    P("")
    P("| 類 | 圈 | 夾 | R1 | R2 | R3 | R4 含條號 | R5 審閱 | R6 (i) 配對 | 判定 | 缺項 → 發函題目樁 |")
    P("|---|---|---:|---|---|---|---:|---:|---:|---|---|")
    verdicts = {}
    for c, (tag, fs) in run_cls.items():
        rr = [res[x] for x in fs]
        R1 = any(r["R1"][0] for r in rr)
        R2 = any(r["R2"][0] for r in rr)
        R3 = any(r["R3"][0] for r in rr)
        R4 = len({h for r in rr for h in r["R4c"]})
        R5 = sum(r["R5"]["files"] for r in rr)
        R6 = sum(r["R6"] for r in rr)
        R6ok = R6 >= T["R6_pairs_min"]
        v = "不夠" if not (R1 and R3) else ("夠" if R6ok else "可用但要補")
        verdicts[c] = (tag, v)

        def mark(ok, rs, key):
            srcs = sorted({r[key][1] for r in rs if r[key][0]})
            return ("✅" + ("（" + "/".join(srcs) + "）" if srcs else "")) if ok else "❌"
        stubs = []
        if not R1:
            stubs.append("R1：請提供該類已定稿文件的章節目錄（或含章節要求的需求單）")
        if not R3:
            stubs.append("R3：請提供同一文件的已填寫實例（含數值／型號／日期／職稱），供辨識變數節")
        if not R6ok:
            stubs.append("R6：請提供 NK 輸出與其對應人工定稿的成對檔")
        if R4 < T["R4_laws_with_clause_min"]:
            stubs.append("R4：請提供該類引用法規的條號清單")
        if R5 < T["R5_reviews_min"]:
            stubs.append("R5：請提供 QA 對 NK 輸出的審閱意見")
        P(f"| {c} | {tag} | {len(fs)} | {mark(R1, rr, 'R1')} | {mark(R2, rr, 'R2')} | {mark(R3, rr, 'R3')} | {R4} | {R5} | {R6} | "
          f"**{v}** | {'；'.join(stubs) or '—'} |")
    P("")
    P("R4、R5、R2 不入判定式（判定只看 R1／R3／R6），照列供發函。✅ 後括號＝由哪種配對過關。")
    P("")

    # 步驟 3
    P("---")
    P("")
    P("## 步驟 3：總測")
    P("")
    P("### (i) A→B 同夾：R2／R3 相似度分布（計入總測）")
    P("")
    P("| 類 | 可比同名節 | min | 25% | 中位 | 75% | max | ≥R2 門檻 | ≤R3 門檻 |")
    P("|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    def dist_row(label, xs):
        P(f"| {label} | {len(xs)} | {pct(q(xs,0))} | {pct(q(xs,.25))} | {pct(med(xs))} | {pct(q(xs,.75))} | {pct(q(xs,1))} | "
          f"{sum(1 for z in xs if z*100 >= T['R2_sim_min_pct'])} | {sum(1 for z in xs if z*100 <= T['R3_sim_max_pct'])} |")
    alli, alliii = [], []
    for c, (_, fs) in run_cls.items():
        xs = [z[1] for x in fs for pr in res[x]["p1"] for z in pr["rows"] if z[1] is not None]
        alli += xs
        dist_row(c, xs)
    dist_row("**全體**", alli)
    P("")
    P("### (iii) B 群內版本對版本（客戶成品版本間，非三顧模板配對；**不計入總測**）")
    P("")
    P("| 類 | 可比同名節 | min | 25% | 中位 | 75% | max | ≥R2 門檻 | ≤R3 門檻 |")
    P("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for c, (_, fs) in run_cls.items():
        xs = [z[1] for x in fs for pr in res[x]["p3"] for z in pr["rows"] if z[1] is not None]
        alliii += xs
        dist_row(c, xs)
    dist_row("**全體**", alliii)
    P("")
    core_v = [v for c, (tag, v) in verdicts.items() if tag == "核心"]
    line = "成立" if core_v and all(v == "夠" for v in core_v) else ("不成立" if any(v == "不夠" for v in core_v) else "不明")
    P(f"**總測：{line}**——依據：核心類判定 " + "、".join(f"{c.split(' ')[0]}＝{v}" for c, (tag, v) in verdicts.items() if tag == "核心")
      + f"；(i) 全體可比同名節 {len(alli)}、中位 {pct(med(alli))}；(iii) 另表 {len(alliii)} 節不計入。")
    P("")
    P("---")
    P("")
    P("⚠️ 統計觀察值。**不判樂迦成品可否當配對**（Alex 的題）；(iii) 只出統計。口徑見定義檔 md §三。")
    out, _, left = nk1_codes.encode("\n".join(L) + "\n", CR)  # 進 repo 的報告只留代號
    if left:
        print(f"🔴 報告仍含真號 {len(left)} 處（歧義），拒絕輸出", file=sys.stderr)
        sys.exit(2)
    if a.out:
        open(a.out, "w", encoding="utf8").write(out)
    else:
        sys.stdout.write(out)


def _rows(P, pairs):
    rows = [z for pr in pairs for z in pr["rows"]]
    if not rows:
        return
    P("")
    P("| 同名節 | 相似度 | 一側 數值單位／型號／日期／職稱 | 另側 數值單位／型號／日期／職稱 |")
    P("|---|---:|---|---|")
    hid = 0
    for k, x, va, vb in rows:
        n = display(k)
        if n is None:
            hid += 1
            n = f"[節名不列 #{hid}]"
        P(f"| {n} | {pct(x)} | {'／'.join(map(str, va))} | {'／'.join(map(str, vb))} |")


if __name__ == "__main__":
    main()
