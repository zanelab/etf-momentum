#!/bin/bash
#
# speccoding-state.sh — Speccoding 工作流状态管理
#
# 用法:
#   ./scripts/speccoding-state.sh init <change-name> [--from-parent <branch>]
#   ./scripts/speccoding-state.sh get
#   ./scripts/speccoding-state.sh phase <new-phase>
#   ./scripts/speccoding-state.sh set <key> <value>
#   ./scripts/speccoding-state.sh checkpoint
#   ./scripts/speccoding-state.sh report
#   ./scripts/speccoding-state.sh help
#
# 状态文件: .speccoding-state.json
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="${SPECCODING_STATE_FILE:-.speccoding-state.json}"

# ─────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────

has_jq() { command -v jq >/dev/null 2>&1; }

json_get() {
  local key="$1"
  if [ ! -f "$STATE_FILE" ]; then echo ""; return; fi
  if has_jq; then
    jq -r ".$key // empty" "$STATE_FILE" 2>/dev/null || echo ""
  else
    grep -o "\"$key\":[^,}]*" "$STATE_FILE" | sed 's/.*://' | tr -d ' "'
  fi
}

json_set() {
  local key="$1"
  local value="$2"
  if [ ! -f "$STATE_FILE" ]; then return 1; fi
  if has_jq; then
    local tmp
    tmp=$(mktemp)
    jq --arg v "$value" \
      ".$key = \$v | .updated_at = \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"" \
      "$STATE_FILE" > "$tmp" && mv "$tmp" "$STATE_FILE"
  else
    sed -i "s/\"$key\":[^,]*/\"$key\": \"$value\"/" "$STATE_FILE"
    sed -i "s/\"updated_at\":[^,]*/\"updated_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"/" "$STATE_FILE"
  fi
}

die() { echo "ERROR: $*" >&2; exit 1; }

# ─────────────────────────────────────────────
# 阶段顺序定义
# ─────────────────────────────────────────────

VALID_PHASES="init proposal brainstorming spec amend executing archive merge"

is_valid_phase() {
  for p in $VALID_PHASES; do
    [[ "$p" == "$1" ]] && return 0
  done
  return 1
}

can_transition() {
  local from="$1" to="$2"
  # amend 可从任意阶段进入
  [[ "$to" == "amend" ]] && return 0
  case "$from" in
    init)          [[ "$to" == "proposal" ]] && return 0 ;;
    proposal)      [[ "$to" == "brainstorming" || "$to" == "spec" ]] && return 0 ;;
    brainstorming) [[ "$to" == "spec" ]] && return 0 ;;
    spec)          [[ "$to" == "executing" ]] && return 0 ;;
    executing)     [[ "$to" == "archive" ]] && return 0 ;;
    archive)       [[ "$to" == "merge" ]] && return 0 ;;
  esac
  return 1
}

# ─────────────────────────────────────────────
# 命令实现
# ─────────────────────────────────────────────

cmd_init() {
  local change_name="" parent_branch="main" from_arg=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --from-parent) parent_branch="$2"; shift 2 ;;
      *)             change_name="$1"; shift ;;
    esac
  done

  [[ -z "$change_name" ]] && die "用法: init <change-name> [--from-parent <branch>]"

  local branch="feature/$change_name"

  cat > "$STATE_FILE" << EOF
{
  "version": 1,
  "active_change": "$change_name",
  "current_phase": "init",
  "branch": "$branch",
  "parent_branch": "$parent_branch",
  "proposal_confirmed": false,
  "design_confirmed": false,
  "spec_created": false,
  "plan_created": false,
  "plan_total": 0,
  "plan_done": 0,
  "spec_synced": false,
  "code_pushed": false,
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

  echo "状态文件已创建: $STATE_FILE"
  echo "  活跃变更: $change_name"
  echo "  分支: $branch"
  echo "  父分支: $parent_branch"
}

cmd_get() {
  if [ ! -f "$STATE_FILE" ]; then
    echo "无状态文件。请先运行 init。"
    return 1
  fi
  if has_jq; then
    jq '.' "$STATE_FILE"
  else
    cat "$STATE_FILE"
  fi
}

cmd_phase() {
  local new_phase="$1"
  if [ ! -f "$STATE_FILE" ]; then die "状态文件不存在。请先运行 init。"; fi
  if ! is_valid_phase "$new_phase"; then die "无效阶段: $new_phase。有效值: $VALID_PHASES"; fi

  local current
  current=$(json_get "current_phase")

  if [[ "$new_phase" == "amend" ]]; then
    echo "→ 进入 amend 阶段（从 $current）"
    json_set "current_phase" "amend"
    return 0
  fi

  if ! can_transition "$current" "$new_phase"; then
    die "不能从阶段 '$current' 直接进入 '$new_phase'。请检查阶段顺序。"
  fi

  echo "→ 阶段推进: $current → $new_phase"
  json_set "current_phase" "$new_phase"
}

cmd_set() {
  local key="$1" value="$2"
  if [ ! -f "$STATE_FILE" ]; then die "状态文件不存在。请先运行 init。"; fi

  # plan_done 上限检查：不能超过 plan_total
  if [[ "$key" == "plan_done" ]]; then
    local total
    total=$(json_get "plan_total")
    if [[ -n "$total" && "$total" != "0" ]]; then
      if [[ "$value" -gt "$total" ]]; then
        die "plan_done ($value) 不能超过 plan_total ($total)"
      fi
    fi
  fi

  json_set "$key" "$value"
  echo "  $key = $value"
}

cmd_checkpoint() {
  if [ ! -f "$STATE_FILE" ]; then die "状态文件不存在。"; fi

  local change
  change=$(json_get "active_change")
  local phase
  phase=$(json_get "current_phase")
  local plan_total
  plan_total=$(json_get "plan_total")
  local plan_done
  plan_done=$(json_get "plan_done")

  local checkpoint_file="openspec/changes/$change/checkpoint.md"
  mkdir -p "openspec/changes/$change"

  cat > "$checkpoint_file" << EOF
# Checkpoint — $(date -u +%Y-%m-%dT%H:%M:%SZ)

## 当前状态
- 阶段: $phase
- 变更: $change
- Plan 进度: $plan_done/$plan_total

EOF

  if [[ -f "openspec/changes/$change/plan.md" ]]; then
    echo "## 未完成的 Plan 项" >> "$checkpoint_file"
    grep -n '\- \[' "openspec/changes/$change/plan.md" | grep -v '\- \[x\]' | head -20 >> "$checkpoint_file"
  fi

  echo "Checkpoint 已写入: $checkpoint_file"
}

cmd_report() {
  if [ ! -f "$STATE_FILE" ]; then
    echo "无活跃变更。请先运行 init。"
    return
  fi

  local change phase branch parent plan_total plan_done
  change=$(json_get "active_change")
  phase=$(json_get "current_phase")
  branch=$(json_get "branch")
  parent=$(json_get "parent_branch")
  plan_total=$(json_get "plan_total")
  plan_done=$(json_get "plan_done")
  local spec_synced
  spec_synced=$(json_get "spec_synced")
  local code_pushed
  code_pushed=$(json_get "code_pushed")

  echo "=========================================="
  echo "  Speccoding 状态报告"
  echo "=========================================="
  echo "  变更: $change"
  echo "  阶段: $phase"
  echo "  分支: $branch"
  echo "  父分支: $parent"
  echo "  Plan: $plan_done/$plan_total"
  echo "  spec/ 已同步: $spec_synced"
  echo "  代码已推送: $code_pushed"
  echo ""
  echo "  可进入阶段:"

  case "$phase" in
    init)         echo "    → proposal" ;;
    proposal)     echo "    → brainstorming / spec" ;;
    brainstorming) echo "    → spec" ;;
    spec)         echo "    → executing" ;;
    amend)        echo "    → （回到 executing 或其他阶段）" ;;
    executing)    echo "    → archive（plan 全部完成时）" ;;
    archive)      echo "    → merge" ;;
  esac
  echo ""
}

cmd_help() {
  cat << EOF
speccoding-state.sh — Speccoding 工作流状态管理

用法: ./scripts/speccoding-state.sh <command> [args]

命令:
  init <change-name> [--from-parent <branch>]
      初始化状态文件，创建 .speccoding-state.json

  get
      读取并输出当前状态

  phase <new-phase>
      推进到指定阶段。自动验证阶段顺序是否合法。
      有效阶段: $VALID_PHASES

  set <key> <value>
      设置单个状态字段

  checkpoint
      将当前进度写入 openspec/changes/<change>/checkpoint.md

  report
      输出简洁的状态报告

  help
      显示本帮助

示例:
  ./scripts/speccoding-state.sh init add-login
  ./scripts/speccoding-state.sh phase proposal
  ./scripts/speccoding-state.sh phase spec
  ./scripts/speccoding-state.sh set plan_done 3
  ./scripts/speccoding-state.sh checkpoint
  ./scripts/speccoding-state.sh report

状态文件: $STATE_FILE
EOF
}

# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

CMD="${1:-help}"
case "$CMD" in
  init|get|phase|set|checkpoint|report|help) ;;
  *) CMD="help" ;;
esac

case "$CMD" in
  init)   shift; cmd_init "$@" ;;
  get)    cmd_get ;;
  phase)  shift; cmd_phase "${1:-}" ;;
  set)    shift; cmd_set "${1:-}" "${2:-}" ;;
  checkpoint) cmd_checkpoint ;;
  report) cmd_report ;;
  help)   cmd_help ;;
esac
