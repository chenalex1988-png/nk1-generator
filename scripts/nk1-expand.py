#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 條號範圍展開器（工單【M4.4】A）— 原則見 specs/guards/normalization_policy.md。

expand_ranges(section_id, text, table_clauses) → (新正文, normalizations[])
  辨識「X 至 Y」「X–Y」「X~Y」「X-Y」（X、Y＝章.條、同章）；三條件全滿足才展開為「X、X+1、…、Y」，
  否則原文不動並記 missing（action:"regen"）。其餘文字一律不動。零依賴、確定性。
"""
import re

VERSION = "1.0.0"
RE_RANGE = re.compile(r"(?<![\d.])(\d{1,2})\.(\d{1,2})\s*(至|到|–|—|~|～|-|－)\s*(\d{1,2})\.(\d{1,2})(?![\d.])")


def expand_ranges(section_id, text, table_clauses):
    table = {str(c) for c in table_clauses}
    norms = []

    def sub(m):
        c1, a, _, c2, b = m.group(1), int(m.group(2)), m.group(3), m.group(4), int(m.group(5))
        orig = m.group(0)
        if c1 != c2 or b <= a:
            norms.append({"section_id": section_id, "kind": "clause_range", "original": orig, "expanded": [],
                          "table_check": "not_same_chapter_or_not_increasing", "action": "regen"})
            return orig
        want = [f"{c1}.{k}" for k in range(a, b + 1)]
        missing = [x for x in want if x not in table]
        if missing:
            norms.append({"section_id": section_id, "kind": "clause_range", "original": orig, "expanded": [],
                          "table_check": f"missing:[{','.join(missing)}]", "action": "regen"})
            return orig
        norms.append({"section_id": section_id, "kind": "clause_range", "original": orig, "expanded": want,
                      "table_check": "all_present"})
        return "、".join(want)

    return RE_RANGE.sub(sub, text), norms
