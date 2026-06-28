#!/bin/bash
#
# speccoding-checkpoint.sh — Speccoding Checkpoint 写入
#
# 用法:
#   ./scripts/speccoding-checkpoint.sh write
#   ./scripts/speccoding-checkpoint.sh read
#
# Checkpoint 格式:
#   <project-root>/openspec/changes/<change>/checkpoint.md
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="${SPECCODING_STATE_FILE:-.speccoding-state.json}"

# ─────────────────────────────────────────────
# 找到项目根目录（优先从 .speccoding-state.json 所在目录推导）
# ─────────────────────────────────────────────

find_project_root() {
  # 优先：从 state file 的目录往上找 openspec/ 或 .git
  if [[ -f "$STATE_FILE" ]]; then
    local dir
    dir="$(cd "$(dirname "$STATE_FILE")" && pwd)"
    while [[ "$dir" != "/" ]]; do
      if [[ -d "$dir/openspec" ]] || [[ -d "$dir/.git" ]]; then
        echo "$dir"
        return 0
      fi
      dir="$(dirname "$dir")"
    done
  fi

  # 回退：从 git top-level
  if command -v git >/dev/null 2>&1 && git rev-parse --show-toplevel 2>/dev/null; then
    git rev-parse --show-toplevel
    return 0
  fi

  # 回退：相对于脚本所在目录的 ../../..（假设 scripts 在项目根目录下）
  cd "$SCRIPT_DIR/../.." && pwd
}

PROJECT_ROOT="$(find_project_root)"
cd "$PROJECT_ROOT"

# ─────────────────────────────────────────────
# 从 state file 读取当前状态（延迟读取，命令执行时才算）
# ─────────────────────────────────────────────

json_get() {
  local key="$1"
  if [ ! -f "$STATE_FILE" ]; then echo ""; return; fi
  if command -v jq >/dev/null 2>&1; then
    jq -r ".$key // empty" "$STATE_FILE" 2>/dev/null || echo ""
  else
    grep -o "\"$key\":[^,}]*" "$STATE_FILE" | sed 's/.*://' | tr -d ' "'
  fi
}

cmd_write() {
  local change phase plan_total plan_done branch parent_branch
  change=$(json_get "active_change") || change=""
  phase=$(json_get "current_phase") || phase=""
  plan_total=$(json_get "plan_total") || plan_total="0"
  plan_done=$(json_get "plan_done") || plan_done="0"
  branch=$(json_get "branch") || branch=""
  parent_branch=$(json_get "parent_branch") || parent_branch=""

  if [[ -z "$change" ]]; then
    echo "ERROR: 无活跃变更，请先运行 init" >&2
    return 1
  fi

  local checkpoint_dir="$PROJECT_ROOT/openspec/changes/$change"
  local checkpoint_file="$checkpoint_dir/checkpoint.md"

  mkdir -p "$checkpoint_dir"

  local undone_items=""
  if [[ -f "$checkpoint_dir/plan.md" ]]; then
    undone_items=$(grep -n '\- \[' "$checkpoint_dir/plan.md" 2>/dev/null | grep -v '\- \[x\]' | head -20 || echo "(无)")
  fi

  local git_info
  git_info=$(git log --oneline -5 2>/dev/null || echo "(非 Git 仓库)")

  cat > "$checkpoint_file" << EOF
# Checkpoint

**写入时间**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
**项目根目录**: $PROJECT_ROOT
**阶段**: $phase
**活跃变更**: $change
**分支**: $branch
**父分支**: $parent_branch
**Plan 进度**: $plan_done/$plan_total

## 未完成的 Plan 项

\`\`\`
$undone_items
\`\`\`

## 最近修改的文件

\`\`\`
$git_info
\`\`\`
EOF

  echo "Checkpoint 已写入: $checkpoint_file"
  echo ""
  echo "恢复时运行："
  echo "  cd $PROJECT_ROOT"
  echo "  ./scripts/speccoding-checkpoint.sh read"
  echo "  然后读取 plan.md 从第一个未完成任务继续"
}

cmd_read() {
  local change
  change=$(json_get "active_change") || change=""

  if [[ -z "$change" ]]; then
    echo "ERROR: 无法读取活跃变更，state 文件可能已损坏" >&2
    return 1
  fi

  local checkpoint_file="$PROJECT_ROOT/openspec/changes/$change/checkpoint.md"

  if [[ ! -f "$checkpoint_file" ]]; then
    echo "无 checkpoint 文件: $checkpoint_file"
    return 1
  fi

  echo "═══ Checkpoint: $change ═══"
  cat "$checkpoint_file"
}

case "${1:-}" in
  write) cmd_write ;;
  read)  cmd_read ;;
  *)     echo "用法: $0 {write|read}"; exit 1 ;;
esac
