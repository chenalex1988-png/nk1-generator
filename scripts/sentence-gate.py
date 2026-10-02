#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 句子閘（守衛第 6 道）v1.1 — 節名候選若其實是句子、或不在詞彙表，就擋下。

規則檔：specs/guards/sentence_gate.yaml（判準照工單，不自調）。
詞彙表：specs/guards/section_lexicon.yaml（v1.1，工單【NK1・M1】A 段）。
判定（v1.2，decisions 2026-09-27 ① 兩層）：
  - **啟發式**：對所有進 repo 的節名欄生效（reports、specs、骨架 YAML、fixtures…）。
  - **詞彙表**：只對 `specs/T-spec/`、骨架 YAML（含 `sections:` 與 `folded:` 兩鍵的 YAML）、`fixtures/` 生效。
  命中者進 gate-hits（repo 外），不進 repo。規則碼：LEN／PUNCT／PREFIX／NUMUNIT／ENG6（啟發式）＋ LEX（不在詞彙表）。
適用：要進 repo 的 YAML／md 內 `name:` 欄位、reports 內節名清單（`- prompt／A／B／C：a｜b` 行、
「同名節」表格首欄）。`[…]` 形式的佔位符（`[REJ-n]`、`[遮・…]`、`[節名不列 #n]`）不檢。

用法：
  sentence-gate.py --staged                 # 守衛用：只查 staged（無 staged 則工作樹）diff 的新增行
  sentence-gate.py FILE...                  # 整檔查
  sentence-gate.py FILE... --list-out PATH  # 命中清單（含節名）寫到 PATH；**PATH 應在 repo 外**
  --staged 有命中且未給 --list-out 時，清單寫到 ~/nk1-data/gate-hits/staged.tsv（目錄存在才寫）

輸出：stdout 只印計數與 `檔:行 規則碼`，**不印節名本身**（節名只進 --list-out）。
exit：0＝0 命中　1＝有命中　2＝閘自身故障（規則檔讀不到等；fail-closed）
"""
import argparse, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
from nk1_normalize import normalize  # noqa: E402
DEFAULT_RULES = os.path.join(REPO, "specs", "guards", "sentence_gate.yaml")
DEFAULT_LEXICON = os.path.join(REPO, "specs", "guards", "section_lexicon.yaml")
GATE_HITS_DIR = os.path.join(os.path.expanduser("~"), "nk1-data", "gate-hits")
RE_CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]")


def load_rules(path):
    """讀本閘規則檔（只支援「鍵: 值」與「- 清單項」；值可加單／雙引號）。"""
    rules, key = {}, None
    with open(path, encoding="utf8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            m = re.match(r"^\s+-\s+(.*)$", line)
            if m and key:
                rules.setdefault(key, []).append(_unq(m.group(1)))
                continue
            m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
            if not m:
                raise ValueError(f"規則檔無法解析：{line!r}")
            key, val = m.group(1), m.group(2).strip()
            if val:
                rules[key] = int(val) if re.fullmatch(r"\d+", val) else _unq(val)
                key = None
    need = ["max_len", "max_words_en", "forbidden_chars", "forbidden_prefixes", "num_unit_regex", "english_run_min"]
    miss = [k for k in need if k not in rules]
    if miss:
        raise ValueError(f"規則檔缺鍵：{miss}")
    return rules


def lex_key(s):
    """詞彙表比對鍵（🔶 阿K 口徑，M1 B 段）：與充足度報告節鍵同口徑——normalize（NFKC、去空白與多餘符號）、
    去數字、去頭尾 .-()/#' 。報告列出的節名本就是此鍵，真文件節名（含空白、全形）要先轉成同一個鍵才比得上。"""
    return re.sub(r"\d", "", normalize(s)).strip(".-()/#' ")


def load_lexicon(path):
    """詞彙表：`names:` 下的「- 節名」清單。空表＝故障（fail-closed：空表會把一切擋下或被誤當放行）。"""
    names = []
    with open(path, encoding="utf8") as f:
        for raw in f:
            m = re.match(r"^\s+-\s+(.*)$", raw.rstrip("\n"))
            if m:
                names.append(_unq(m.group(1)))
    if not names:
        raise ValueError(f"詞彙表為空：{path}")
    return set(names)


def _unq(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


class Gate:
    def __init__(self, rules, lexicon=None):
        """lexicon＝None 時只跑啟發式（測試／詞彙表建構用）；正式閘一律帶詞彙表。"""
        self.r = rules
        self.lex = None if lexicon is None else {lex_key(n) for n in lexicon}
        self.num = re.compile(rules["num_unit_regex"])
        n = int(rules["english_run_min"])
        self.eng = re.compile(r"(?:[A-Za-z][A-Za-z'\-]*[\s/]+){%d}[A-Za-z][A-Za-z'\-]*" % (n - 1))

    def heuristic(self, name):
        """啟發式層：回傳命中規則碼清單；空＝放行。"""
        s = name.strip()
        hits = []
        words = re.findall(r"[A-Za-z][A-Za-z0-9'\-]*", s)
        if RE_CJK.search(s):                           # 🔶 M4.3 B：雙語節名分開計——中文部分字數、英文部分詞數
            zh = re.sub(r"[A-Za-z][A-Za-z0-9'\-]*|\s+", "", s)
            too_long = len(zh) > int(self.r["max_len"]) or len(words) > int(self.r["max_words_en"])
        else:                                          # 純英文節名以詞數計
            too_long = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", s)) > int(self.r["max_words_en"])
        if too_long:
            hits.append("LEN")
        if any(c in s for c in self.r["forbidden_chars"]):
            hits.append("PUNCT")
        if any(s.startswith(p) for p in self.r["forbidden_prefixes"]):
            hits.append("PREFIX")
        if self.num.search(s):
            hits.append("NUMUNIT")
        if self.eng.search(s):
            hits.append("ENG6")
        return hits

    def check(self, name, use_lex=True):
        """判定＝啟發式擋下 OR（use_lex 時）不在詞彙表；回傳命中規則碼清單，空＝放行。"""
        hits = self.heuristic(name)
        if use_lex and self.lex is not None and lex_key(name) not in self.lex:
            hits.append("LEX")
        return hits


# ── 候選抽取 ───────────────────────────────────────────────────
RE_LIST_LINE = re.compile(r"^\s*-\s*(?:prompt|A|B|C)：(.*)$")
RE_SUFFIX = re.compile(r"（另 \d+ 節名[^）]*）\s*$")
RE_NAME_FIELD = re.compile(r"""(?:^|[\s{,])name:\s*(?:"((?:[^"\\]|\\.)*)"|'([^']*)'|([^,}\n#]+))""")
RE_PLACEHOLDER = re.compile(r"^\[[^\]]*\]$")


def candidates(path, lines):
    """回傳 [(行號, 節名)]；lines 為整檔各行（行號 1 起）。"""
    out = []
    is_md = path.lower().endswith(".md")
    in_tbl = False
    for i, line in enumerate(lines, 1):
        if is_md:
            m = RE_LIST_LINE.match(line)
            if m:
                body = RE_SUFFIX.sub("", m.group(1))
                out += [(i, x) for x in body.split("｜") if x.strip()]
            if line.startswith("| 同名節 |"):
                in_tbl = True
                continue
            if in_tbl:
                if not line.startswith("|"):
                    in_tbl = False
                elif not line.startswith("|---"):
                    out.append((i, line.split("|")[1]))
        for m in RE_NAME_FIELD.finditer(line):
            v = next(g for g in m.groups() if g is not None)
            out.append((i, v.replace('\\"', '"')))
    return [(i, x.strip()) for i, x in out if x.strip() and not RE_PLACEHOLDER.match(x.strip())]


RE_SKEL_KEYS = (re.compile(r"^sections:", re.M), re.compile(r"^folded:", re.M))


def lex_scope(path, lines):
    """詞彙表層適用範圍：specs/T-spec/、fixtures/、骨架 YAML。"""
    rel = os.path.relpath(os.path.abspath(path), REPO) if os.path.isabs(path) or os.path.exists(path) else path
    rel = rel.replace(os.sep, "/")
    if rel.startswith("specs/T-spec/") or rel.startswith("fixtures/"):
        return True
    if re.search(r"\.ya?ml$", path, re.I):
        text = "\n".join(lines)
        return all(r.search(text) for r in RE_SKEL_KEYS)
    return False


def _git(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True, check=True).stdout


def staged_targets():
    """回傳 [(路徑, 全檔各行, 新增行號集合)]；有 staged 查 staged，否則查工作樹。"""
    staged = bool(_git("diff", "--cached", "--name-only").strip())
    diff = _git("diff", "--cached", "-U0") if staged else _git("diff", "-U0")
    targets, cur, added = [], None, set()
    for line in diff.splitlines() + ["diff --git END"]:
        if line.startswith("diff --git"):
            if cur and re.search(r"\.(md|ya?ml)$", cur, re.I):
                content = _git("show", f":{cur}") if staged else open(os.path.join(REPO, cur), encoding="utf8").read()
                targets.append((cur, content.splitlines(), added))
            cur, added = None, set()
        elif line.startswith("+++ "):
            p = line[4:]
            cur = None if p == "/dev/null" else re.sub(r"^b/", "", p)
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            st, n = int(m.group(1)), int(m.group(2) or 1)
            added |= set(range(st, st + n))
    return ("staged diff" if staged else "工作樹 diff"), targets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--rules", default=DEFAULT_RULES)
    ap.add_argument("--lexicon", default=DEFAULT_LEXICON)
    ap.add_argument("--list-out")
    a = ap.parse_args()
    try:
        gate = Gate(load_rules(a.rules), load_lexicon(a.lexicon))
    except Exception as e:
        print(f"🔴 句子閘故障：{e}", file=sys.stderr)
        sys.exit(2)
    if a.staged:
        try:
            src, targets = staged_targets()
        except Exception as e:
            print(f"🔴 句子閘故障：讀 diff 失敗：{e}", file=sys.stderr)
            sys.exit(2)
    else:
        src, targets = "指定檔", []
        for f in a.files:
            with open(f, encoding="utf8") as fh:
                ls = fh.read().splitlines()
            targets.append((f, ls, None))
    ncand, hits = 0, []
    for path, lines, only in targets:
        use_lex = lex_scope(path, lines)
        for ln, name in candidates(path, lines):
            if only is not None and ln not in only:
                continue
            ncand += 1
            codes = gate.check(name, use_lex)
            if codes:
                hits.append((path, ln, name, codes))
    print(f"🔍 句子閘：對象＝{src}　檔數＝{len(targets)}　節名候選＝{ncand}　命中＝{len(hits)}")
    for path, ln, _, codes in hits:
        print(f"   {os.path.basename(path)}:{ln}  {'+'.join(codes)}")
    if hits and not a.list_out and a.staged and os.path.isdir(GATE_HITS_DIR):
        a.list_out = os.path.join(GATE_HITS_DIR, "staged.tsv")
    if a.list_out and hits:
        with open(a.list_out, "w", encoding="utf8") as f:
            for path, ln, name, codes in hits:
                f.write(f"{path}:{ln}\t{'+'.join(codes)}\t{name}\n")
        print(f"   命中清單 → {a.list_out}")
    if hits:
        print("🔴 句子閘【擋下】", file=sys.stderr)
        sys.exit(1)
    print("✅ 句子閘【通過】：0 命中")


if __name__ == "__main__":
    main()
