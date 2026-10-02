#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nk1-gen.py 閘門測試（M4.1 A）— 零依賴；合成值。SOP 編號誤入 refs → 攔下；正確放 sop_refs → 過。"""
import importlib.util, json, os, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
_sp = importlib.util.spec_from_file_location("nk1_gen", os.path.join(REPO, "scripts", "nk1-gen.py"))
g = importlib.util.module_from_spec(_sp)                 # 無 docxtpl 也可載（render 內才 import）
_sp.loader.exec_module(g)

REFS = [{"law": "PIC/S GMP Annex 15", "clause": c} for c in ("3.9", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.8")]
INTAKE = {"sop_ids": ["SOP-SYN-101", "SOP-SYN-102"], "model": "ZQ-950"}
ALLOW = g.build_allow(INTAKE, REFS)
LAW = {g.cs._ns(r["law"] + r["clause"]) for r in REFS}
SOP = {g.cs._ns(x) for x in INTAKE["sop_ids"]}
BODY = "依 PIC/S GMP Annex 15 3.9 執行，並依 SOP-SYN-101 操作。"


def raw(refs, sops=None):
    d = {"section_id": "S01", "body": BODY, "refs": refs}
    if sops is not None:
        d["sop_refs"] = sops
    return json.dumps(d, ensure_ascii=False)


class TestGate(unittest.TestCase):
    def test_sop_in_refs_blocked(self):
        r = g.gate_section(raw([REFS[0], {"law": "SOP-SYN-101", "clause": ""}], []), ALLOW, LAW, SOP)
        self.assertFalse(r["passed"])
        self.assertEqual((r["refs_in"], r["refs_n"]), (1, 2))

    def test_sop_in_sop_refs_passes(self):
        r = g.gate_section(raw([REFS[0]], ["SOP-SYN-101"]), ALLOW, LAW, SOP)
        self.assertTrue(r["passed"], r)
        self.assertEqual((r["sop_in"], r["sop_n"]), (1, 1))

    def test_unknown_sop_blocked(self):
        r = g.gate_section(raw([REFS[0]], ["SOP-SYN-999"]), ALLOW, LAW, SOP)
        self.assertFalse(r["passed"])

    def test_empty_clause_blocked(self):
        r = g.gate_section(raw([{"law": "PIC/S GMP Annex 15", "clause": ""}], []), ALLOW, LAW, SOP)
        self.assertFalse(r["passed"])

    def test_schema_requires_sop_refs_and_nonempty_clause(self):
        self.assertIn("sop_refs", g.SCHEMA["required"])
        self.assertEqual(g.SCHEMA["properties"]["refs"]["items"]["properties"]["clause"]["minLength"], 1)


    def test_refs_7_rejected_by_schema(self):
        """M4.2 A：refs 7 條 → schema 拒（即使 7 條皆在條號表內）。"""
        r = g.gate_section(raw(REFS[:7], []), ALLOW, LAW, SOP)
        self.assertEqual(r["refs_in"], 7)
        self.assertGreater(r["schema_errors"], 0)
        self.assertFalse(r["passed"])

    def test_refs_6_passes(self):
        r = g.gate_section(raw(REFS[:6], []), ALLOW, LAW, SOP)
        self.assertEqual(r["schema_errors"], 0)
        self.assertTrue(r["passed"], r)

    def test_sop_refs_7_rejected(self):
        r = g.gate_section(raw([REFS[0]], ["SOP-SYN-101"] * 7), ALLOW, LAW, SOP)
        self.assertFalse(r["passed"])

    def test_schema_declares_max_items(self):
        p = g.SCHEMA["properties"]
        self.assertEqual((p["refs"]["maxItems"], p["sop_refs"]["maxItems"]), (6, 6))



SKEL = {"sections": [{"order": o, "name": n, "level": 1} for o, n in enumerate(
            ["目的", "安裝驗證", "安裝驗證測試", "器具材料", "操作驗證", "操作驗證測試", "器具材料", "驗證結果"], 1)],
        "repeats": [{"head": ["安裝驗證", "操作驗證"], "segments": ["iq", "oq"], "t0": ["安裝驗證測試", "操作驗證測試"],
                     "block": ["@t0", "器具材料"], "count": 2, "starts": [3, 6]}]}
INTAKE5 = {"equipment_name": "合成設備", "remarks": "不得餵", "accept_iq": [{"item": "a", "criterion": "b"}],
           "accept_oq": [{"item": "c", "criterion": "d"}], "accept_pq": [{"item": "e", "criterion": "f"}]}


class TestFeedingV04(unittest.TestCase):
    """M4.3 D：各段只餵共同欄＋該段 accept；驗證結果節三段皆可見；指引句依段別索引。"""

    def test_roles(self):
        r = g.section_roles(SKEL)
        self.assertEqual(r[2], ("iq", "_head"))
        self.assertEqual(r[3], ("iq", "_test"))
        self.assertEqual(r[4], ("iq", "器具材料"))
        self.assertEqual(r[7], ("oq", "器具材料"))
        self.assertNotIn(1, r)
        self.assertEqual(g.result_order(SKEL), 8)

    def test_intake_view_segment_only(self):
        v = g.intake_view(INTAKE5, "iq")
        self.assertIn("accept_iq", v)
        self.assertNotIn("accept_oq", v)
        self.assertNotIn("accept_pq", v)
        self.assertNotIn("remarks", v)
        self.assertEqual(set(g.intake_view(INTAKE5, None, True)) & {"accept_iq", "accept_oq", "accept_pq"},
                         {"accept_iq", "accept_oq", "accept_pq"})
        self.assertEqual(set(g.intake_view(INTAKE5, None)) & {"accept_iq", "accept_oq", "accept_pq"}, set())

    def test_guide_for_v05(self):
        gd = g.fy.load(os.path.join(REPO, "specs", "guides", "T027_v0.5.yaml"))
        a, b = g.guide_for(gd, 9, ("iq", "器具材料")), g.guide_for(gd, 18, ("oq", "器具材料"))
        self.assertNotEqual(a, b)
        self.assertIn("安裝驗證", a)
        self.assertIn("逐段", g.guide_for(gd, 34, None))

    def test_prompt_forbids_ranges(self):
        self.assertIn("不得寫「X 至 Y」範圍", g.SYSTEM)



D5 = json.load(open(os.path.join(REPO, "fixtures", "intake_synth_v0.5.json"), encoding="utf8"))


class TestGatesV05(unittest.TestCase):
    """M4.3 E：分段允收／中文數字／簡體／範圍，攔下原因歸因正確；Jaccard。"""

    def setUp(self):
        self.ex = g.seg_exclusive(D5)
        self.allow_iq = g.build_allow(g.intake_view(D5, "iq"), REFS)

    def gate(self, body, allow=None, excl="iq"):
        return g.gate_section(json.dumps({"section_id": "S09", "body": body, "refs": [], "sop_refs": []}, ensure_ascii=False),
                              allow or self.allow_iq, LAW, SOP, self.ex.get(excl) if excl else None)

    def test_exclusive_sets(self):
        self.assertIn("72h", self.ex["iq"])                 # PQ 專屬
        self.assertIn("30min", self.ex["iq"])               # OQ 專屬
        self.assertNotIn("220V", self.ex["iq"])             # 共同欄（公用系統－電）
        self.assertNotIn("72h", self.ex["pq"])

    def test_iq_hits_pq_value_blocked(self):
        r = self.gate("安裝驗證期間需連續運轉 72 h。")
        self.assertFalse(r["passed"])
        self.assertIn("分段允收", r["reasons"])
        self.assertEqual(r["excl_hits"], 1)
        self.assertNotIn("封閉集合", r["reasons"])

    def test_iq_own_values_pass(self):
        r = self.gate("核對型號 ZQ-950 與資產編號 SYN-EQ9-017，電源為 220 V。")
        self.assertTrue(r["passed"], r)

    def test_cn_numeral_simplified_range(self):
        self.assertEqual(self.gate("本節另做三項核對。")["reasons"], ["中文數字"])
        self.assertEqual(self.gate("本节核对型号。")["reasons"], ["簡體"])
        self.assertEqual(self.gate("依 PIC/S GMP Annex 15 3.9 至 3.9 辦理。")["reasons"], ["範圍"])

    def test_cn_numeral_traceable_passes_in_oq(self):
        allow = g.build_allow(g.intake_view(D5, "oq"), REFS)
        self.assertTrue(self.gate("溫度均勻性以九點量測。", allow, "oq")["passed"])

    def test_jaccard(self):
        self.assertEqual(g.jaccard3("本節說明核對項目", "本節說明核對項目"), 1.0)
        self.assertLess(g.jaccard3("本節說明安裝核對項目", "本節說明操作測試條件"), 0.9)



class TestExpandInGate(unittest.TestCase):
    """M4.4：展開在範圍閘之前；展開後照常過閘；展不開則仍被範圍閘攔（交給重生）。"""
    TABLE = [r["clause"] for r in REFS]                                  # 3.2–3.9

    def run_gate(self, body):
        raw = json.dumps({"section_id": "S03", "body": body, "refs": [], "sop_refs": []}, ensure_ascii=False)
        rx, norms, found = g.expand_raw("S03", raw, self.TABLE)
        return g.gate_section(rx, ALLOW, LAW, SOP), norms, found, json.loads(rx)["body"]

    def test_expandable_range_passes(self):
        r, n, f, b = self.run_gate("依 PIC/S GMP Annex 15 3.2 至 3.4 辦理。")
        self.assertTrue(r["passed"], r)
        self.assertEqual((f, n[0]["table_check"]), (1, "all_present"))
        self.assertIn("3.2、3.3、3.4", b)

    def test_unexpandable_range_still_blocked(self):
        r, n, f, b = self.run_gate("依 PIC/S GMP Annex 15 3.8 至 3.11 辦理。")      # 3.10、3.11 不在表
        self.assertIn("範圍", r["reasons"])
        self.assertEqual(n[0]["action"], "regen")

    def test_expanded_still_scanned(self):
        r, n, f, b = self.run_gate("依 PIC/S GMP Annex 15 3.2 至 3.4 辦理，溫度 99 ℃。")   # 展開成功但 99 ℃ 不在 allow
        self.assertIn("封閉集合", r["reasons"])



class TestCnEquivInGate(unittest.TestCase):
    def test_gate_passes_and_records_equiv(self):
        d6 = json.load(open(os.path.join(REPO, "fixtures", "intake_synth_v0.6.json"), encoding="utf8"))
        raw = json.dumps({"section_id": "S18", "body": "每 1 min 記錄，共執行三次。", "refs": [], "sop_refs": []}, ensure_ascii=False)
        r = g.gate_section(raw, g.build_allow(d6, REFS), LAW, SOP)
        self.assertTrue(r["passed"], r["reasons"])
        self.assertEqual(r["cn_equiv"], [{"original": "三次", "arabic": "3次"}])

    def test_prompt_has_quantity_rule(self):
        self.assertIn("次數與數量照資料表原樣寫（例：1 次）", g.SYSTEM_V2)


if __name__ == "__main__":
    unittest.main()
