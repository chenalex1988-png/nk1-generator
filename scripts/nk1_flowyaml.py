# -*- coding: utf-8 -*-
"""NK1 小型 YAML 讀取器（本線未裝 PyYAML）— 只支援本 repo 規格檔用到的子集：
  頂層「鍵: 純量／flow 值」、頂層「鍵:」下接「  - 純量／flow 值」清單；# 開頭為註解。
flow 值（[…]／{…}）以「鍵名補引號 → json」解析；字串值一律雙引號。
"""
import json, re


def _flow(v):
    v = v.strip()
    if not v:
        return None
    if v[0] in "[{":
        j = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', v)
        return json.loads(j)
    if v[0] == '"':
        return json.loads(v)
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return {"true": True, "false": False, "null": None}.get(v, v)


def load(path):
    d, key = {}, None
    for ln, line in enumerate(open(path, encoding="utf8"), 1):
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^\s+-\s+(.*)$", line)
        if m and key:
            d[key].append(_flow(m.group(1)))
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not m:
            raise ValueError(f"{path} 第 {ln} 行無法解析")          # 不回顯內容
        k, v = m.group(1), m.group(2)
        if v.strip():
            d[k], key = _flow(v), None
        else:
            d[k], key = [], k
    return d
