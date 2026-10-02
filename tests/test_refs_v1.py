#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""條號表 v1 產生器與檔案測試（M5.0 A）— 零依賴。"""
import importlib.util, json, os, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_sp = importlib.util.spec_from_file_location("rv1", os.path.join(REPO, "scripts", "nk1-refs-v1.py"))
rv = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(rv)
_sp2 = importlib.util.spec_from_file_location("iv", os.path.join(REPO, "scripts", "nk1-intake-validate.py"))
iv = importlib.util.module_from_spec(_sp2)
_sp2.loader.exec_module(iv)
V1 = json.load(open(os.path.join(REPO, "specs", "refs", "annex15_v1.json"), encoding="utf8"))


class TestRefsV1(unittest.TestCase):
    def test_split_mixed(self):
        self.assertEqual(rv.split_mixed("vi. 引述現有文件； vi. References to existing documents;"),
                         [("zh", "vi. 引述現有文件；"), ("en", "vi. References to existing documents;")])
        self.assertEqual(rv.split_mixed("純中文一行。"), [("zh", "純中文一行。")])

    def test_compare_marker_and_order(self):
        pw = rv._words("i. Alpha beta gamma. ii. Delta epsilon.")
        self.assertEqual(rv.compare(pw, "Alpha beta gamma. Delta epsilon.")[0], "identical")
        self.assertEqual(rv.compare(pw, "Alpha beta zeta.")[0], "diff")

    def test_expand_rules(self):
        m = rv.expand_rules([{"from": "3.8", "to": "3.10", "doc_types": ["X"], "sections": ["iq"]},
                             {"from": "3.10", "to": "3.10", "doc_types": ["Y"], "sections": []}], ["3.8", "3.9", "3.10", "3.11"])
        self.assertEqual(m["3.10"], {"doc_types": ["X", "Y"], "sections": ["iq"]})
        self.assertNotIn("3.11", m)

    def test_v1_file(self):
        self.assertEqual(len(V1["refs"]), 44)
        self.assertEqual(V1["correspondence"]["number_one_to_one"], 44)
        self.assertEqual(V1["correspondence"]["pe009_14_vs_18"]["diff"], 0)
        self.assertEqual(len(V1["not_included"]), 6)
        self.assertTrue(all(r["version"] == "PE 009-18" for r in V1["refs"]))
        self.assertEqual(iv.check_refs_v1(V1), [])


if __name__ == "__main__":
    unittest.main()
