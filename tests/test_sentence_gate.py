#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""句子閘測試 — 零依賴（unittest）。全部為合成語料，無任何原句。

跑法：python3 -m unittest discover -s tests -v

工單驗收：20 條（10 節名／10 句子）→ 啟發式層 10/10 擋、10/10 放。
KNOWN_GAPS：仿 v1.0 初跑實際漏出型態（無標點、無禁用開頭、≤20 字的批註句／指令句）的合成版——
啟發式層擋不下（v1.0 以 expectedFailure 記錄）；**v1.1 改以詞彙表測：4/4 擋**（工單【NK1・M1】A 段）。
詞彙表測試用合成詞彙表（SYN_LEX），不依賴 repo 內真詞彙表的內容。
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCRIPT = os.path.join(REPO, "scripts", "sentence-gate.py")
_spec = importlib.util.spec_from_file_location("sentence_gate", SCRIPT)
sg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sg)
RULES = sg.load_rules(sg.DEFAULT_RULES)
GATE = sg.Gate(RULES)                                   # 啟發式層（無詞彙表）

NAMES = [                       # 10 條合成節名 → 應放行
    "安裝驗證",
    "允收標準",
    "修改歷程RevisionHistory",
    "目的Purpose",
    "器具材料",
    "權責Responsibility",
    "設備清冊管理",
    "附件二設備狀態標示單",
    "測試結果",
    "Scope and Purpose",
]
SENTENCES = [                   # 10 條合成句子 → 應擋下（每條註明預期命中規則）
    "第三版段落偏長，建議再精簡一些",                 # 批註句（有逗號）  PUNCT
    "請依下列章節撰寫並加入指定細節",                 # 指令句            PREFIX
    "應於每次使用前確認設備狀態標示",                 # 指令句            PREFIX
    "須由品保人員覆核後始得放行",                     # 指令句            PREFIX
    "若溫度偏離設定值則啟動偏差程序",                 # 條件句            PREFIX
    "依據相關法規建立本程序之管理要求",               # 指令句            PREFIX
    "腔體溫度維持在37℃",                              # 含數值單位        NUMUNIT
    "本程序適用於本廠所有生產設備之安裝操作與性能驗證作業",  # 過長      LEN
    "The operator shall verify all alarms before use",  # 英文 ≥6 詞   ENG6
    "定義：列出本文件使用的名詞",                     # 含全形冒號        PUNCT
]
KNOWN_GAPS = [                  # 仿 v1.0 漏出型態的合成版 → 依現行判準擋不下
    "第三版段落偏長建議再精簡一些",                   # 批註句，無標點
    "描述每個部門在本程序中的任務",                   # 指令句，無禁用開頭
    "視需要可移入附錄內",                             # 指令句
    "按住...完成轉速設定",                            # 半形省略號，無全形標點
]


SYN_LEX = set(NAMES) | {"目的", "範圍"}                # 合成詞彙表
LEX_GATE = sg.Gate(RULES, SYN_LEX)


class TestSentenceGate(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(NAMES), 10)
        self.assertEqual(len(SENTENCES), 10)

    def test_names_pass(self):
        passed = [n for n in NAMES if not GATE.heuristic(n)]
        self.assertEqual(len(passed), 10, [n for n in NAMES if GATE.heuristic(n)])
        self.assertTrue(all(not LEX_GATE.check(n) for n in NAMES))   # 在詞彙表內 → 全放

    def test_sentences_blocked(self):
        blocked = [s for s in SENTENCES if GATE.heuristic(s)]
        self.assertEqual(len(blocked), 10, [s for s in SENTENCES if not GATE.heuristic(s)])

    def test_known_gaps_blocked_by_lexicon(self):
        """v1.1：4 條啟發式放行者，以詞彙表測 → 4/4 擋，且規則碼為 LEX。"""
        self.assertEqual(sum(1 for s in KNOWN_GAPS if not GATE.heuristic(s)), 4)
        codes = [LEX_GATE.check(s) for s in KNOWN_GAPS]
        self.assertEqual(sum(1 for c in codes if c), 4)
        self.assertTrue(all(c == ["LEX"] for c in codes))

    def test_v11_prefix_xu_removed(self):
        self.assertEqual(GATE.heuristic("需求規格"), [])

    def test_v11_english_word_count(self):
        self.assertEqual(GATE.heuristic("scope and purpose of plan"), [])          # 5 詞
        self.assertIn("LEN", GATE.heuristic("scope and purpose of this plan"))   # 6 詞
        self.assertIn("LEN", GATE.heuristic("合成節名" * 6))                      # 中文 24 字

    def test_real_lexicon_loads(self):
        lex = sg.load_lexicon(sg.DEFAULT_LEXICON)
        for w in ("目的", "範圍", "程序", "職責", "參考資料", "政策", "定義", "附件和表單"):
            self.assertIn(w, lex)
        self.assertTrue(all(not GATE.heuristic(n) for n in lex))           # 詞彙表內每條都過啟發式

    def test_placeholders_skipped_and_md_extraction(self):
        md = ["- B：安裝驗證｜[遮・英文詞]｜[REJ-1]｜請依下列章節撰寫（另 2 節名像句子／過長，只計不列）",
              "| 同名節 | 相似度 |", "|---|---:|", "| 允收標準 | 80% |", "| [節名不列 #1] | — |", "",
              '  - {n: 1, name: "若溫度偏離則停機", tables: []}']
        got = [x for _, x in sg.candidates("r.md", md)]
        self.assertEqual(got, ["安裝驗證", "請依下列章節撰寫", "允收標準", "若溫度偏離則停機"])

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            ok = os.path.join(d, "ok.yaml")
            bad = os.path.join(d, "bad.yaml")
            open(ok, "w", encoding="utf8").write('sections:\n  - {name: "目的"}\n')
            open(bad, "w", encoding="utf8").write('sections:\n  - {name: "須由品保人員覆核後始得放行"}\n')
            r1 = subprocess.run([sys.executable, SCRIPT, ok], capture_output=True, text=True)
            r2 = subprocess.run([sys.executable, SCRIPT, bad], capture_output=True, text=True)
            self.assertEqual(r1.returncode, 0)
            self.assertEqual(r2.returncode, 1)
            self.assertNotIn("品保人員", r2.stdout)       # stdout 不印節名

    def test_bad_rules_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.yaml")
            open(p, "w", encoding="utf8").write("max_len: 20\n")
            r = subprocess.run([sys.executable, SCRIPT, "--rules", p, p], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            e = os.path.join(d, "empty.yaml")
            open(e, "w", encoding="utf8").write("names:\n")
            r = subprocess.run([sys.executable, SCRIPT, "--lexicon", e, p], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)                                   # 空詞彙表 fail-closed


    def test_v12_lex_scope_two_layers(self):
        """decisions 2026-09-27 ①：詞彙表層只對 specs/T-spec/、fixtures/、骨架 YAML。"""
        self.assertTrue(sg.lex_scope("specs/T-spec/x.md", []))
        self.assertTrue(sg.lex_scope("fixtures/x.yaml", []))
        self.assertTrue(sg.lex_scope("/tmp/s.yaml", ["sections:", "  - {name: \"a\"}", "folded:"]))
        self.assertFalse(sg.lex_scope("reports/r.md", []))
        self.assertFalse(sg.lex_scope("specs/other.yaml", ["names:"]))

    def test_v12_reports_heuristic_only(self):
        with tempfile.TemporaryDirectory() as d:
            r = os.path.join(d, "r.md")
            open(r, "w", encoding="utf8").write("- B：未收錄節名｜目的\n- B：須由品保人員覆核後始得放行\n")
            p = subprocess.run([sys.executable, SCRIPT, r], capture_output=True, text=True)
            self.assertEqual(p.returncode, 1)
            self.assertIn("PREFIX", p.stdout)
            self.assertNotIn("LEX", p.stdout)                     # 報告不走詞彙表層


if __name__ == "__main__":
    unittest.main()
