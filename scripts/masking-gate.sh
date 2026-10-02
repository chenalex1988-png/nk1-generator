#!/bin/bash
# NK1 遮蔽閘 — 被 gen-nk1-pack.sh 與 nk1-guard.sh 共用
#
# 用法：masking-gate.sh <待檢查的檔>
# 回傳：0＝通過；1＝命中拒絕清單（並印出命中行）；2＝閘自身故障（清單找不到等）
#
# 🔑 設計原則：fail-closed。閘自己壞掉要回非 0，不可以「查不到清單就放行」。
#    ——§2.13：假護欄比沒護欄更危險，因為你會信它。
set -u

TARGET="${1:-}"
if [ -z "${TARGET}" ] || [ ! -f "${TARGET}" ]; then
  echo "🔴 遮蔽閘故障：待檢查的檔不存在或未指定（TARGET='${TARGET}'）" >&2
  exit 2
fi

REAL_LIST="${HOME}/nk1-data/denylist.txt"
EXAMPLE_LIST="$(cd "$(dirname "$0")" && pwd)/denylist.example.txt"

if [ -f "${REAL_LIST}" ]; then
  LIST="${REAL_LIST}"; LIST_KIND="真清單"
elif [ -f "${EXAMPLE_LIST}" ]; then
  LIST="${EXAMPLE_LIST}"; LIST_KIND="範例清單（⚠️ 真清單 ${REAL_LIST} 不存在）"
else
  echo "🔴 遮蔽閘故障：真清單與範例清單皆不存在，拒絕放行" >&2
  exit 2
fi

# 去掉註解與空行；空 pattern 會 match 全部，必須濾掉（沉默失敗來源）
PATTERNS="$(mktemp -t nk1gate)"
trap 'rm -f "${PATTERNS}"' EXIT
grep -v '^[[:space:]]*#' "${LIST}" | grep -v '^[[:space:]]*$' > "${PATTERNS}"

PCOUNT="$(wc -l < "${PATTERNS}" | tr -d ' ')"
if [ "${PCOUNT}" -eq 0 ]; then
  echo "🔴 遮蔽閘故障：清單 ${LIST} 濾除註解後為 0 條規則，拒絕放行" >&2
  exit 2
fi

echo "🔍 遮蔽閘：清單＝${LIST_KIND}　規則數＝${PCOUNT}　對象＝${TARGET}"

HITS="$(grep -nE -f "${PATTERNS}" "${TARGET}" 2>/dev/null || true)"

if [ -n "${HITS}" ]; then
  echo "🔴 遮蔽閘【拒絕】：命中拒絕清單" >&2
  echo "${HITS}" | head -20 >&2
  HITN="$(printf '%s\n' "${HITS}" | wc -l | tr -d ' ')"
  echo "　命中行數＝${HITN}（最多顯示 20 行）" >&2
  exit 1
fi

echo "✅ 遮蔽閘【通過】：0 命中"
exit 0
