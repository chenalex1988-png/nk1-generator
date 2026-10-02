#!/bin/bash
# NK1 收工守衛 — commit 前跑，七道檢查全過才准 commit（⑦ ahead-behind 為 M5.8 新增）
#
# 🔑 §2.18：禁的是【後果】不是【路徑】。這六道擋的後果各自不同，不是同一件事的六種說法：
#    ①②＝機密外洩（檔案層）　③＝機密外洩（內容層）　④＝阿觀讀到過期世界
#    ⑤＝T 層原句外洩（prompt 全文混進 T-spec；④之外的另一種「內容層」）
#    ⑥＝節名其實是句子（docx 正文句子以「節名」身分進 repo；遮蔽閘與⑤都不查 docx 句子）
#    ⑦＝本機與 origin 分叉／落後（M5.8 接 remote 後；③ 另含文件編號閘＝真號經代號表擋）
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO}" || { echo "🔴 進不去 repo：${REPO}" >&2; exit 2; }
FAIL=0

echo "════ NK1 收工守衛 ════"
echo ""

# --- ① 無 untracked docx／pdf／xlsx ---
echo "① 檢查 untracked 的 docx／pdf／xlsx"
BAD="$(git status --porcelain 2>/dev/null | grep '^??' | sed 's/^?? //' | tr -d '"' | grep -iE '\.(docx|pdf|xlsx)$' || true)"
if [ -n "${BAD}" ]; then
  echo "🔴 FAIL：發現 untracked 的文件檔——這類檔常常就是樂迦／客戶文件本體" >&2
  echo "${BAD}" | sed 's/^/     /' >&2
  FAIL=1
else
  echo "   ✅ PASS：無"
fi
echo ""

# --- ② data/ 在 .gitignore 且無 >1 MB 大檔 ---
echo "② 檢查 data/ 隔離與大檔"
if git check-ignore -q data/ 2>/dev/null; then
  echo "   ✅ data/ 已被 .gitignore 涵蓋"
else
  echo "🔴 FAIL：data/ 沒有被 .gitignore 擋住——資料會進版本歷史，撤不掉" >&2
  FAIL=1
fi
BIG="$(find data -type f -size +1024k 2>/dev/null || true)"
if [ -n "${BIG}" ]; then
  echo "   ⚠️ data/ 內有 >1 MB 檔案（不擋 commit，但要知道它在）："
  echo "${BIG}" | sed 's/^/     /'
else
  echo "   ✅ data/ 無 >1 MB 大檔"
fi
# 大檔也查工作樹（data/ 以外；.venv/ 為 gitignore 的 docxtpl 相依，2026-09-26 起排除）
BIGT="$(find . -type f -size +1024k -not -path './.git/*' -not -path './data/*' -not -path './.venv/*' 2>/dev/null || true)"
if [ -n "${BIGT}" ]; then
  echo "🔴 FAIL：data/ 以外有 >1 MB 檔案，可能是誤放的文件本體" >&2
  echo "${BIGT}" | sed 's/^/     /' >&2
  FAIL=1
else
  echo "   ✅ data/ 以外無 >1 MB 檔案"
fi
echo ""

# --- ③ 待 commit 的 diff 過遮蔽閘 ---
echo "③ 待 commit 的 diff 過遮蔽閘"
DIFF_TMP="$(mktemp -t nk1diff)"
trap 'rm -f "${DIFF_TMP}"' EXIT
# staged 有東西就查 staged，否則查工作樹改動
if [ -n "$(git diff --cached --name-only 2>/dev/null)" ]; then
  git diff --cached > "${DIFF_TMP}"; SRC="staged diff"
else
  git diff > "${DIFF_TMP}"; SRC="工作樹 diff"
fi
if [ ! -s "${DIFF_TMP}" ]; then
  echo "   ⏸ 無待 commit 改動（${SRC} 為空），跳過"
else
  # M5.1 A（Alex 裁）：specs/refs/ 公開法規原文免人名樣式規則——條件符合者移出 diff、另以扣除人名規則後的清單檢查
  DIFF_F="$(mktemp -t nk1difff)"
  python3 "${REPO}/scripts/refs-exempt.py" "${DIFF_TMP}" --out "${DIFF_F}" 2>&1 | sed 's/^/   /'
  ERC="${PIPESTATUS[0]}"
  bash "${REPO}/scripts/masking-gate.sh" "${DIFF_F}" | sed 's/^/   /'
  RC="${PIPESTATUS[0]}"
  # M5.8：真文件編號／原稿資料夾名（真清單之外的另一份清單＝repo 外代號對照表）
  python3 "${REPO}/scripts/nk1_codes.py" check "${DIFF_F}" 2>&1 | sed 's/^/   /'
  CRC="${PIPESTATUS[0]}"
  [ "${CRC}" -eq 0 ] && echo "   ✅ 文件編號閘【通過】：0 真號"
  rm -f "${DIFF_F}"
  [ "${ERC}" -ne 0 ] && RC="${ERC}"
  [ "${CRC}" -ne 0 ] && RC="${CRC}"
  if [ "${RC}" -ne 0 ]; then
    echo "🔴 FAIL：${SRC} 未通過遮蔽閘（exit ${RC}）" >&2
    FAIL=1
  fi
fi
echo ""

# --- ④ 包若源頭變則已重產（比 hash）---
echo "④ 記憶包是否跟得上源頭"
PACK="${REPO}/NK1_記憶包.md"
SRC_FILES="CLAUDE.md memory/MEMORY.md memory/decisions.md memory/todo.md memory/predictions.md"
MISSING=0
for f in ${SRC_FILES}; do [ -f "${f}" ] || MISSING=1; done
if [ "${MISSING}" -eq 1 ]; then
  echo "🔴 FAIL：來源檔缺席，無法比對" >&2; FAIL=1
elif [ ! -f "${PACK}" ]; then
  echo "   ⚠️ 尚未產過包（${PACK} 不存在）→ 收工前請跑 scripts/gen-nk1-pack.sh"
else
  NOW_SRC="$(cat ${SRC_FILES} | shasum -a 256 | cut -c1-12)"
  IN_PACK="$(grep -m1 '| 源頭 hash |' "${PACK}" | sed 's/.*`\(.*\)`.*/\1/')"
  echo "   源頭現值＝${NOW_SRC}　包內記載＝${IN_PACK}"
  if [ "${NOW_SRC}" = "${IN_PACK}" ]; then
    echo "   ✅ PASS：包是最新的"
  else
    echo "🔴 FAIL：源頭已變但包未重產——阿觀會讀到過期世界" >&2
    echo "     → 跑 scripts/gen-nk1-pack.sh 重產後再 commit" >&2
    FAIL=1
  fi
fi
echo ""

# --- ⑤ specs/T-spec/ 無 prompt 原句（≥30 連續字元）---
echo "⑤ specs/T-spec/ 是否含 prompt 原句（≥30 連續字元）"
python3 "${REPO}/scripts/tspec-leak-check.py" "${REPO}/specs/T-spec" 2>&1 | sed 's/^/   /'
TRC="${PIPESTATUS[0]}"
if [ "${TRC}" -ne 0 ]; then
  echo "🔴 FAIL：T-spec 洩漏閘未通過（exit ${TRC}）——T-spec 只准出結構，不准出原句" >&2
  FAIL=1
fi
echo ""

# --- ⑥ 句子閘：進 repo 的 YAML／md 節名欄位與 reports 節名清單 ---
echo "⑥ 句子閘（specs/guards/sentence_gate.yaml）"
python3 "${REPO}/scripts/sentence-gate.py" --staged 2>&1 | sed 's/^/   /'
SRC6="${PIPESTATUS[0]}"
if [ "${SRC6}" -ne 0 ]; then
  echo "🔴 FAIL：句子閘未通過（exit ${SRC6}）——節名欄位出現句子樣式；清單用 --list-out 寫到 repo 外再看" >&2
  FAIL=1
fi
echo ""

# --- ⑦ 對 origin 的 ahead-behind（M5.8 起有 remote；取代「無 remote」提醒）---
echo "⑦ 對 origin 的 ahead-behind"
if ! git remote get-url origin >/dev/null 2>&1; then
  echo "🔴 FAIL：沒有 origin remote（M5.8 起應有）" >&2
  FAIL=1
elif ! git fetch -q origin 2>/dev/null; then
  echo "🔴 FAIL：git fetch origin 失敗——比不了，不當作同步" >&2
  FAIL=1
else
  BR="$(git symbolic-ref --short HEAD)"
  if ! git rev-parse -q --verify "origin/${BR}" >/dev/null; then
    echo "🔴 FAIL：origin 上沒有 ${BR}" >&2
    FAIL=1
  else
    read -r AHEAD BEHIND <<<"$(git rev-list --left-right --count "${BR}...origin/${BR}")"
    echo "   ahead ${AHEAD}／behind ${BEHIND}（${BR} 對 origin/${BR}）"
    if [ "${BEHIND}" -ne 0 ]; then
      echo "🔴 FAIL：落後 origin ${BEHIND}——先處理分叉／落後再 commit" >&2
      FAIL=1
    elif [ "${AHEAD}" -ne 0 ]; then
      echo "   ⚠️ 領先 ${AHEAD}：commit 後記得 push，收尾要 0/0"
    else
      echo "   ✅ 0/0"
    fi
  fi
fi
echo ""

echo "════════════════════"
if [ "${FAIL}" -eq 0 ]; then
  echo "🟢 七道全過，可以 commit"
  echo ""
  echo "📌 提醒：**不要用 \`git add -A\`**，只 add 明列路徑——"
  echo "   \`git add CLAUDE.md memory/ specs/ orders/ reports/ scripts/ .gitignore\`"
  echo "   （\`-A\` 會把你還沒看過的東西一起收進去，那正是這五道閘要防的事。）"
  exit 0
else
  echo "🔴 有檢查未過，**不要 commit**" >&2
  exit 1
fi
