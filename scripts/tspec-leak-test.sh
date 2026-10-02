#!/bin/bash
# NK1 第 5 道閘的測試 — 塞一段 30 字 prompt 原文進假 T-spec，**必須被擋**。
#
# 🔑 完成判據＝【閘的 exit code】＋【它印了什麼】，不是「腳本跑完沒噴錯」。
# 🔴 本測試全程不印 prompt 內容：毒餌由 python 直接寫檔，不經 stdout、不經變數。
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO}" || exit 2
BAIT="${REPO}/specs/T-spec/__leaktest__.md"
RC_ALL=0

cleanup() { rm -f "${BAIT}"; rmdir "${REPO}/specs/T-spec" 2>/dev/null || true; }
trap cleanup EXIT

echo "════ 第 5 道閘測試 ════"
echo ""

# --- 負例：乾淨檔應放行 ---
mkdir -p "${REPO}/specs/T-spec"
printf '# 假 T-spec（乾淨）\n\n- doc_type: 測試\n- sections: []\n- fields: []\n' > "${BAIT}"
python3 "${REPO}/scripts/tspec-leak-check.py" "${REPO}/specs/T-spec" >/dev/null 2>&1
RC="$?"
if [ "${RC}" -eq 0 ]; then echo "✅ 測試 1／2（乾淨檔）：放行，exit 0"
else echo "🔴 測試 1／2（乾淨檔）：**誤擋**，exit ${RC}" >&2; RC_ALL=1; fi

# --- 正例：塞 40 字元 prompt 原文 → 必須擋 ---
# 毒餌由 python 寫入，**不印出**
python3 - "${BAIT}" <<'PY'
import json, os, re, sys
bait = sys.argv[1]
root = os.path.expanduser("~/nk1-data/templates")
src = None
for d, _, fs in os.walk(root):
    for f in sorted(fs):
        if f.endswith(".json"):
            t = re.sub(r"\s+", "", str(json.load(open(os.path.join(d, f), encoding="utf-8"))[0].get("content", "")))
            if len(t) >= 200:
                src = t[100:140]; break
    if src: break
if not src:
    sys.exit(3)
with open(bait, "w", encoding="utf-8") as fh:
    fh.write("# 假 T-spec（毒餌）\n\n- doc_type: 測試\n- note: ")
    fh.write(src)          # 🔴 只寫檔，不 print
    fh.write("\n")
PY
if [ "$?" -ne 0 ]; then echo "🔴 測試 2／2：毒餌製備失敗（語料讀不到）" >&2; exit 2; fi

python3 "${REPO}/scripts/tspec-leak-check.py" "${REPO}/specs/T-spec" >/dev/null 2>&1
RC="$?"
if [ "${RC}" -eq 1 ]; then echo "✅ 測試 2／2（40 字元原句）：**已擋**，exit 1"
else echo "🔴 測試 2／2（40 字元原句）：**沒擋住**，exit ${RC}" >&2; RC_ALL=1; fi

# --- 串到守衛：⑤ 必須出現 FAIL ---
if bash "${REPO}/scripts/nk1-guard.sh" 2>&1 | grep -q "T-spec 洩漏閘未通過"; then
  echo "✅ 串接測試：nk1-guard.sh 第 ⑤ 道確實回報 FAIL"
else
  echo "🔴 串接測試：守衛沒把第 ⑤ 道的失敗接起來" >&2; RC_ALL=1
fi

echo ""
if [ "${RC_ALL}" -eq 0 ]; then echo "🟢 第 5 道閘測試全過"; else echo "🔴 第 5 道閘測試有項目未過" >&2; fi
exit "${RC_ALL}"
