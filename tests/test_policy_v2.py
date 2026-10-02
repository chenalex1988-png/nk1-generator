#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5.0 C 品保六項退件理由閘測試（9～13 各 ≥2 例）— 合成字串；不需模型。"""
import importlib.util, json, os, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_sp = importlib.util.spec_from_file_location("nk1_gen", os.path.join(REPO, "scripts", "nk1-gen.py"))
g = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(g)
INTAKE = json.load(open(os.path.join(REPO, "fixtures", "intake_synth_v0.6.json"), encoding="utf8"))
SPEC = g.fy.load(os.path.join(REPO, "specs", "intake_v0.6.yaml"))
SU = g.fy.load(os.path.join(REPO, "specs", "guards", "section_uses_T027.yaml"))
REFS1 = g.load_refs(os.path.join(REPO, "specs", "refs", "annex15_v1.json"))
BASE = g.policy_base(INTAKE, SPEC, SU, REFS1)
V = "PIC/S GMP Annex 15（PE 009-18）"


def ctx(order, name, role=None):
    return g.policy_ctx(BASE, {"order": order, "name": name}, role)


def run(body, c, refs=()):
    return g.policy_checks(body, list(refs), c)


class TestResultBan(unittest.TestCase):                                   # C-9
    def test_blocks_verdict_terms_in_result_sections(self):
        r, d = run("溫度各點均在設定值 1 ℃ 以內，判定合格。", ctx(13, "測試結果", ("iq", "測試結果")))
        self.assertIn("結果禁令", r)
        r, _ = run("三段皆已符合允收標準。", ctx(34, "驗證結果"))
        self.assertIn("結果禁令", r)

    def test_placeholder_only_passes_and_other_sections_exempt(self):
        r, _ = run("（待填）結果記錄於下表。", ctx(14, "結果判定", ("iq", "結果判定")))
        self.assertNotIn("結果禁令", r)
        r, _ = run("本節說明允收標準須符合資料表。", ctx(11, "允收標準", ("iq", "允收標準")))
        self.assertNotIn("結果禁令", r)                                      # 非結果節不適用


class TestUseBinding(unittest.TestCase):                                  # C-10
    def test_value_in_wrong_use_blocked(self):
        r, d = run("安裝驗證期間需連續運轉 72 h。", ctx(9, "器具材料", ("iq", "器具材料")))    # pq允收 值進 iq 節
        self.assertIn("用途錯置", r)
        r, d = run("計畫核准日為 2026-11-02。", ctx(1, "計畫核准"))                       # 啟用日 進 核准節
        self.assertIn("用途錯置", r)

    def test_value_in_right_use_passes(self):
        r, _ = run("核對資產編號 SYN-EQ9-017 與電源 220 V。", ctx(9, "器具材料", ("iq", "器具材料")))
        self.assertNotIn("用途錯置", r)
        r, _ = run("偏差依 SOP-SYN-201 處理。", ctx(12, "超標處理", ("iq", "超標處理")))
        self.assertNotIn("用途錯置", r)

    def test_backward_compat_policy_none(self):
        raw = json.dumps({"section_id": "S09", "body": "核對。", "refs": [], "sop_refs": []}, ensure_ascii=False)
        r = g.gate_section(raw, g.build_allow(INTAKE, REFS1), set(), set())
        self.assertEqual(r["policy"], {})


class TestClauseBinding(unittest.TestCase):                               # C-11
    def test_other_section_clause_blocked(self):
        r, d = run(f"依 {V} 3.13 執行。", ctx(9, "器具材料", ("iq", "器具材料")))            # PQ 條號進 IQ 節
        self.assertGreater(d["clause_misplaced"], 0)
        self.assertNotIn("章節錯置", r)                                       # M5.4 C-8：改審閱對照，不攔
        r, _ = run(f"依 {V} 3.13 執行。", dict(ctx(9, "器具材料", ("iq", "器具材料")), clause_gate="block"))
        self.assertIn("章節錯置", r)
        r, d = run("本節名詞定義。", ctx(3, "定義Definition"), [{"law": "PIC/S GMP Annex 15", "clause": "3.9", "version": "PE 009-18"}])
        self.assertGreater(d["clause_misplaced"], 0)                          # refs 條號也計入審閱對照

    def test_own_section_clause_passes(self):
        r, _ = run(f"依 {V} 3.9 執行。", ctx(9, "器具材料", ("iq", "器具材料")))
        self.assertNotIn("章節錯置", r)
        r, _ = run(f"依 {V} 11.1、11.2 記錄修改。", ctx(36, "修改歷程"))
        self.assertNotIn("章節錯置", r)


class TestVersion(unittest.TestCase):                                     # C-12
    def test_missing_version_blocked(self):
        r, d = run("依 PIC/S GMP Annex 15 3.9 執行。", ctx(9, "器具材料", ("iq", "器具材料")))
        self.assertIn("缺版次", r)
        r, d = run(f"依 {V} 3.9 執行。", ctx(9, "器具材料", ("iq", "器具材料")), [{"law": "PIC/S GMP Annex 15", "clause": "3.9"}])
        self.assertIn("缺版次", r)                                            # refs 缺 version

    def test_with_version_passes_and_schema_v2(self):
        r, _ = run(f"依 {V} 3.9 執行。", ctx(9, "器具材料", ("iq", "器具材料")),
                   [{"law": "PIC/S GMP Annex 15", "clause": "3.9", "version": "PE 009-18"}])
        self.assertNotIn("缺版次", r)
        self.assertTrue(g.schema_errors({"section_id": "S", "body": "x", "refs": [{"law": "a", "clause": "1.1"}], "sop_refs": []}, g.SCHEMA_V2))


class TestOverflow(unittest.TestCase):                                    # C-13
    def test_change_control_or_requal_blocked(self):
        r, _ = run("超出允收時啟動變更管制。", ctx(12, "超標處理", ("iq", "超標處理")))
        self.assertIn("超標處置", r)
        r, _ = run("不合格時安排再驗證。", ctx(30, "超標處理", ("pq", "超標處理")))
        self.assertIn("超標處置", r)

    def test_deviation_sop_passes_and_guide_points_to_it(self):
        r, _ = run("超出允收時依 SOP-SYN-201 登錄偏差並調查。", ctx(21, "超標處理", ("oq", "超標處理")))
        self.assertNotIn("超標處置", r)
        gd = g.fy.load(os.path.join(REPO, "specs", "guides", "T027_v0.6.yaml"))
        self.assertTrue(all("偏差處理" in x["guide"] for x in gd["segment_guides"] if x["item"] == "超標處理"))



class TestLawVersionSuffix(unittest.TestCase):
    def test_law_with_version_suffix_counts_as_member(self):
        raw = json.dumps({"section_id": "S16", "body": "依規辦理。", "sop_refs": [],
                          "refs": [{"law": "PIC/S GMP Annex 15（PE 009-18）", "clause": "3.10", "version": "PE 009-18"}]}, ensure_ascii=False)
        law = {g.cs._ns(r["law"] + r["clause"]) for r in REFS1}
        r = g.gate_section(raw, g.build_allow(INTAKE, REFS1), law, set())
        self.assertEqual((r["refs_in"], r["refs_n"]), (1, 1))
        self.assertEqual(g.law_base("PIC/S GMP Annex 15 (PE 009-18)"), "PIC/S GMP Annex 15")



class TestLawTrailingClause(unittest.TestCase):
    """M5.3：law 欄去版次後綴、再去結尾條號；law 內條號須等於 refs.clause。"""
    LAW = {g.cs._ns(r["law"] + r["clause"]) for r in REFS1}

    def gate(self, law, clause):
        raw = json.dumps({"section_id": "S30", "body": "依規辦理。", "sop_refs": [],
                          "refs": [{"law": law, "clause": clause, "version": "PE 009-18"}]}, ensure_ascii=False)
        return g.gate_section(raw, g.build_allow(INTAKE, REFS1), self.LAW, set())

    def test_trailing_clause_equal_passes(self):
        r = self.gate("PIC/S GMP Annex 15（PE 009-18）3.13", "3.13")
        self.assertEqual((r["refs_in"], r["refs_n"]), (1, 1))
        self.assertEqual(g.law_parse("PIC/S GMP Annex 15 3.14（PE 009-18）"), ("PIC/S GMP Annex 15", "3.14"))

    def test_trailing_clause_mismatch_blocked(self):
        r = self.gate("PIC/S GMP Annex 15（PE 009-18）3.13", "3.14")
        self.assertEqual(r["refs_in"], 0)
        self.assertIn("引用", r["reasons"])



class TestResultStatement(unittest.TestCase):
    """M5.4 B：全文內容判——品保 2026-09-30 函 2-1 所列五處句型（合成重述）必須全部命中；規範式句放行。"""
    QA5 = {"計畫核准": "該計畫於 2026-10-01 獲得正式核准。",
           "操作驗證概述": "所有測試項目均符合規定。",
           "性能驗證概述": "完成性能驗證，模擬負載下連續運轉 72 h 無中斷且參數穩定，偏離 0 件。",
           "性能驗證各節": "全程依 SOP 執行，偏離件數為 0 件。",
           "安裝驗證備註": "接點均依據工廠驗收測試結果予以記錄。"}

    def test_qa_five_all_hit(self):
        miss = [k for k, t in self.QA5.items() if not g.cs.result_statement_hits(t)]
        self.assertEqual(miss, [])

    def test_normative_passes(self):
        for t in ("允收：偏離件數應為 0。", "溫度漂移應 ≤ 0.5 ℃。", "升溫須於 30 min 內完成。", "監測參數穩定性與 SOP 一致性。"):
            self.assertEqual(g.cs.result_statement_hits(t), [], t)

    def test_any_section_not_only_result_sections(self):
        r, _ = run("所有測試項目均符合規定。", ctx(16, "操作驗證", ("oq", "_head")))
        self.assertIn("結果陳述", r)
        r, _ = run("計畫於 2026-10-01 獲得核准。", ctx(1, "計畫核准"))
        self.assertIn("結果陳述", r)


if __name__ == "__main__":
    unittest.main()
