#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""封閉集合掃描器測試 — 零依賴（unittest）；合成值，無任何真實內容。

工單驗收：植入 25 值（每類 5），allow 放 15 → 差集恰 10；allow 全放 → 差集 0。
M1 C 段（v1.1）：兩案不變＋植入 5 個裸 X.Y 節編號 → 差集 0。
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import _synth_docx  # noqa: E402

SCRIPT = os.path.join(REPO, "scripts", "nk1-closedset.py")
_spec = importlib.util.spec_from_file_location("nk1_closedset", SCRIPT)
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)

PLANT = {
    "數值": ["12 mL", "30 min", "25℃", "70%", "150 rpm"],
    "編號": ["AB-CD1-001", "EN-F02-010", "QA-T03-100", "MBQ-A-EQP12", "SOP-QA-7"],
    "日期": ["2025/01/15", "2025-02-20", "15JAN2025", "2024/12/31", "03MAR2026"],
    "法規": ["PIC/S", "Annex 15", "ICH Q9(R1)", "21 CFR Part 11", "ISO 14644"],
    "條號": ["第12條", "§ 211", "Clause 7", "3.2.1", "4.5"],
}
TEXT = "合成段落：" + "，".join(v for vs in PLANT.values() for v in vs) + "，結束。"

ALLOW_15 = {
    "intake": {"數值": ["12 mL", "30 min", "25℃"], "日期": ["2025/01/15", "2025-02-20", "15JAN2025"],
               "編號": ["AB-CD1-001", "EN-F02-010"]},
    "numbering_rules": [r"QA-T\d{2}-\d{3}"],
    "refs": ["PIC/S", "Annex 15", "ICH Q9(R1)", "藥事法第12條", "21 CFR § 211", "ISO Clause 7"],
}
ALLOW_ALL = {
    "intake": {k: PLANT[k] for k in ("數值", "日期", "編號")},
    "refs": PLANT["法規"] + ["藥事法第12條", "21 CFR § 211", "ISO Clause 7", "Annex 15 3.2.1", "ICH 4.5"],
}


class TestClosedSet(unittest.TestCase):
    def test_plant_25_each_category_5(self):
        res, _ = cs.scan(TEXT, {})
        self.assertEqual({k: res[k]["hits"] for k in PLANT}, {k: 5 for k in PLANT})

    def test_allow_15_diff_10(self):
        res, _ = cs.scan(TEXT, ALLOW_15)
        self.assertEqual(sum(v["allowed"] for v in res.values()), 15)
        self.assertEqual(sum(v["diff"] for v in res.values()), 10)
        self.assertEqual({k: res[k]["diff"] for k in PLANT}, {k: 2 for k in PLANT})

    def test_allow_all_diff_0(self):
        res, _ = cs.scan(TEXT, ALLOW_ALL)
        self.assertEqual(sum(v["diff"] for v in res.values()), 0)

    def test_masking_no_raw_values(self):
        res, _ = cs.scan(TEXT, {})
        masked = [m for v in res.values() for m in v["diff_masked"]]
        self.assertIn("N mL", masked)
        self.assertIn("X-X9-999", masked)
        for raw in ("AB-CD1-001", "2025/01/15", "150rpm"):
            self.assertNotIn(raw, masked)

    def test_placeholders_stripped(self):
        res, ph = cs.scan("編號 SOP-XX-001，日期 YYYY/MM/DD，值 ${溫度}", {})
        self.assertEqual(sum(v["hits"] for v in res.values()), 0)
        self.assertGreaterEqual(ph, 2)

    def test_cli_docx_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            doc = os.path.join(d, "x.docx")
            _synth_docx.build(doc, [("h", 1, "目的"), ("p", TEXT)])
            a15, aall = os.path.join(d, "a15.json"), os.path.join(d, "aall.json")
            json.dump(ALLOW_15, open(a15, "w", encoding="utf8"), ensure_ascii=False)
            json.dump(ALLOW_ALL, open(aall, "w", encoding="utf8"), ensure_ascii=False)
            r1 = subprocess.run([sys.executable, SCRIPT, doc, "--allow", a15], capture_output=True, text=True)
            r2 = subprocess.run([sys.executable, SCRIPT, doc, "--allow", aall], capture_output=True, text=True)
            self.assertEqual(r1.returncode, 1)
            self.assertIn("差集合計：10", r1.stdout)
            self.assertNotIn("EN-F02-010", r1.stdout)
            self.assertEqual(r2.returncode, 0)



class TestClosedSetV11(unittest.TestCase):
    def test_bare_section_numbers_diff_0(self):
        text = "3.1 目的\n3.2 範圍\n4.1 程序\n4.2 職責\n5.1 定義\n"
        res, _ = cs.scan(text, {})
        self.assertEqual(res["條號"]["hits"], 0)
        self.assertEqual(sum(v["diff"] for v in res.values()), 0)

    def test_bare_xy_counts_with_regulation_in_sentence(self):
        res, _ = cs.scan("依 Annex 15 3.2 辦理。另見 4.1 節。依第 5 條與 6.2 處理。", {})
        self.assertEqual(res["條號"]["hits"], 2)             # 3.2（同句有法規名）、6.2（同句有「第」）；4.1 不算

    def test_units_seconds_and_case(self):
        res, _ = cs.scan("保持 30 s；保持 45 秒；持續 5 sec；流速 10 mLA。", {})
        self.assertEqual(res["數值"]["hits"], 3)              # 30s、45秒、10mL；5 sec 不算（後接小寫）

    def test_docno_alnum_head_and_span_dedup(self):
        res, _ = cs.scan("編號 EN1-F02-010 與 SOP-QA-7。", {})
        self.assertEqual(res["編號"]["hits"], 2)
        self.assertEqual(cs.find_all("編號", "EN1-F02-010"), ["EN1-F02-010"])



class TestClosedSetV12(unittest.TestCase):
    ALLOW = {"intake": {"數值": ["0.5 ℃", "1.5 L", "2.5 %", "3.5 rpm", "4.5 kPa"]}}

    def test_decimals_with_units_diff_0(self):
        """M1.1 A4：植入 5 個帶單位小數（同句有「第／§」）→ 差集 0。"""
        text = "依第12條與 § 4.2：溫差 ±0.5 ℃、容量 1.5 L、誤差 2.5 %、轉速 3.5 rpm、壓差 4.5 kPa。"
        res, _ = cs.scan(text, dict(self.ALLOW, refs=["合成規範第12條", "合成指引§4.2"]))
        self.assertEqual(res["條號"]["hits"], 2)                 # 只剩 第12條、§4.2
        self.assertEqual(sum(v["diff"] for v in res.values()), 0)

    def test_bare_xy_followed_by_plusminus_excluded(self):
        res, _ = cs.scan("依第3條：設定 37.0±0.5 ℃、37.05 ℃。", {})
        self.assertEqual(res["條號"]["hits"], 1)                 # 第3條

    def test_table_cell_xy_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.docx")
            _synth_docx.build(p, [("p", "依第3條辦理 4.1 節。"), ("tbl", 1, 2, False, [["依第5條", "6.2"]])])
            res, _ = cs.scan(cs.read_text(p), {})
            self.assertEqual(res["條號"]["hits"], 3)             # 本文 第3條＋4.1；儲存格內 第5條 算、6.2 不算



class TestClosedSetV13(unittest.TestCase):
    """M4.3 E：中文數字類、簡體字、條號範圍。"""

    def test_cn_numeral_must_trace_to_intake(self):
        res, _ = cs.scan("採九點量測，另做三項檢查。", {"intake": {"中文數字": ["九點"]}})
        self.assertEqual((res["中文數字"]["hits"], res["中文數字"]["diff"]), (2, 1))   # 九點 可回溯、三項 不可

    def test_cn_numeral_not_triggered_by_plain_words(self):
        res, _ = cs.scan("操作一致性良好，逐一確認。", {})
        self.assertEqual(res["中文數字"]["hits"], 0)

    def test_simplified_hits(self):
        self.assertEqual(cs.simplified_hits("溫度測試"), [])
        self.assertEqual(cs.simplified_hits("温度测试"), ["温", "测", "试"])

    def test_clause_ranges(self):
        self.assertEqual(len(cs.clause_ranges("依 Annex 15 3.2 至 3.7 辦理")), 1)
        self.assertEqual(len(cs.clause_ranges("見 3.9–3.14")), 1)
        self.assertEqual(len(cs.clause_ranges("依第 12 至 15 條")), 1)
        self.assertEqual(cs.clause_ranges("依 3.9、3.10 及 3.11 逐條；溫度 36 ℃ 至 38 ℃；日期 2026-10-15"), [])



class TestCnWhitelist(unittest.TestCase):
    """M4.4 C：固定語白名單。"""

    def test_whitelisted_not_counted(self):
        res, _ = cs.scan("若任一項目未達標，逐一確認，第一次量測須一致。", {})
        self.assertEqual(res["中文數字"]["hits"], 0)
        self.assertGreaterEqual(cs.cn_whitelisted_count("若任一項目未達標，第一次量測。"), 2)

    def test_other_rules_unchanged(self):
        res, _ = cs.scan("另做三項核對、兩次量測。", {})
        self.assertEqual(res["中文數字"]["hits"], 2)

    def test_whitelist_file_has_ten(self):
        self.assertEqual(len(cs.cn_whitelist()), 10)



class TestCnEquivalence(unittest.TestCase):
    """M5.2 b：一～十換算為阿拉伯數字後與 intake 相等即可回溯，並記原寫法。"""
    ALLOW = {"intake": {"數值": ["1 次", "3 次"], "量詞數": ["24 瓶", "9 點"]}}

    def test_equivalent_counts_as_traceable_and_recorded(self):
        res, _ = cs.scan("量測一次，重複三次。", self.ALLOW)
        self.assertEqual((res["中文數字"]["hits"], res["中文數字"]["diff"]), (2, 0))
        self.assertEqual({e["original"]: e["arabic"] for e in res["中文數字"]["equiv"]}, {"一次": "1次", "三次": "3次"})

    def test_non_equal_or_out_of_range_still_blocked(self):
        res, _ = cs.scan("量測兩次，重複五次，共十二次。", self.ALLOW)
        self.assertEqual(res["中文數字"]["diff"], 3)                  # 兩（非一～十）、五次（intake 無）、十二次（多字不換算）
        self.assertEqual(res["中文數字"]["equiv"], [])

    def test_converter(self):
        self.assertEqual(cs.cn_to_arabic("九點"), "9點")
        self.assertEqual(cs.cn_to_arabic("十項"), "10項")
        self.assertIsNone(cs.cn_to_arabic("兩次"))
        self.assertIsNone(cs.cn_to_arabic("十二次"))


if __name__ == "__main__":
    unittest.main()
