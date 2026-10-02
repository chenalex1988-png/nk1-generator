#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""骨架抽取器測試 — 零依賴（unittest），fixture 為合成 docx（tests/_synth_docx.py，stdlib 直寫）。

工單驗收：12 節、3 張表、repeat count 3（夜跑二）；
M1 B 段：全表格文件 → 3 節；head 可變 repeat ×3 → count 3，渲染標籤為三個 head。
測試一律注入合成詞彙表（SYN_LEX），不依賴 repo 內真詞彙表的內容。
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import _synth_docx  # noqa: E402

SCRIPT = os.path.join(REPO, "scripts", "nk1-skel.py")
FIXTURE_NAMES = ["目的", "範圍", "權責", "器具材料", "方法步驟", "允收標準", "結論", "子項測試"]
SYN_LEX = FIXTURE_NAMES + _synth_docx.TABLE_ONLY_LABELS + _synth_docx.HEADS
_sgspec = importlib.util.spec_from_file_location("sentence_gate", os.path.join(REPO, "scripts", "sentence-gate.py"))
sg = importlib.util.module_from_spec(_sgspec)
_sgspec.loader.exec_module(sg)
GATE = sg.Gate(sg.load_rules(sg.DEFAULT_RULES), set(SYN_LEX))
VENV_PY = os.path.join(REPO, ".venv", "bin", "python")


def _lex_file(d):
    p = os.path.join(d, "lex.yaml")
    open(p, "w", encoding="utf8").write("names:\n" + "".join(f'  - "{n}"\n' for n in SYN_LEX))
    return p
_spec = importlib.util.spec_from_file_location("nk1_skel", SCRIPT)
sk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sk)


class TestSkel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.fx = os.path.join(cls.tmp.name, "fixture.docx")
        _synth_docx.skel_fixture(cls.fx)
        cls.d = sk.extract(cls.fx, "fixture", GATE)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_sections_12(self):
        self.assertEqual(self.d["stats"]["sections"], 12)

    def test_tables_3(self):
        self.assertEqual(self.d["stats"]["tables"], 3)

    def test_repeat_count_3(self):
        self.assertEqual(len(self.d["repeats"]), 1)
        self.assertEqual(self.d["repeats"][0]["count"], 3)
        self.assertEqual(self.d["repeats"][0]["block"], ["器具材料", "方法步驟", "允收標準"])
        self.assertEqual(self.d["folded"], ["目的", "範圍", "權責", {"repeat": 1, "count": 3}])

    def test_table_cells_are_not_sections(self):
        names = [s["name"] for s in self.d["sections"]]
        for cell in ("甲", "丁", "庚"):                # 表內「1. 甲」「一、丁」「(1) 庚」不得成節
            self.assertNotIn(cell, names)

    def test_table_meta(self):
        t = self.d["sections"][2]["tables"][0]           # 權責下的表
        self.assertEqual((t["rows"], t["cols"], t["header"]), (4, 3, True))
        self.assertFalse(self.d["sections"][-1]["tables"][0]["header"])

    def test_levels_and_order(self):
        self.assertEqual([s["level"] for s in self.d["sections"][:4]], [1, 1, 1, 2])
        self.assertEqual([s["order"] for s in self.d["sections"]], list(range(1, 13)))

    def test_rejected_name_placeholder(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "rej.docx")
            _synth_docx.build(p, [("h", 1, "目的"), ("h", 1, "須由品保人員覆核後始得放行"), ("h", 1, "範圍")])
            r = sk.extract(p, "x", GATE)
            self.assertEqual(r["stats"]["rejected"], 1)
            self.assertEqual([s["name"] for s in r["sections"]], ["目的", "[REJ-1]", "範圍"])
            self.assertNotIn("品保", sk.to_yaml(r))

    def test_cli_deterministic_and_gate_clean(self):
        outs = []
        for _ in range(2):
            r = subprocess.run([sys.executable, SCRIPT, self.fx, "--doc-type", "fixture", "--lexicon", _lex_file(self.tmp.name)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            outs.append(r.stdout)
        self.assertEqual(outs[0], outs[1])
        with tempfile.TemporaryDirectory() as d:
            y = os.path.join(d, "s.yaml")
            open(y, "w", encoding="utf8").write(outs[0])
            lex = _lex_file(d)                                # 合成詞彙表（v1.1 閘含詞彙表層）
            g = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "sentence-gate.py"), "--lexicon", lex, y],
                               capture_output=True, text=True)
            self.assertEqual(g.returncode, 0, g.stdout)



class TestSkelV11(unittest.TestCase):
    """M1 B 段：節判定收緊、規則 3（表格合併標籤）、head 可變 repeat。"""

    def test_plain_numbering_ignored_when_headings_exist(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.docx")
            _synth_docx.build(p, [("h", 1, "目的"), ("p", "1. 範圍"), ("p", "一、權責"), ("h", 1, "結論")])
            self.assertEqual([s["name"] for s in sk.extract(p, "x", GATE)["sections"]], ["目的", "結論"])

    def test_plain_numbering_fallback_first_level_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "b.docx")
            _synth_docx.build(p, [("p", "1. 目的"), ("p", "1.1 器具材料"), ("p", "(1) 允收標準"), ("p", "二、範圍")])
            r = sk.extract(p, "x", GATE)
            self.assertEqual([(s["level"], s["name"]) for s in r["sections"]], [(1, "目的"), (1, "範圍")])

    def test_rule4_numbered_in_lexicon_is_section(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "n.docx")
            _synth_docx.build(p, [("h", 1, "目的"), ("np", 3, "器具材料"), ("np", 3, "未收錄項目"), ("np", 0, "允收標準")])
            r = sk.extract(p, "x", GATE)
            self.assertEqual([(s["level"], s["name"]) for s in r["sections"]], [(1, "目的"), (4, "器具材料"), (1, "允收標準")])

    def test_table_only_doc_3_sections(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.docx")
            _synth_docx.table_only_fixture(p)
            r = sk.extract(p, "x", GATE)
            self.assertEqual(r["stats"]["sections"], 3)
            self.assertEqual(r["stats"]["tables"], 3)
            self.assertEqual([s["name"] for s in r["sections"]], _synth_docx.TABLE_ONLY_LABELS)
            self.assertTrue(all(len(s["tables"]) == 1 for s in r["sections"]))
            self.assertEqual(r["tables_before_first_section"], [])

    def test_merged_label_must_pass_lexicon(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "u.docx")
            _synth_docx.build(p, [("mtbl", "未收錄標籤", 2, 3), ("mtbl", "政策", 2, 3)])
            r = sk.extract(p, "x", GATE)
            self.assertEqual([s["name"] for s in r["sections"]], ["政策"])
            self.assertEqual(len(r["tables_before_first_section"]), 1)

    def test_head_repeat_x3(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "h.docx")
            _synth_docx.head_repeat_fixture(p)
            r = sk.extract(p, "x", GATE)
            self.assertEqual(len(r["repeats"]), 1)
            rp = r["repeats"][0]
            self.assertEqual(rp["count"], 3)
            self.assertEqual(rp["head"], _synth_docx.HEADS)
            self.assertEqual(rp["block"], ["器具材料", "允收標準"])
            self.assertEqual(r["folded"], ["目的", {"repeat": 1, "count": 3}, "結論"])
            self.assertIn('head: ["甲類驗證", "乙類驗證", "丙類驗證"]', sk.to_yaml(r))

    def test_head_repeat_block_len_1(self):
        seq = ["驗證", "甲類驗證", "子項測試", "乙類驗證", "子項測試", "丙類驗證", "子項測試", "結論"]
        lv = [1, 2, 3, 2, 3, 2, 3, 1]
        self.assertEqual(sk.find_repeats(seq, levels=lv), [(["子項測試"], [2, 4, 6], True)])

    def test_head_must_be_shallower_than_block(self):
        seq = ["甲類驗證", "子項測試", "乙類驗證", "子項測試"]
        self.assertEqual(sk.find_repeats(seq, levels=[2, 2, 2, 2]), [])

    @unittest.skipUnless(os.path.exists(VENV_PY), "無 .venv（docxtpl）")
    def test_head_repeat_render_labels(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            p, y = os.path.join(d, "h.docx"), os.path.join(d, "h.yaml")
            _synth_docx.head_repeat_fixture(p)
            open(y, "w", encoding="utf8").write(sk.to_yaml(sk.extract(p, "x", GATE)))
            t, o = os.path.join(d, "t.docx"), os.path.join(d, "o.docx")
            r = subprocess.run([VENV_PY, os.path.join(REPO, "scripts", "nk1-skel2docx.py"), y, "--template-out", t, "--out", o],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            xml = zipfile.ZipFile(o).read("word/document.xml").decode("utf8")
            pos = [xml.find(h) for h in _synth_docx.HEADS]
            self.assertTrue(all(x > 0 for x in pos), pos)
            self.assertEqual(pos, sorted(pos))
            self.assertEqual(xml.count("器具材料"), 3)
            self.assertNotIn("RUN-", xml)



class TestRenderDeterminism(unittest.TestCase):
    """M1 D 段：同 YAML 同假值渲染兩次 → sha256 相同；zip entry mtime 固定 1980-01-01、依名稱排序。"""

    @unittest.skipUnless(os.path.exists(VENV_PY), "無 .venv（docxtpl）")
    def test_same_yaml_same_sha(self):
        import hashlib, time, zipfile
        y = os.path.join(REPO, "fixtures", "skel_synth_example.yaml")
        shas = []
        with tempfile.TemporaryDirectory() as d:
            for i in range(2):
                if i:
                    time.sleep(2.1)                        # 跨過 zip 的 2 秒時間解析度，未固定 mtime 就會露餡
                t, o = os.path.join(d, f"t{i}.docx"), os.path.join(d, f"o{i}.docx")
                r = subprocess.run([VENV_PY, os.path.join(REPO, "scripts", "nk1-skel2docx.py"), y,
                                    "--template-out", t, "--out", o], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                shas.append(tuple(hashlib.sha256(open(x, "rb").read()).hexdigest() for x in (t, o)))
                with zipfile.ZipFile(o) as z:
                    infos = z.infolist()
                    self.assertTrue(all(zi.date_time == (1980, 1, 1, 0, 0, 0) for zi in infos))
                    self.assertEqual([zi.filename for zi in infos], sorted(zi.filename for zi in infos))
        self.assertEqual(shas[0], shas[1])



class TestSkelV13(unittest.TestCase):
    """M4.3 B：標題不過詞彙表閘；REJ → CLI 失敗不出檔；overlay 帶 segment／t0。"""

    def test_titles_skip_lexicon(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.docx")
            _synth_docx.build(p, [("h", 1, "未收錄標題"), ("h", 1, "目的")])
            r = sk.extract(p, "x", GATE)
            self.assertEqual([s["name"] for s in r["sections"]], ["未收錄標題", "目的"])
            self.assertEqual(r["stats"]["rejected"], 0)

    def test_bilingual_len_counted_separately(self):
        self.assertEqual(sg.Gate(sg.load_rules(sg.DEFAULT_RULES)).heuristic("目的及說明Purpose and Description"), [])
        self.assertIn("LEN", sg.Gate(sg.load_rules(sg.DEFAULT_RULES)).heuristic("目的" + "purpose and scope of this plan x"))

    def test_rej_cli_fails_without_output(self):
        with tempfile.TemporaryDirectory() as d:
            p, out = os.path.join(d, "r.docx"), os.path.join(d, "o.yaml")
            _synth_docx.build(p, [("h", 1, "目的"), ("h", 1, "須由品保人員覆核後始得放行")])
            r = subprocess.run([sys.executable, SCRIPT, p, "--out", out, "--lexicon", _lex_file(d)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 3)
            self.assertFalse(os.path.exists(out))

    def test_overlay_segments(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "h.docx")
            _synth_docx.head_repeat_fixture(p)
            r = sk.extract(p, "x", GATE)
            ov = {"doc_type": "x", "version": "0.5", "segments": [
                {"head": h, "segment": sgm, "block0_title": h + "測試"} for h, sgm in zip(_synth_docx.HEADS, ("iq", "oq", "pq"))]}
            r = sk.apply_overlay(r, ov)
            rp = r["repeats"][0]
            self.assertEqual(rp["segments"], ["iq", "oq", "pq"])
            self.assertEqual(rp["t0"], [h + "測試" for h in _synth_docx.HEADS])
            self.assertEqual(rp["block"][0], "@t0")
            self.assertEqual({s.get("segment") for s in r["sections"] if s["order"] in (2, 3, 4)}, {"iq"})
            self.assertIn('segments: ["iq", "oq", "pq"]', sk.to_yaml(r))

    def test_overlay_head_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "h.docx")
            _synth_docx.head_repeat_fixture(p)
            r = sk.extract(p, "x", GATE)
            with self.assertRaises(ValueError):
                sk.apply_overlay(r, {"segments": [{"head": "不存在", "segment": "iq", "block0_title": "x"}]})


if __name__ == "__main__":
    unittest.main()
