#!/bin/bash
#
# speccoding-gate.sh — Speccoding Pre-flight Gate 强制检查
#
# 用法:
#   ./scripts/speccoding-gate.sh check <target-phase>
#   ./scripts/speccoding-gate.sh list
#
# 每次进入新阶段前必须运行此脚本。失败则禁止进入该阶段。
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="${SPECCODING_STATE_FILE:-.speccoding-state.json}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS() { echo -e "${GREEN}✅ PASS${NC}: $1"; }
FAIL() { echo -e "${RED}❌ FAIL${NC}: $1"; }
WARN() { echo -e "${YELLOW}⚠️  WARN${NC}: $1"; }

json_get() {
  local key="$1"
  if [ ! -f "$STATE_FILE" ]; then echo ""; return; fi
  if command -v jq >/dev/null 2>&1; then
    jq -r ".$key // empty" "$STATE_FILE" 2>/dev/null || echo ""
  else
    grep -o "\"$key\":[^,}]*" "$STATE_FILE" | sed 's/.*://' | tr -d ' "'
  fi
}

die() { echo -e "${RED}🚫 GATE BLOCKED: $*${NC}" >&2; exit 1; }

# ─────────────────────────────────────────────
# Gate 检查：proposal
# ─────────────────────────────────────────────

gate_proposal() {
  local change
  change=$(json_get "active_change" || echo "")

  if [[ -z "$change" ]]; then
    PASS "无活跃变更，可进入 proposal"
    return 0
  fi

  local change_dir="openspec/changes/$change"

  # 已有活跃变更时检查是否有未完成的 proposal
  if [[ -f "$change_dir/proposal.md" ]]; then
    if grep -q "提案已确认" "$change_dir/proposal.md" 2>/dev/null; then
      PASS "已有确认的 proposal"
    else
      WARN "proposal.md 存在但尚未确认"
    fi
  else
    PASS "proposal 目录为空，可进入 proposal"
  fi
}

# ─────────────────────────────────────────────
# Gate 检查：brainstorming
# ─────────────────────────────────────────────

gate_brainstorming() {
  local change
  change=$(json_get "active_change") || die "无法读取活跃变更"
  [[ -z "$change" ]] && die "无活跃变更，请先进入 proposal"

  local change_dir="openspec/changes/$change"
  local proposal="$change_dir/proposal.md"

  [[ ! -f "$proposal" ]] && die "proposal.md 不存在，禁止进入 brainstorming"

  if ! grep -q "提案已确认" "$proposal"; then
    die "proposal 尚未由用户确认（需要 Status: - [x] 提案已确认）"
  fi

  PASS "proposal 已确认，可进入 brainstorming"
}

# ─────────────────────────────────────────────
# Gate 检查：spec
# ─────────────────────────────────────────────

gate_spec() {
  local change
  change=$(json_get "active_change") || die "无法读取活跃变更"
  [[ -z "$change" ]] && die "无活跃变更，请先进入 proposal"

  local change_dir="openspec/changes/$change"

  [[ ! -f "$change_dir/proposal.md" ]] && die "proposal.md 不存在，禁止进入 spec"

  if [[ -f "$change_dir/design.md" ]]; then
    PASS "proposal.md 存在，design.md 存在，可进入 spec"
  else
    PASS "proposal.md 存在，可进入 spec（无 design.md，可选）"
  fi
}

# ─────────────────────────────────────────────
# Gate 检查：executing
# ─────────────────────────────────────────────

gate_executing() {
  local change
  change=$(json_get "active_change") || die "无法读取活跃变更"
  [[ -z "$change" ]] && die "无活跃变更"

  local change_dir="openspec/changes/$change"

  [[ ! -f "$change_dir/spec.md" ]] && die "spec.md 不存在，禁止进入 executing"
  [[ ! -f "$change_dir/plan.md" ]] && die "plan.md 不存在，禁止进入 executing"

  local checkbox_count
  checkbox_count=$(grep -c '^\- \[' "$change_dir/plan.md" 2>/dev/null || echo 0)
  [[ "$checkbox_count" -eq 0 ]] && die "plan.md 无任何任务项，禁止进入 executing"

  local spec_synced
  spec_synced=$(json_get "spec_synced" || echo "false")
  if [[ "$spec_synced" != "true" ]]; then
    WARN "spec/ 尚未同步到项目级文档（建议在 archive 前完成）"
  fi

  PASS "spec.md 和 plan.md 存在（$checkbox_count 个任务），可进入 executing"
}

# ─────────────────────────────────────────────
# Gate 检查：archive
# ─────────────────────────────────────────────

gate_archive() {
  local change
  change=$(json_get "active_change") || die "无法读取活跃变更"
  [[ -z "$change" ]] && die "无活跃变更"

  local change_dir="openspec/changes/$change"
  local plan="$change_dir/plan.md"

  [[ ! -f "$plan" ]] && die "plan.md 不存在"

  local undone
  undone=$(grep -c '^\- \[ \]' "$plan" 2>/dev/null || echo 0)
  [[ "$undone" -gt 0 ]] && die "plan.md 尚有 $undone 项未完成，禁止归档"

  # spec/ 完整性检查
  echo ""
  echo "─── spec/ 完整性检查 ───"
  local spec_dir="spec"
  local missing=0

  for f in requirements.md design.md tasks.md structure.md devlog.md; do
    local file="$spec_dir/$f"
    if [[ ! -f "$file" ]]; then
      WARN "spec/$f 不存在"
      missing=$((missing + 1))
    elif grep -q '<!-- 请填写 -->' "$file" 2>/dev/null; then
      FAIL "spec/$f 仍包含占位符 <!-- 请填写 -->"
      missing=$((missing + 1))
    else
      PASS "spec/$f 已填充"
    fi
  done

  echo ""
  [[ "$missing" -gt 0 ]] && die "spec/ 目录尚未填充完毕，禁止归档"

  PASS "plan.md 全部完成，spec/ 已填充，可进入 archive"
}

# ─────────────────────────────────────────────
# Gate 检查：merge
# ─────────────────────────────────────────────

gate_merge() {
  local change branch
  change=$(json_get "active_change") || die "无法读取活跃变更"
  branch=$(json_get "branch") || die "无法读取分支信息"

  [[ -z "$change" ]] && die "无活跃变更"

  local spec_synced
  spec_synced=$(json_get "spec_synced" || echo "false")
  if [[ "$spec_synced" != "true" ]]; then
    die "spec/ 尚未同步到项目级文档（archive 前应已完成），禁止 merge"
  fi

  local code_pushed
  code_pushed=$(json_get "code_pushed" || echo "false")
  if [[ "$code_pushed" != "true" ]]; then
    die "代码尚未推送到远程（需要 git push），禁止 merge"
  fi

  PASS "spec/ 已同步，代码已推送，可进入 merge"
}

# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────

cmd_check() {
  local target_phase="${1:-}"
  [[ -z "$target_phase" ]] && echo "用法: gate.sh check <phase>" && exit 1

  echo ""
  echo "═══════════════════════════════════════"
  echo "  Pre-flight Gate: → $target_phase"
  echo "═══════════════════════════════════════"
  echo ""

  # 无状态文件时，只有 init/proposal 可以直接通过
  if [[ ! -f "$STATE_FILE" ]]; then
    case "$target_phase" in
      init|proposal) PASS "无状态文件，可直接进入 $target_phase"; return 0 ;;
      *) die "无状态文件，请先运行 init" ;;
    esac
  fi

  case "$target_phase" in
    init)         PASS "init 阶段无门控"; return 0 ;;
    proposal)     gate_proposal ;;
    brainstorming) gate_brainstorming ;;
    spec)         gate_spec ;;
    amend)        PASS "amend 可随时进入"; return 0 ;;
    executing)    gate_executing ;;
    archive)      gate_archive ;;
    merge)        gate_merge ;;
    *)            die "未知阶段: $target_phase" ;;
  esac

  echo ""
  echo -e "${GREEN}═══════════════════════════════════════"
  echo "  Gate 结论: 允许进入 $target_phase"
  echo "═══════════════════════════════════════${NC}"
}

cmd_list() {
  echo "Pre-flight Gate 检查清单："
  echo ""
  echo "  init         → 无门控"
  echo "  proposal     → 无门控（有活跃变更时检查是否已确认）"
  echo "  brainstorming → proposal.md 存在 且 Status: - [x] 提案已确认"
  echo "  spec         → proposal.md 存在"
  echo "  amend        → 无门控（可随时进入）"
  echo "  executing    → spec.md 存在 且 plan.md 存在 且 plan.md 有 checkbox"
  echo "  archive      → plan.md 全部为 - [x] 且 spec/ 全部文件已填充无占位符"
  echo "  merge        → spec_synced=true 且 code_pushed=true"
  echo ""
  echo "失败时：脚本 exit 1，AI 禁止进入目标阶段"
}

CMD="${1:-}"
shift || true

case "$CMD" in
  check) cmd_check "$@" ;;
  list)  cmd_list ;;
  *)     echo "用法: $0 {check|list}"; exit 1 ;;
esac
