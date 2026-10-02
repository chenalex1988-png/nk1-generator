#!/bin/bash
# NK1 收件守衛（第 8 道，M6.0）— 合併數位經理回送的 commit 之前跑；只在阿K（Air2，唯一寫入者）這邊跑。
#
# 用法：
#   scripts/nk1-inbound.sh BUNDLE             # 回送 bundle（git bundle create … main）
#   scripts/nk1-inbound.sh --patches DIR      # 回送 format-patch 目錄（以 git am 套到暫存分支）
#
# 做的事（**不自動合併**；全過才印出合併指令，由阿K 手動合、跑守衛七道、push）：
#   0. 前置：工作樹乾淨、在 main、對 origin 0/0
#   1. 取件：bundle verify → fetch 到 refs/inbound/main（patches → 暫存 worktree git am）
#   2. 第 8 道（diff＝merge-base 起她新增的改動；另查 commit 作者／訊息）：
#      a 不得新增 docx／pdf／xlsx／zip、>1 MB 檔、data/ 下任何檔
#      b 遮蔽閘（真清單；含英文人名樣式）＋ 文件編號閘（代號對照表；真號／原稿資料夾名＝~/nk1-data 內容；替換數 >0 即命中）
#      b' 人名清單 ~/nk1-data/names.txt（逐字；缺席＝fail-closed）
#      c prompt 原句指紋（≥30 字元，~/nk1-data/templates 語料）＝~/nk1-data 內容
#      d 信箱（允許 *.invalid 與 noreply@anthropic.com）
#      e IPv4（允許 127.0.0.1、0.0.0.0）
#   3. 暫存 worktree 試合併 → 全部測試（unittest）
#
# 🔑 §2.18：禁的是【後果】——她的改動把 ~/nk1-data 內容、人名、信箱、IP 帶進 Alex 的 GitHub。
#    命中只印檔名、行數、規則類別，**不印命中內容**（同遮蔽閘原則）。
# exit：0＝全過可合　1＝有命中（退件）　2＝故障（fail-closed，不當作通過）
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO}" || { echo "🔴 進不去 repo：${REPO}" >&2; exit 2; }
INREF="refs/inbound/main"
TMPD="$(mktemp -d -t nk1in)"
WT="${TMPD}/wt"
cleanup() { git worktree remove --force "${WT}" >/dev/null 2>&1; rm -rf "${TMPD}"; }
trap cleanup EXIT
FAIL=0
die() { echo "🔴 $*" >&2; exit 2; }

MODE="bundle"; SRC="${1:-}"
if [ "${SRC}" = "--patches" ]; then MODE="patches"; SRC="${2:-}"; fi
[ -n "${SRC}" ] && [ -e "${SRC}" ] || die "用法：nk1-inbound.sh BUNDLE｜--patches DIR（找不到：'${SRC}'）"

echo "════ NK1 收件守衛（第 8 道）════"
# --- 0 前置 ---
[ -z "$(git status --porcelain)" ] || die "工作樹不乾淨，先處理再收件"
[ "$(git symbolic-ref --short HEAD)" = "main" ] || die "不在 main"
git fetch -q origin || die "git fetch origin 失敗——比不了，不當作同步"
read -r A B <<<"$(git rev-list --left-right --count main...origin/main)"
[ "${A}" = "0" ] && [ "${B}" = "0" ] || die "main 對 origin 不是 0/0（ahead ${A}／behind ${B}）"

# --- 1 取件 ---
if [ "${MODE}" = "bundle" ]; then
  git bundle verify "${SRC}" >"${TMPD}/verify.txt" 2>&1 || { cat "${TMPD}/verify.txt" >&2; die "bundle verify 失敗"; }
  git fetch -q "${SRC}" "+refs/heads/main:${INREF}" || die "自 bundle 取 main 失敗（bundle 須含 main）"
  git worktree add -q --detach "${WT}" main || die "建暫存 worktree 失敗"
else
  git worktree add -q --detach "${WT}" main || die "建暫存 worktree 失敗"
  ls "${SRC}"/*.patch >/dev/null 2>&1 || die "目錄內沒有 .patch"
  ( cd "${WT}" && git am -q "${SRC}"/*.patch ) || die "git am 失敗（patch 與 main 不相容）"
  git update-ref "${INREF}" "$(git -C "${WT}" rev-parse HEAD)"
  git -C "${WT}" checkout -q --detach main
fi
BASE="$(git merge-base main "${INREF}")" || die "與 main 無共同祖先——不是由交付 bundle 長出來的"
N="$(git rev-list --count "${BASE}..${INREF}")"
echo "   來件：${N} 個 commit（merge-base $(git rev-parse --short "${BASE}")）"
[ "${N}" -gt 0 ] || { echo "   ⏸ 沒有新 commit，無事可合"; exit 0; }
git log --format='     %h %s' "${BASE}..${INREF}"
DIFF="${TMPD}/in.diff"; ADDED="${TMPD}/added/added.txt"; META="${TMPD}/meta.txt"
mkdir -p "${TMPD}/added"
git diff "${BASE}" "${INREF}" > "${DIFF}"
grep '^+' "${DIFF}" | grep -v '^+++ ' | sed 's/^+//' > "${ADDED}" || true
git log --format='%an%n%ae%n%cn%n%ce%n%B' "${BASE}..${INREF}" > "${META}"
echo ""

# --- 2a 檔案層 ---
echo "⑧a 檔案層（文件檔／大檔／data/）"
BADF="$(git diff --name-only --diff-filter=AMR "${BASE}" "${INREF}" | grep -iE '\.(docx|pdf|xlsx|zip)$|^data/' || true)"
BIG=""
while IFS= read -r f; do
  [ -n "${f}" ] || continue
  s="$(git cat-file -s "${INREF}:${f}" 2>/dev/null || echo 0)"
  [ "${s}" -gt 1048576 ] && BIG="${BIG}${f}\n"
done < <(git diff --name-only --diff-filter=AMR "${BASE}" "${INREF}")
if [ -n "${BADF}${BIG}" ]; then
  echo "🔴 FAIL：" >&2; printf '%s\n' "${BADF}" | sed '/^$/d;s/^/     /' >&2; printf "${BIG}" | sed '/^$/d;s/^/     >1MB /' >&2; FAIL=1
else echo "   ✅ 無"; fi

# --- 2b 遮蔽閘＋文件編號閘 ---
echo "⑧b 遮蔽閘（人名等）＋文件編號閘"
DIFF_F="${TMPD}/in.filtered.diff"
python3 "${REPO}/scripts/refs-exempt.py" "${DIFF}" --out "${DIFF_F}" 2>&1 | sed 's/^/   /'; ERC="${PIPESTATUS[0]}"
bash "${REPO}/scripts/masking-gate.sh" "${DIFF_F}" | sed 's/^/   /'; RC="${PIPESTATUS[0]}"
bash "${REPO}/scripts/masking-gate.sh" "${META}" >/dev/null 2>&1; MRC=$?
# 嚴格：可換成代號的真號（替換數 >0）也算命中——`nk1_codes.py check` 只以「殘留」判 exit，替換數不計（守衛 ③ 現行行為，M6.0 回報待裁）
python3 - "${REPO}/scripts/nk1_codes.py" "${DIFF_F}" "${META}" <<'PY' 2>&1 | sed 's/^/   /'; CRC="${PIPESTATUS[0]}"
import importlib.util, sys
sp = importlib.util.spec_from_file_location("c", sys.argv[1]); c = importlib.util.module_from_spec(sp)
try:
    sp.loader.exec_module(c); rows = c.load()
except SystemExit:
    sys.exit(2)
bad = 0
for p in sys.argv[2:]:
    _, n, left = c.encode(open(p, encoding="utf8").read(), rows)
    if n or left:
        print(f"🔴 文件編號閘：{'commit 作者／訊息' if p == sys.argv[3] else 'diff'} 真號 {n}、歧義 {len(left)}（內容不印）")
        bad += 1
print("✅ 文件編號閘：0 真號" if not bad else "")
sys.exit(1 if bad else 0)
PY
for v in ERC RC CRC; do eval "x=\${$v}"; [ "${x}" -eq 2 ] && die "⑧b 閘自身故障（${v}=2）"; done
[ "${MRC}" -eq 2 ] && die "⑧b 遮蔽閘（commit 作者／訊息）故障"
if [ "${ERC}" -ne 0 ] || [ "${RC}" -ne 0 ] || [ "${CRC}" -ne 0 ]; then echo "🔴 FAIL：diff 命中遮蔽閘或文件編號閘" >&2; FAIL=1; fi
if [ "${MRC}" -ne 0 ]; then echo "🔴 FAIL：commit 作者／訊息命中遮蔽清單（內容不印）" >&2; FAIL=1; fi
[ "${ERC}${RC}${CRC}${MRC}" = "0000" ] && echo "   ✅ 0 命中（diff＋commit 作者／訊息）"

# --- 2b' 人名清單（中文人名等遮蔽閘樣式抓不到者；逐字比對，清單在 repo 外）---
echo "⑧b' 人名清單（~/nk1-data/names.txt）"
NAMES="${HOME}/nk1-data/names.txt"
if [ ! -s "${NAMES}" ]; then
  echo "🔴 FAIL：人名清單缺席或為空（fail-closed）——遮蔽閘只有英文人名樣式，中文人名須靠此清單" >&2; FAIL=1
else
  NL="${TMPD}/names.pat"; grep -v '^[[:space:]]*#' "${NAMES}" | sed '/^[[:space:]]*$/d' > "${NL}"
  NH="$(cat "${ADDED}" "${META}" | grep -cFf "${NL}" || true)"
  if [ "${NH}" != "0" ]; then echo "🔴 FAIL：命中人名清單 ${NH} 行（內容不印）" >&2; FAIL=1; else echo "   ✅ 0（清單 $(wc -l < "${NL}" | tr -d ' ') 條）"; fi
fi

# --- 2c prompt 原句指紋 ---
echo "⑧c ~/nk1-data 語料原句（≥30 字元）"
python3 "${REPO}/scripts/tspec-leak-check.py" "${TMPD}/added" 2>&1 | sed 's/^/   /'; TRC="${PIPESTATUS[0]}"
[ "${TRC}" -eq 2 ] && die "⑧c 指紋閘故障"
[ "${TRC}" -ne 0 ] && { echo "🔴 FAIL：新增內容含語料原句" >&2; FAIL=1; }

# --- 2d 信箱／2e IPv4（只印數量）---
EMAIL_RE='[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
IP_RE='(^|[^0-9.])((25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])($|[^0-9.])'
count_bad_email() { grep -oE "${EMAIL_RE}" "$1" | grep -vE '@[A-Za-z0-9.-]+\.invalid$|^noreply@anthropic\.com$' | wc -l | tr -d ' '; }
count_bad_ip() { grep -oE "${IP_RE}" "$1" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | grep -vxE '127\.0\.0\.1|0\.0\.0\.0' | wc -l | tr -d ' '; }
echo "⑧d 信箱"
E1="$(count_bad_email "${ADDED}")"; E2="$(count_bad_email "${META}")"
if [ "${E1}" != "0" ] || [ "${E2}" != "0" ]; then echo "🔴 FAIL：信箱 diff ${E1}／commit 作者與訊息 ${E2}（允許 *.invalid）" >&2; FAIL=1; else echo "   ✅ 0"; fi
echo "⑧e IPv4"
I1="$(count_bad_ip "${ADDED}")"; I2="$(count_bad_ip "${META}")"
if [ "${I1}" != "0" ] || [ "${I2}" != "0" ]; then echo "🔴 FAIL：IP diff ${I1}／commit 訊息 ${I2}（允許 127.0.0.1、0.0.0.0）" >&2; FAIL=1; else echo "   ✅ 0"; fi
echo ""

# --- 3 試合併＋測試 ---
echo "⑧f 暫存 worktree 試合併＋全部測試"
if ( cd "${WT}" && git merge -q --no-ff --no-edit "${INREF}" >/dev/null 2>&1 ); then
  if ( cd "${WT}" && python3 -m unittest discover -s tests 2>&1 | tail -3 | sed 's/^/   /'; exit "${PIPESTATUS[0]}" ); then echo "   ✅ 測試全過"
  else echo "🔴 FAIL：試合併後測試未過" >&2; FAIL=1; fi
else echo "🔴 FAIL：與 main 有衝突，試合併失敗（退回請她以最新交付 bundle 重做）" >&2; FAIL=1; fi
echo ""

echo "════════════════════"
if [ "${FAIL}" -eq 0 ]; then
  echo "🟢 第 8 道全過。合併（手動）："
  echo "   git merge --no-ff ${INREF} -m '合併數位經理回送（${N} commit）'"
  echo "   scripts/gen-nk1-pack.sh && git add NK1_記憶包.md && bash scripts/nk1-guard.sh && git commit -m '重產記憶包' && git push origin main"
  echo "   之後重出交付 bundle（RUNBOOK §8）"
  exit 0
fi
echo "🔴 第 8 道未過：不合、退件（只回報規則類別與檔名，不轉述命中內容）" >&2
exit 1
