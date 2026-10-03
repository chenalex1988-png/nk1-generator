#!/bin/bash
# NK1 交接測試（M6.0）— 接手者在自己的機器（內網主機）跑、自己回報；現執行腦不代跑。
#
# 三項全過＝交接完成（移交計畫第六節）：
#   ① 全部測試過（unittest；以 .venv/bin/python 跑、0 skipped——缺 docxtpl 時渲染測試會被略過，那不算過）
#   ② 守衛七道全過（scripts/nk1-guard.sh exit 0）
#   ③ 以合成資料完成一次離線生成：監看先起→OLLAMA_NO_CLOUD=1 serve→nk1-gen.py（2 輪）→停 serve→停監看；
#      判準＝nk1-gen exit 0、兩輪 docx sha 相同、監看 summary exit 0（全段零外連）且有取到 ollama 程序
#
# 用法：scripts/handover-check.sh [--skel 骨架.yaml] [--ollama ollama執行檔] [--model qwen3.5:9b]
#   未給 --skel 或找不到 ollama → ③ 標「未跑」，整體 exit 3（交接未完成），不是失敗也不是通過。
# exit：0＝三項全過　1＝有項失敗　2＝腳本故障　3＝③ 未跑（需模型的部分由接手者在內網主機補跑）
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO}" || { echo "🔴 進不去 repo：${REPO}" >&2; exit 2; }
SKEL=""; OLLAMA="$(command -v ollama || echo "${HOME}/ollama/bin/ollama")"; MODEL="qwen3.5:9b"
while [ $# -gt 0 ]; do
  case "$1" in
    --skel) SKEL="${2:-}"; shift 2 ;;
    --ollama) OLLAMA="${2:-}"; shift 2 ;;
    --model) MODEL="${2:-}"; shift 2 ;;
    *) echo "🔴 不認得的參數：$1" >&2; exit 2 ;;
  esac
done
PY="${REPO}/.venv/bin/python"
R1=FAIL; R2=FAIL; R3=未跑

echo "════ NK1 交接測試 ════"
echo "機器：$(hostname)　$(uname -sm)　HEAD $(git rev-parse --short HEAD)"
echo ""

# --- ① 測試 ---
echo "① 全部測試"
if [ ! -x "${PY}" ]; then
  echo "🔴 FAIL：.venv 不存在（RUNBOOK §2）——無 .venv 時渲染測試會被略過，不算過" >&2
else
  OUT="$("${PY}" -m unittest discover -s tests 2>&1)"; RC=$?
  echo "${OUT}" | grep -E "^Ran |^OK|^FAILED" | sed 's/^/   /'
  if [ "${RC}" -eq 0 ] && ! echo "${OUT}" | grep -q "skipped="; then R1=PASS; echo "   ✅ 全過、0 skipped"
  else echo "🔴 FAIL：測試未全過或有略過（exit ${RC}）" >&2; fi
fi
echo ""

# --- ② 守衛 ---
echo "② 守衛七道"
if bash scripts/nk1-guard.sh > /tmp/nk1-handover-guard.txt 2>&1; then R2=PASS; echo "   ✅ 七道全過"
else grep -E "^🔴" /tmp/nk1-handover-guard.txt | sed 's/^/   /'; echo "🔴 FAIL：守衛未過（全文 /tmp/nk1-handover-guard.txt）" >&2; fi
echo ""

# --- ③ 離線生成 ---
echo "③ 合成資料離線生成（全程監看）"
if [ -z "${SKEL}" ] || [ ! -f "${SKEL}" ]; then
  echo "   ⏸ 未跑：未給 --skel 或檔不存在（骨架另包交付：NK1_骨架包_v0.7，--skel ~/nk1-data/skel/T027/fbad2c5b.v0.7.yaml）"
elif [ ! -x "${OLLAMA}" ]; then
  echo "   ⏸ 未跑：找不到 ollama 執行檔（${OLLAMA}；ENVIRONMENT §2、RUNBOOK §4）"
elif ! command -v lsof >/dev/null; then
  echo "   ⏸ 未跑：沒有 lsof——監看無法取樣，零外連無從證明（ENVIRONMENT §4 E5）"
elif curl -s -m 2 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  echo "🔴 FAIL：11434 已有服務在跑——監看必須先於 serve 啟動，請先停掉既有 ollama 再跑" >&2; R3=FAIL
else
  W="${HOME}/nk1-data/netwatch/handover-$(date +%Y%m%d-%H%M%S)"; G="${HOME}/nk1-data/gen/handover"
  mkdir -p "${W}" "${G}" "${G}-inbox"
  python3 scripts/nk1-netwatch.py watch --log "${W}/log.jsonl" --stop-file "${W}/STOP" & WP=$!
  sleep 2; python3 scripts/nk1-netwatch.py mark --phases "${W}/phases.jsonl" "serve 啟動"
  OLLAMA_NO_CLOUD=1 "${OLLAMA}" serve > "${W}/serve.log" 2>&1 & SP=$!
  for _ in $(seq 1 30); do curl -s -m 2 http://127.0.0.1:11434/api/version >/dev/null 2>&1 && break; sleep 1; done
  grep -i "cloud disabled" "${W}/serve.log" | tail -1 | sed 's/^/   serve log：/'
  python3 scripts/nk1-netwatch.py mark --phases "${W}/phases.jsonl" "生成"
  "${PY}" scripts/nk1-gen.py \
    --intake fixtures/intake_synth_v0.6.json --intake-spec specs/intake_v0.6.yaml \
    --section-uses specs/guards/section_uses_T027.yaml --skel "${SKEL}" \
    --guides specs/guides/T027_v0.7.yaml --refs specs/refs/annex15_v1.json \
    --model "${MODEL}" --out-dir "${G}" --report "${W}/gen-report.md" --inbox "${G}-inbox" > "${W}/gen.log" 2>&1
  GRC=$?
  python3 scripts/nk1-netwatch.py mark --phases "${W}/phases.jsonl" "停 ollama"
  kill -TERM "${SP}" 2>/dev/null; wait "${SP}" 2>/dev/null
  sleep 3; touch "${W}/STOP"; wait "${WP}" 2>/dev/null
  python3 scripts/nk1-netwatch.py summary --log "${W}/log.jsonl" --phases "${W}/phases.jsonl" --md > "${W}/summary.md" 2>&1; NRC=$?
  STATS="$(ls -td "${G}"/*/ 2>/dev/null | head -1)stats.json"
  SAME="$(python3 -c "import json,sys; s=json.load(open(sys.argv[1])); print(len({r['docx_sha'] for r in s['runs']})==1 and len(s['runs'])>=2)" "${STATS}" 2>/dev/null || echo False)"
  SEEN="$(python3 -c "import json,sys; print(sum(1 for l in open(sys.argv[1]) if json.loads(l).get('pids')))" "${W}/log.jsonl" 2>/dev/null || echo 0)"
  echo "   nk1-gen exit ${GRC}　兩輪 docx sha 相同：${SAME}　監看 summary exit ${NRC}　有程序的取樣 ${SEEN}"
  echo "   紀錄：${W}（repo 外）"
  if [ "${GRC}" -eq 0 ] && [ "${SAME}" = "True" ] && [ "${NRC}" -eq 0 ] && [ "${SEEN}" -gt 0 ]; then R3=PASS; echo "   ✅ 離線生成完成、全程零外連"
  else R3=FAIL; echo "🔴 FAIL：見 ${W}/gen.log、summary.md（有外連＝立刻停、回報 Alex，不重跑）" >&2; fi
fi
echo ""

echo "════════════════════"
echo "① ${R1}　② ${R2}　③ ${R3}"
if [ "${R1}${R2}${R3}" = "PASSPASSPASS" ]; then echo "🟢 交接測試三項全過——請接手者自己回報（貼本輸出）"; exit 0; fi
if [ "${R1}" = "FAIL" ] || [ "${R2}" = "FAIL" ] || [ "${R3}" = "FAIL" ]; then echo "🔴 交接未完成：有項失敗" >&2; exit 1; fi
echo "⏸ 交接未完成：③ 未跑（需模型，由接手者在內網主機補跑）"; exit 3
