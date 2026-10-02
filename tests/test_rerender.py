#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5.4 C 重渲染（引用搬審閱層）測試 — 合成字串。"""
import importlib.util, os, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_sp = importlib.util.spec_from_file_location("rr", os.path.join(REPO, "scripts", "nk1-rerender.py"))
rr = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(rr)
T = {"3.9", "3.10", "11.2"}
V = "PIC/S GMP Annex 15（PE 009-18）"


class TestRerender(unittest.TestCase):
    def test_clean_boundary_removed_and_logged(self):
        nb, n, st = rr.strip_citations("S09", f"本節說明核對工具。依 {V}3.9 之規定。核對型號。", T)
        self.assertEqual(st, "ok")
        self.assertNotIn("Annex", nb)
        self.assertEqual((n[0]["clauses"], n[0]["table_check"]), (["3.9"], "all_in_table"))
        nb, n, st = rr.strip_citations("S16", f"測試完成後記錄，並符合 {V}3.10 之要求。", T)
        self.assertEqual((st, nb), ("ok", "測試完成後記錄。"))

    def test_embedded_not_modified(self):
        b = f"相關作業依據 {V}3.9 執行。"
        nb, n, st = rr.strip_citations("S08", b, T)
        self.assertEqual((st, nb), ("embedded", b))                  # 原文不動
        self.assertEqual(n[0]["action"], "block")

    def test_clause_not_in_table_not_modified(self):
        b = f"依 {V}5.3 之規定。"
        nb, n, st = rr.strip_citations("S05", b, T)
        self.assertEqual((st, nb), ("not_in_table", b))

    def test_translation_copy_detected(self):
        refs = [{"clause": "3.9", "translation_zh": "安裝驗證應包括但不侷限於下列各項：對照工程圖及規格確認組件"}]
        self.assertEqual(rr.copies_translation("本節：安裝驗證應包括但不侷限於下列各項，其餘自擬。", refs), "3.9")
        self.assertIsNone(rr.copies_translation("本節說明安裝驗證核對項目。", refs))


if __name__ == "__main__":
    unittest.main()
