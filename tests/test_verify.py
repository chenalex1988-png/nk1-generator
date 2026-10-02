#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 驗證器 v1 測試 — 零依賴（unittest），對應設計包 §7 驗收與 J-02。

跑法：python3 -m unittest discover -s tests -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
FIX = os.path.join(ROOT, "fixtures")
sys.path.insert(0, SCRIPTS)

from nk1_normalize import normalize  # noqa: E402


def run_cli(claims, out_dir, fuzzy=None):
    cmd = [sys.executable, os.path.join(SCRIPTS, "nk1-verify.py"),
           "--kb", os.path.join(FIX, "kb.jsonl"),
           "--claims", os.path.join(FIX, claims),
           "--out", out_dir]
    if fuzzy is not None:
        cmd += ["--fuzzy", str(fuzzy)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    verified = None
    vp = os.path.join(out_dir, "verified.json")
    if os.path.isfile(vp):
        with open(vp, encoding="utf-8") as fh:
            verified = json.load(fh)
    return p.returncode, p.stdout + p.stderr, verified


class TestVerifier(unittest.TestCase):

    def test_j02_ten_bad_refs_none_supported(self):
        """J-02：植入 10 條錯引，**全數不得為 supported**。任一 supported 即 fail。"""
        with tempfile.TemporaryDirectory() as d:
            rc, _, v = run_cli("claims_bad.json", d)
            self.assertEqual(rc, 1, "錯引集必須回 exit 1")
            self.assertEqual(len(v["claims"]), 10)
            for c in v["claims"]:
                for r in c.get("refs") or []:
                    self.assertNotEqual(r["status"], "supported",
                                        "錯引被判 supported：%s" % c["claim_id"])
                if not c.get("refs"):
                    self.assertEqual(c["status"], "uncited")

    def test_positive_all_supported_exit0(self):
        """正例 10 條全 supported，且 exit 0。"""
        with tempfile.TemporaryDirectory() as d:
            rc, out, v = run_cli("claims_good.json", d)
            self.assertEqual(rc, 0, "正例未全過：%s" % out)
            for c in v["claims"]:
                for r in c["refs"]:
                    self.assertEqual(r["status"], "supported", c["claim_id"])
                    self.assertIsNotNone(r["offset_start"])
                    self.assertIsNotNone(r["quote"])

    def test_exit2_on_malformed_input(self):
        """輸入格式錯 → exit 2（與『驗不過』的 exit 1 分開）。"""
        with tempfile.TemporaryDirectory() as d:
            rc, out, _ = run_cli("claims_malformed.json", d)
            self.assertEqual(rc, 2, out)
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "nk1-verify.py"),
                                "--kb", os.path.join(FIX, "does_not_exist.jsonl"),
                                "--claims", os.path.join(FIX, "claims_good.json"),
                                "--out", d], capture_output=True, text=True)
            self.assertEqual(p.returncode, 2, "KB 讀不到必須 exit 2")

    def test_j09_superseded_ref_is_rejected_distinctly(self):
        """J-09（驗證器側）：引用作廢版 → unsupported，且 reason 必須說「作廢版」。

        🔑 不可與「ref_id 不存在」折疊：前者去換版本，後者去查幻覺，處置不同。"""
        with tempfile.TemporaryDirectory() as d:
            rc, out, v = run_cli("claims_superseded.json", d)
            self.assertEqual(rc, 1, out)
            r = v["claims"][0]["refs"][0]
            self.assertEqual(r["status"], "unsupported")
            self.assertIn("作廢版", r["reason"])
            self.assertNotIn("不存在", r["reason"])

    def test_kb_status_required_fail_closed(self):
        """kb.jsonl 缺 status → exit 2。預設成 effective 就是 fail-open。"""
        with tempfile.TemporaryDirectory() as d:
            kb = os.path.join(d, "kb.jsonl")
            with open(kb, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"ref_id": "X-1", "kind": "C", "version": "1.0",
                                     "clause_no": "1", "text_raw": "測試條文一二三"},
                                    ensure_ascii=False) + "\n")
            p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "nk1-verify.py"),
                                "--kb", kb, "--claims", os.path.join(FIX, "claims_good.json"),
                                "--out", d], capture_output=True, text=True)
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertIn("status", p.stderr)

    def test_clause_from_clause_no(self):
        """clause←clause_no：薄管線 export_kb 直出的欄名要能直接餵。"""
        with open(os.path.join(FIX, "kb.jsonl"), encoding="utf-8") as fh:
            first = json.loads(fh.readline())
        self.assertIn("clause_no", first)
        self.assertNotIn("clause", first)
        with tempfile.TemporaryDirectory() as d:
            rc, out, _ = run_cli("claims_good.json", d)
            self.assertEqual(rc, 0, out)

    def test_normalize_idempotent(self):
        """normalize() 冪等：normalize(normalize(x)) == normalize(x)。"""
        samples = [
            "第 1.2 條：清潔（Cleaning）——溫度 ≤25 ℃",
            "ＡＢＣ１２３　ａｂｃ",
            "「引號」『雙層』〈角〉【方】",
            "",
            "   \t\n  ",
            "XX-YY-000／版次 1.0",
        ]
        for s in samples:
            once = normalize(s)
            self.assertEqual(normalize(once), once, repr(s))

    def test_normalize_keeps_comparison_symbols(self):
        """≤ 與 ≥ 不得被丟掉——丟了會讓兩條意思相反的條文正規化後相同。"""
        self.assertNotEqual(normalize("溫度 ≤25 ℃"), normalize("溫度 ≥25 ℃"))

    def test_kb_text_norm_is_recomputed(self):
        """KB 輸入端的 text_norm 一律忽略重算（fixture 內故意填了假值）。"""
        with open(os.path.join(FIX, "kb.jsonl"), encoding="utf-8") as fh:
            line = fh.readline()
        self.assertIn("亂填", json.loads(line)["text_norm"])
        with tempfile.TemporaryDirectory() as d:
            rc, _, _ = run_cli("claims_good.json", d)
            self.assertEqual(rc, 0, "若信了輸入端的 text_norm，正例不可能全過")

    def test_fuzzy_threshold_produces_partial(self):
        """fuzzy 命中只給 partial，不給 supported。"""
        claims = {"claims": [{"claim_id": "F-01", "text": "近似錨點",
                              "refs": [{"kind": "T-ref", "id": "FAKE-SOP-A-1-5",
                                        "version": "1.0", "clause": "1.5",
                                        "anchor": "覆核人X"}]}]}
        with tempfile.TemporaryDirectory() as d:
            cp = os.path.join(d, "c.json")
            with open(cp, "w", encoding="utf-8") as fh:
                json.dump(claims, fh, ensure_ascii=False)
            p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "nk1-verify.py"),
                                "--kb", os.path.join(FIX, "kb.jsonl"),
                                "--claims", cp, "--out", d, "--fuzzy", "0.70"],
                               capture_output=True, text=True)
            with open(os.path.join(d, "verified.json"), encoding="utf-8") as fh:
                v = json.load(fh)
            self.assertEqual(v["claims"][0]["refs"][0]["status"], "partial", p.stdout + p.stderr)
            self.assertEqual(p.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
