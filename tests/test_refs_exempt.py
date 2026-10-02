#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5.1 A 遮蔽閘例外測試 — 合成規則與合成條目（不讀真清單）。"""
import hashlib, importlib.util, json, os, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_sp = importlib.util.spec_from_file_location("rx", os.path.join(REPO, "scripts", "refs-exempt.py"))
rx = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(rx)
NAME_RULE = r"\b[A-Z][a-z]+ [A-Z][a-z]+\b"          # 合成的人名樣式規則
OTHER_RULE = r"SECRETCO"                            # 合成的其他規則
PV = " ".join(("Process", "Validation"))                # 拼接：字面會觸發人名樣式規則
PQ = " ".join(("Performance", "Qualification"))
TXT = f"Combined {PV} may be performed."


def ref(o, **kw):
    r = {"clause": "3.13", "original": o, "version": "PE 009-18", "source": "PE 009-18／食藥署 2019",
         "original_sha256": hashlib.sha256(o.encode()).hexdigest()}
    r.update(kw)
    return r


class TestRefsExempt(unittest.TestCase):
    def test_eligible_conditions(self):
        self.assertEqual(len(rx.eligible([ref(TXT)])), 1)
        self.assertEqual(rx.eligible([ref(TXT, version="PE 009-14")]), [])
        self.assertEqual(rx.eligible([ref(TXT, original_sha256="0" * 64)]), [])      # sha 不符 → 不給例外
        self.assertEqual(rx.eligible([ref(TXT, source="其他")]), [])

    def test_filter_removes_only_exempt_lines(self):
        line = '+   "original": ' + json.dumps(TXT, ensure_ascii=False) + ","
        diff = "\n".join(["+  {", line, f'+   "title": "{PQ}"'])
        out, n = rx.filter_diff(diff, rx.eligible([ref(TXT)]))
        self.assertEqual(n, 1)
        self.assertNotIn(TXT, out)
        self.assertIn(PQ, out)                             # 非 original 欄照留給完整閘

    def test_exempt_only_from_name_rule(self):
        bad, nn, no = rx.check_exempt(rx.eligible([ref(TXT)]), [NAME_RULE, OTHER_RULE])
        self.assertEqual((bad, nn, no), ([], 1, 1))
        bad, _, _ = rx.check_exempt(rx.eligible([ref(f"SECRETCO {PV}.")]), [NAME_RULE, OTHER_RULE])
        self.assertEqual(bad, ["3.13"])                                              # 其他規則照擋


if __name__ == "__main__":
    unittest.main()
