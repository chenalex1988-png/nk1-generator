#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""條號範圍展開器測試（M4.4 A）— 零依賴；合成字串。"""
import importlib.util, os, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_sp = importlib.util.spec_from_file_location("nk1_expand", os.path.join(REPO, "scripts", "nk1-expand.py"))
ex = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(ex)
TABLE = [f"3.{k}" for k in range(1, 15)] + [f"8.{k}" for k in range(1, 4)] + [f"11.{k}" for k in range(1, 8)]


class TestExpand(unittest.TestCase):
    def test_all_forms_expand(self):
        for sep in (" 至 ", "–", "~", "-", "到"):
            t, n = ex.expand_ranges("S03", f"依 Annex 15 3.2{sep}3.4 辦理。", TABLE)
            self.assertEqual(t, "依 Annex 15 3.2、3.3、3.4 辦理。", sep)
            self.assertEqual(n[0]["table_check"], "all_present")
            self.assertEqual(n[0]["expanded"], ["3.2", "3.3", "3.4"])

    def test_two_digit_and_other_text_untouched(self):
        t, n = ex.expand_ranges("S36", "見 11.1 至 11.7；溫度 36 ℃ 至 38 ℃；日期 2026-10-15。", TABLE)
        self.assertEqual(t, "見 11.1、11.2、11.3、11.4、11.5、11.6、11.7；溫度 36 ℃ 至 38 ℃；日期 2026-10-15。")
        self.assertEqual(len(n), 1)

    def test_missing_in_table_not_expanded(self):
        t, n = ex.expand_ranges("S05", "依 3.12 至 3.16 辦理。", TABLE)
        self.assertEqual(t, "依 3.12 至 3.16 辦理。")
        self.assertEqual((n[0]["table_check"], n[0]["action"]), ("missing:[3.15,3.16]", "regen"))

    def test_cross_chapter_not_expanded(self):
        t, n = ex.expand_ranges("S05", "依 3.13 至 8.2 辦理。", TABLE)
        self.assertEqual(t, "依 3.13 至 8.2 辦理。")
        self.assertEqual(n[0]["action"], "regen")

    def test_no_range_no_record(self):
        t, n = ex.expand_ranges("S01", "依 3.9、3.10 逐條辦理。", TABLE)
        self.assertEqual((t, n), ("依 3.9、3.10 逐條辦理。", []))


if __name__ == "__main__":
    unittest.main()
