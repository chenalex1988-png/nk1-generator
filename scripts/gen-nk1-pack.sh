#!/bin/bash
# NK1 記憶包產生器 — 產出 NK1_記憶包.md 供阿觀（claude.ai）使用
#
# 🔑 兩條設計原則：
#   ① fail-closed：遮蔽閘沒過、超過大小上限 → 不產出、回非 0。寧可沒有包，不要有髒包。
#   ② 完成判據＝【輸出 hash 前後值】＋【閘 exit code】，不是「腳本跑完沒噴錯」。
#      ——§2.17：有反應只證明管線通，內容才證明它做的是對的事。
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO}" || { echo "🔴 進不去 repo：${REPO}" >&2; exit 2; }

OUT="${REPO}/NK1_記憶包.md"
LIMIT=307200            # 300 KB，fail-closed（硬上限，不動）

# ── 警戒線（只提醒、照樣產包；上限值不動）────────────────────────────
# 🔑 上限擋的是「包壞掉」，有正確的自動處置＝停手；
#    警戒線提的是「該蒸餾了」，**沒有正確的自動處置**（挑哪些歸檔是 Alex 的裁決）→ 只通知，不代決。
WARN=204800             # 200 KB 警戒線
_kb() { echo $(( ( $1 + 512 ) / 1024 )); }
TMP="$(mktemp -t nk1pack)"
trap 'rm -f "${TMP}"' EXIT

# --- 產包前先記錄舊 hash（完成判據的「前值」）---
if [ -f "${OUT}" ]; then OLD_HASH="$(shasum -a 256 "${OUT}" | cut -c1-12)"; else OLD_HASH="(不存在)"; fi

# --- 標頭四行 ---
GEN_TIME="$(date '+%Y-%m-%d %H:%M:%S %z')"
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo '(無 commit)')"
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then DIRTY="🔴 有未 commit 改動"; else DIRTY="✅ 工作樹乾淨"; fi

# 源頭 hash＝所有來源檔內容的合併 hash（來源變了，這個值一定變）
SRC_FILES="CLAUDE.md memory/MEMORY.md memory/decisions.md memory/todo.md memory/predictions.md"
for f in ${SRC_FILES}; do
  [ -f "${f}" ] || { echo "🔴 來源檔缺席：${f}（fail-closed，不產包）" >&2; exit 2; }
done
SRC_HASH="$(cat ${SRC_FILES} | shasum -a 256 | cut -c1-12)"

{
  echo "# NK1 記憶包 v0.1"
  echo ""
  echo "| 標頭 | 值 |"
  echo "|---|---|"
  echo "| 產生時間 | ${GEN_TIME} |"
  echo "| 源頭 hash | \`${SRC_HASH}\` |"
  echo "| commit | \`${COMMIT}\` |"
  echo "| 未 commit 標記 | ${DIRTY} |"
  echo ""
  echo "> 🔴 **本包獨立於 canon 記憶包。canon 記「線」，本包記「案」。FAILURES 只在 canon。**"
  echo "> 阿觀讀不到本機；本包是他唯一的現況來源。**源頭一變就要重產**，否則他讀的是過期世界。"
  echo ""
  echo "---"
  echo ""
} > "${TMP}"

# --- 【一】CLAUDE.md 全文 ---
{ echo "## 【一】CLAUDE.md（工作檔・全文）"; echo ""; cat CLAUDE.md; echo ""; echo "---"; echo ""; } >> "${TMP}"

# --- 【二】MEMORY.md 全文 ---
{ echo "## 【二】memory/MEMORY.md（一頁現況・全文）"; echo ""; cat memory/MEMORY.md; echo ""; echo "---"; echo ""; } >> "${TMP}"

# --- 【三】decisions.md 近 30 天全文 ---
# UTF-8：一律用 python3 切段，不用 awk substr/length（§2 雷區 #2＝byte offset 會切爛全形字）
{ echo "## 【三】memory/decisions.md（近 30 天・全文）"; echo ""; } >> "${TMP}"
python3 - "${TMP}" <<'PYEOF' || { echo "🔴 decisions 切段失敗（fail-closed）" >&2; exit 2; }
import io, sys, re, datetime
tmp = sys.argv[1]
cutoff = datetime.date.today() - datetime.timedelta(days=30)
text = io.open('memory/decisions.md', encoding='utf-8').read()
lines = text.split('\n')
# 以 "## YYYY-MM-DD" 開頭切段；段首日期 >= cutoff 才收
out, keep, seen = [], False, 0
hdr = re.compile(r'^##\s+(\d{4})-(\d{2})-(\d{2})')
for ln in lines:
    m = hdr.match(ln)
    if m:
        d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        keep = (d >= cutoff)
        if keep: seen += 1
    if keep:
        out.append(ln)
if seen == 0:
    out.append('（近 30 天無決策段落）')
with io.open(tmp, 'a', encoding='utf-8') as f:
    f.write('\n'.join(out) + '\n\n---\n\n')
print(f'   decisions：收入 {seen} 個日期段', file=sys.stderr)
PYEOF

# --- 【四】todo.md（略去已完成 [x]）---
{ echo "## 【四】memory/todo.md（略去已完成 \`[x]\`）"; echo ""; } >> "${TMP}"
grep -v '^\s*-\s*\[x\]' memory/todo.md >> "${TMP}" || { echo "🔴 todo 過濾失敗" >&2; exit 2; }
{ echo ""; echo "---"; echo ""; } >> "${TMP}"

# --- 【五】predictions.md 全文 ---
{ echo "## 【五】memory/predictions.md（全文）"; echo ""; cat memory/predictions.md; echo ""; echo "---"; echo ""; } >> "${TMP}"

# --- 【六】specs/ 與 orders/ 檔名與 sha 前 8 索引（只給索引，不給全文）---
{
  echo "## 【六】specs/ 與 orders/ 索引（檔名＋sha256 前 8，不含全文）"
  echo ""
  echo "> 🔑 **只給索引不給全文的理由**：阿觀要的是「有哪些、變沒變」，不是逐字內容；"
  echo "> 要哪一份，開口要，由 Alex 或阿K 貼。**這也讓包的大小不隨案子成長而爆掉。**"
  echo ""
  for d in specs orders; do
    echo "### ${d}/"
    echo ""
    if [ -z "$(ls -A "${d}" 2>/dev/null)" ]; then
      echo "（空）"
    else
      echo "| 檔 | sha256 前 8 |"
      echo "|---|---|"
      find "${d}" -type f ! -name '.DS_Store' | sort | while read -r f; do
        echo "| \`$(basename "${f}")\` | \`$(shasum -a 256 "${f}" | cut -c1-8)\` |"
      done
    fi
    echo ""
  done
} >> "${TMP}"

# --- 🔴 產包前跑遮蔽閘（對「即將成為包」的內容檢查，不是對源頭）---
echo ""
bash "${REPO}/scripts/masking-gate.sh" "${TMP}"
GATE_RC=$?
if [ "${GATE_RC}" -ne 0 ]; then
  echo "🔴 遮蔽閘未通過（exit ${GATE_RC}）→ **不產包**，${OUT} 維持原狀" >&2
  echo "   完成判據：閘 exit code＝${GATE_RC}（非 0）／輸出 hash 前＝${OLD_HASH}　後＝未變更" >&2
  exit 1
fi

# --- 大小上限 fail-closed ---
SIZE="$(wc -c < "${TMP}" | tr -d ' ')"
if [ "${SIZE}" -gt "${LIMIT}" ]; then
  echo "🔴 超過上限：${SIZE} > ${LIMIT} bytes（300 KB）→ **不產包**" >&2
  echo "   完成判據：閘 exit code＝0／大小閘＝FAIL／輸出 hash 前＝${OLD_HASH}　後＝未變更" >&2
  exit 1
fi

mv "${TMP}" "${OUT}" || { echo "🔴 落檔失敗（mv）" >&2; exit 2; }
trap - EXIT
NEW_HASH="$(shasum -a 256 "${OUT}" | cut -c1-12)"

echo ""
echo "✅ 已產：${OUT}"
echo "   大小　　　：${SIZE} bytes（上限 ${LIMIT}）"
echo "   產生時間　：${GEN_TIME}"
echo "   源頭 hash ：${SRC_HASH}"
echo "   commit　　：${COMMIT}　${DIRTY}"
if [ "${SIZE}" -gt "${WARN}" ]; then
  echo "⚠️ 記憶包 $(_kb "${SIZE}") KB 已過警戒線 $(_kb "${WARN}") KB（上限 $(_kb "${LIMIT}") KB）——該蒸餾／歸檔了，見 decisions 2026-09-12 律去重"
fi
echo ""
echo "   📌 完成判據（不是「腳本跑完」）："
echo "      閘 exit code ＝ ${GATE_RC}（0＝通過）"
echo "      輸出 hash 前 ＝ ${OLD_HASH}"
echo "      輸出 hash 後 ＝ ${NEW_HASH}"
if [ "${OLD_HASH}" = "${NEW_HASH}" ]; then
  echo "      ⚠️ 前後 hash 相同＝內容沒變（若你剛改過源頭，這就是異常）"
fi
echo ""
echo "👉 下一步：拖 ${OUT} 到 claude.ai → 阿觀 Project → 換掉舊包（換裝一律由人類執行）"
