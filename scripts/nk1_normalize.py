#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NK1 正規化 — **NK1 與 NK-Locus 共用同一支**（設計包 §7）。

normalize() 是驗證器的地基：KB 與 anchor 走同一條路，否則「找不到」會變成
正規化差異造成的假陰性。**不信任輸入端給的 text_norm，一律重算。**

規則（設計包工單 4）：NFKC → 全形轉半形（NFKC 涵蓋）→ 去所有空白
→ 統一引號／括號／破折號 → 只保留中英數與基本標點。

🔑 normalize_with_map() 另回傳 index map：正規化後第 i 字來自原字串第 map[i] 字。
   **沒有這張表就回填不了 offset**——驗證器要的是原文座標，不是正規化座標。
"""
import unicodedata

__all__ = ["normalize", "normalize_with_map", "NORMALIZE_VERSION"]

NORMALIZE_VERSION = "1.0.0"

# 統一引號／括號／破折號（目標字元本身不得是其他規則的鍵，否則失去冪等性）
TRANS = {}
for ch in '“”‘’「」『』｢｣〝〞＂＇':
    TRANS[ch] = '"'
for ch in '（〔［｛【《〈':
    TRANS[ch] = '('
for ch in '）〕］｝】》〉':
    TRANS[ch] = ')'
for ch in '—–‒―─－〜～':
    TRANS[ch] = '-'

# 保留的基本標點（其餘符號一律丟棄）
# 🔴 比較／度量符號**必須保留**：丟掉 ≤ ≥ ° 會讓「≤25℃」與「≥25℃」正規化後相同，
#    那就是把兩條意思相反的條文變成同一條——錨點會命中錯的地方。
KEEP_PUNCT = set('.,:;!?()"\'-/%#&+=。、·…<>≤≥±°×÷~')


def _keep(c):
    if c in KEEP_PUNCT:
        return True
    if c.isalnum():                      # 中英數（含日韓字）
        return True
    return False


def normalize_with_map(s):
    """回傳 (正規化字串, index map)。map[i] ＝ 該字來自原字串的位置。"""
    if s is None:
        return "", []
    out, idx = [], []
    for i, ch in enumerate(s):
        for c in unicodedata.normalize("NFKC", ch):
            c = TRANS.get(c, c)
            if c.isspace():
                continue
            if not _keep(c):
                continue
            out.append(c)
            idx.append(i)
    return "".join(out), idx


def normalize(s):
    return normalize_with_map(s)[0]
