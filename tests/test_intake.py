#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""資料表／指引句／條號表 schema 驗證器測試（M1.1 B2／B3）— 零依賴；合成資料。"""
import copy, importlib.util, json, os, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
_spec = importlib.util.spec_from_file_location("iv", os.path.join(REPO, "scripts", "nk1-intake-validate.py"))
iv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(iv)
SPEC = iv.fy.load(os.path.join(REPO, "specs", "intake_v0.yaml"))
DATA = json.load(open(os.path.join(REPO, "fixtures", "intake_synth_v0.json"), encoding="utf8"))


class TestIntake(unittest.TestCase):
    def test_spec_ok_18_fields(self):
        self.assertEqual(iv.check_spec(SPEC), [])
        self.assertEqual(len(SPEC["fields"]), 18)

    def test_synth_instance_ok(self):
        self.assertEqual(iv.check_data(SPEC, DATA), [])

    def test_bad_instance_caught(self):
        d = copy.deepcopy(DATA)
        del d["model"]
        d["planned_date"] = "2026/10/15"
        d["rated_params"] = d["rated_params"] * 2                 # 8 組 >6
        d["acceptance_items"][0].pop("method")
        errs = iv.check_data(SPEC, d)
        self.assertEqual(len(errs), 4, errs)

    def test_guides_ok(self):
        g = iv.fy.load(os.path.join(REPO, "specs", "guides", "T027_v0.yaml"))
        self.assertEqual(iv.check_guides(g, 37), [])
        g["guides"] = g["guides"][:-1]
        self.assertTrue(iv.check_guides(g, 37))

    def test_refs_ok(self):
        r = iv.fy.load(os.path.join(REPO, "specs", "refs", "annex15_v0.yaml"))
        self.assertEqual(iv.check_refs(r), [])
        self.assertGreaterEqual(len(r["refs"]), 30)



SPEC5 = iv.fy.load(os.path.join(REPO, "specs", "intake_v0.5.yaml"))
DATA5 = json.load(open(os.path.join(REPO, "fixtures", "intake_synth_v0.5.json"), encoding="utf8"))


class TestIntakeV05(unittest.TestCase):
    """M4.3 A：驗收項目拆 accept_iq／oq／pq（各 1–5 項 {item, criterion}，皆必填）。"""

    def test_spec_20_fields_ok(self):
        self.assertEqual(iv.check_spec(SPEC5), [])
        self.assertEqual(len(SPEC5["fields"]), 20)

    def test_synth_v05_ok(self):
        self.assertEqual(iv.check_data(SPEC5, DATA5), [])
        self.assertEqual([len(DATA5[k]) for k in iv.SEGMENT_FIELDS], [3, 3, 3])

    def test_missing_any_segment_rejected(self):
        for k in iv.SEGMENT_FIELDS:
            d = copy.deepcopy(DATA5)
            del d[k]
            self.assertTrue(any(k in e for e in iv.check_data(SPEC5, d)), k)
            d[k] = []
            self.assertTrue(any(k in e for e in iv.check_data(SPEC5, d)), k)

    def test_segment_item_shape_and_max(self):
        d = copy.deepcopy(DATA5)
        d["accept_pq"] = d["accept_pq"] * 2                     # 6 項 >5
        d["accept_iq"][0].pop("criterion")
        self.assertEqual(len(iv.check_data(SPEC5, d)), 2)

    def test_spec_missing_segment_field_rejected(self):
        sp = copy.deepcopy(SPEC5)
        sp["fields"] = [f for f in sp["fields"] if f["key"] != "accept_oq"]
        self.assertTrue(any("accept_oq" in e for e in iv.check_spec(sp)))



class TestGuidesV05(unittest.TestCase):
    G = iv.fy.load(os.path.join(REPO, "specs", "guides", "T027_v0.5.yaml"))

    def test_ok(self):
        self.assertEqual(iv.check_guides_v05(self.G), [])
        self.assertEqual(len(self.G["segment_guides"]), 27)          # 3 段 ×（_head＋_test＋7 項）

    def test_missing_item_and_result_names_caught(self):
        g = copy.deepcopy(self.G)
        g["segment_guides"] = [x for x in g["segment_guides"] if not (x["segment"] == "oq" and x["item"] == "超標處理")]
        for x in g["common"]:
            if x["order"] == 34:
                x["guide"] = "本節說明結果。"
        e = iv.check_guides_v05(g)
        self.assertTrue(any("oq" in x for x in e) and any("驗證結果" in x for x in e), e)



SPEC6 = iv.fy.load(os.path.join(REPO, "specs", "intake_v0.6.yaml"))
DATA6 = json.load(open(os.path.join(REPO, "fixtures", "intake_synth_v0.6.json"), encoding="utf8"))


class TestIntakeV06(unittest.TestCase):
    """M5.0 B：日期拆三欄（可空）、偏差處理 SOP 必填、每段方法步驟欄組（pq 另含負載定義）、uses 標籤。"""

    def test_spec_and_data_ok(self):
        self.assertEqual(iv.check_spec(SPEC6), [])
        self.assertEqual(len(SPEC6["fields"]), 26)
        self.assertEqual(iv.check_data(SPEC6, DATA6), [])

    def test_planned_date_mapped_to_execution_deadline(self):
        self.assertNotIn("planned_date", DATA6)
        self.assertEqual(DATA6["execution_deadline"], "2026-10-15")

    def test_dates_optional(self):
        d = copy.deepcopy(DATA6)
        for k in ("plan_approval_date", "execution_deadline", "go_live_date"):
            d[k] = ""
        self.assertEqual(iv.check_data(SPEC6, d), [])
        d["go_live_date"] = "2026/11/02"
        self.assertEqual(len(iv.check_data(SPEC6, d)), 1)

    def test_deviation_sop_and_methods_required(self):
        d = copy.deepcopy(DATA6)
        del d["deviation_sop"]
        d["method_pq"].pop("load_definition")
        d["method_iq"].pop("runs")
        e = iv.check_data(SPEC6, d)
        self.assertEqual(len(e), 3, e)

    def test_uses_required_in_spec(self):
        sp = copy.deepcopy(SPEC6)
        sp["fields"][0]["uses"] = []
        self.assertTrue(any("uses" in x for x in iv.check_spec(sp)))


if __name__ == "__main__":
    unittest.main()
