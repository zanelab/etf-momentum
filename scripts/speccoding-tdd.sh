#!/bin/bash
#
# speccoding-tdd.sh — TDD 铁律强制验证
#
# 用法:
#   ./scripts/speccoding-tdd.sh verify <实现文件1> [实现文件2] ...
#   ./scripts/speccoding-tdd.sh check-commit
#   ./scripts/speccoding-tdd.sh list
#
# 验证规则（必须全部满足才算通过）：
#   1. 每个实现文件必须有对应的测试文件
#   2. 测试文件必须存在
#   3. 测试文件最近修改时间 >= 实现文件最近修改时间
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS() { echo -e "${GREEN}✅ PASS${NC}: $1"; }
FAIL() { echo -e "${RED}❌ FAIL${NC}: $1"; }
WARN() { echo -e "${YELLOW}⚠️  WARN${NC}: $1"; }
die() { echo -e "${RED}🚫 TDD VIOLATION: $*${NC}" >&2; exit 1; }

# ─────────────────────────────────────────────
# 语言 → 测试文件扩展名/路径映射
# ─────────────────────────────────────────────

# 常见的测试文件查找模式
# 格式：实现扩展名 → 测试扩展名或相对于 src 的路径模式
EXT_TEST_MAP="
js:jest:src/*.test.js:test/*.test.js:__tests__/*.js
js:mocha:test/*.spec.js:test/*.spec.js
ts:jest:src/*.test.ts:test/*.spec.ts:__tests__/*.ts
ts:mocha:test/*.spec.ts
py:pytest:test_*.py:*_test.py:tests/
py:unittest:test_*.py
go:testing:*_test.go
java:junit:src/test/java/**/*.java
rb:rspec:spec/**/*_spec.rb
rs:rust:src/**/*test*.rs
css:jest:*.css.spec.js:*.test.js
css:playwright:*.spec.js
swift:xcunit:*Test.swift:Tests/*.swift
kt:kotest:src/test/kotlin/**/*.kt
cs:nunit:*Tests.cs:*Test.cs
"

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

has_git() { command -v git >/dev/null 2>&1 && [[ -d .git ]]; }

# 查找实现文件对应的测试文件
find_test_file() {
  local impl_file="$1"
  local impl_dir impl_name impl_ext

  impl_dir=$(dirname "$impl_file")
  impl_name=$(basename "$impl_file" | sed 's/\.[^.]*$//')
  impl_ext=$(basename "$impl_file" | sed 's/.*\.//')

  local test_candidates=""

  case "$impl_ext" in
    js)
      test_candidates="
        ${impl_dir}/${impl_name}.test.js
        ${impl_dir}/${impl_name}.spec.js
        ${impl_dir}/__tests__/${impl_name}.test.js
        ${impl_dir}/__tests__/${impl_name}.spec.js
        test/${impl_name}.test.js
        test/${impl_name}.spec.js
        tests/${impl_name}.test.js
        tests/${impl_name}.spec.js
        spec/${impl_name}.test.js
        spec/${impl_name}.spec.js
      "
      ;;
    ts|tsx)
      test_candidates="
        ${impl_dir}/${impl_name}.test.ts
        ${impl_dir}/${impl_name}.test.tsx
        ${impl_dir}/${impl_name}.spec.ts
        ${impl_dir}/${impl_name}.spec.tsx
        ${impl_dir}/__tests__/${impl_name}.test.ts
        ${impl_dir}/__tests__/${impl_name}.spec.ts
        test/${impl_name}.test.ts
        test/${impl_name}.spec.ts
        tests/${impl_name}.test.ts
        tests/${impl_name}.spec.ts
        spec/${impl_name}.test.ts
        spec/${impl_name}.spec.ts
      "
      ;;
    py)
      test_candidates="
        ${impl_dir}/test_${impl_name}.py
        ${impl_dir}/${impl_name}_test.py
        ${impl_dir}/tests/test_${impl_name}.py
        ${impl_dir}/tests/${impl_name}_test.py
        test/test_${impl_name}.py
        tests/test_${impl_name}.py
      "
      ;;
    go)
      test_candidates="
        ${impl_dir}/${impl_name}_test.go
      "
      ;;
    java)
      test_candidates="
        ${impl_dir}/${impl_name}Test.java
        ${impl_dir}/*Test.java
        src/test/java/$(echo "$impl_file" | sed 's|src/main/java/||' | sed 's|\.|/|g')Test.java
      "
      ;;
    rb)
      test_candidates="
        ${impl_dir}/${impl_name}_spec.rb
        ${impl_dir}/spec/${impl_name}_spec.rb
        spec/${impl_dir}/${impl_name}_spec.rb
      "
      ;;
    rs)
      test_candidates="
        ${impl_dir}/${impl_name}test.rs
        ${impl_dir}/tests/${impl_name}.rs
      "
      ;;
    swift)
      test_candidates="
        ${impl_dir}/${impl_name}Test.swift
        Tests/${impl_name}Test.swift
      "
      ;;
    kt)
      test_candidates="
        ${impl_dir}/${impl_name}Test.kt
        src/test/kotlin/$(echo "$impl_file" | sed 's|src/main/kotlin/||' | sed 's|\.|/|g')Test.kt
      "
      ;;
    cs)
      test_candidates="
        ${impl_dir}/${impl_name}Tests.cs
        ${impl_dir}/${impl_name}Test.cs
        Tests/${impl_name}Tests.cs
      "
      ;;
    *)
      # 通用回退：同名 + test/spec 前缀
      test_candidates="
        ${impl_dir}/test_${impl_name}.${impl_ext}
        ${impl_dir}/${impl_name}.test.${impl_ext}
        ${impl_dir}/${impl_name}.spec.${impl_ext}
        test/${impl_name}.test.${impl_ext}
        tests/${impl_name}.test.${impl_ext}
      "
      ;;
  esac

  for candidate in $test_candidates; do
    if [[ -f "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done

  return 1
}

# 获取文件修改时间（秒级 epoch）
file_mtime() {
  local f="$1"
  if [[ ! -f "$f" ]]; then echo 0; return; fi
  if command -v stat >/dev/null 2>&1; then
    stat -c %Y "$f" 2>/dev/null || echo 0
  else
    # macOS fallback
    stat -f %m "$f" 2>/dev/null || echo 0
  fi
}

# ─────────────────────────────────────────────
# 命令：verify — 验证实现文件是否有对应测试
# ─────────────────────────────────────────────

cmd_verify() {
  shift  # 移除 verify 命令

  if [[ $# -eq 0 ]]; then
    echo "用法: $0 verify <实现文件1> [实现文件2] ..."
    exit 1
  fi

  echo ""
  echo "═══════════════════════════════════════"
  echo "  TDD 验证：检查测试文件"
  echo "═══════════════════════════════════════"
  echo ""

  local failed=0
  local total=0

  for impl_file in "$@"; do
    ((total++)) || true

    # 跳过非代码文件
    if [[ ! -f "$impl_file" ]]; then
      WARN "文件不存在，跳过: $impl_file"
      continue
    fi

    local ext="${impl_file##*.}"
    # 跳过 markdown, yaml, json, toml 等非实现文件
    case "$ext" in
      md|yaml|yml|json|toml|xml|html|css|scss|sass|less) continue ;;
    esac

    local test_file
    test_file=$(find_test_file "$impl_file")

    if [[ -z "$test_file" ]] || [[ ! -f "$test_file" ]]; then
      FAIL "实现文件无对应测试: $impl_file"
      echo "        请先为 $impl_file 编写测试文件再实现"
      echo "        建议的测试文件命名:"
      echo "          ${impl_file%.*}.test.${ext}"
      echo "          test/$(basename "${impl_file%.*}").test.${ext}"
      failed=$((failed + 1))
      continue
    fi

    # 验证测试修改时间 >= 实现修改时间
    local impl_mtime test_mtime
    impl_mtime=$(file_mtime "$impl_file")
    test_mtime=$(file_mtime "$test_file")

    if [[ "$test_mtime" -lt "$impl_mtime" ]]; then
      local impl_date test_date
      impl_date=$(date -d "@$impl_mtime" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r "$impl_mtime" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "$impl_mtime")
      test_date=$(date -d "@$test_mtime" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r "$test_mtime" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "$test_mtime")
      FAIL "TDD 顺序违规: 测试文件 ($test_date) 早于实现文件 ($test_date)"
      echo "        实现文件: $impl_file"
      echo "        测试文件: $test_file"
      echo "        测试必须先于实现编写（先红，再绿）"
      failed=$((failed + 1))
      continue
    fi

    PASS "$impl_file → $test_file"
  done

  echo ""
  if [[ "$failed" -gt 0 ]]; then
    echo -e "${RED}═══════════════════════════════════════${NC}"
    echo -e "${RED}  TDD 验证失败: $failed/$total 项未通过${NC}"
    echo -e "${RED}  禁止提交代码，必须先编写测试！${NC}"
    echo -e "${RED}═══════════════════════════════════════${NC}"
    exit 1
  else
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo -e "${GREEN}  TDD 验证通过: $total/$total 项${NC}"
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
  fi
}

# ─────────────────────────────────────────────
# 命令：check-commit — 检查上一次 git commit 是否符合 TDD
# ─────────────────────────────────────────────

cmd_check_commit() {
  echo ""
  echo "═══════════════════════════════════════"
  echo "  TDD Git Commit 检查"
  echo "═══════════════════════════════════════"
  echo ""

  if ! has_git; then
    WARN "非 Git 仓库，跳过 commit 检查"
    return 0
  fi

  # 获取上一次 commit 修改的实现文件和测试文件
  local changed_impls=()
  local changed_tests=()

  # 检查 git log 的文件变更
  local diff_args="--name-only --format='' HEAD~1..HEAD"
  local changed_files
  changed_files=$(git diff $diff_args 2>/dev/null) || {
    WARN "无法读取 git 历史，跳过检查"
    return 0
  }

  local failed=0

  while IFS= read -r file; do
    [[ -z "$file" ]] && continue

    local ext="${file##*.}"
    case "$ext" in
      md|yaml|yml|json|toml|xml|html) continue ;;
    esac

    local test_file
    test_file=$(find_test_file "$file")

    if [[ -n "$test_file" ]] && [[ -f "$test_file" ]]; then
      # 有对应测试的文件，验证测试也被改了
      if echo "$changed_files" | grep -qF "$test_file"; then
        PASS "$file + $test_file（均已修改）"
      else
        FAIL "实现文件已修改但测试文件未变: $file"
        echo "        测试文件: $test_file"
        failed=$((failed + 1))
      fi
    fi
  done <<< "$changed_files"

  echo ""
  if [[ "$failed" -gt 0 ]]; then
    echo -e "${RED}  TDD Commit 检查失败: $failed 项${NC}"
    exit 1
  fi
}

# ─────────────────────────────────────────────
# 命令：list — 显示支持的扩展名
# ─────────────────────────────────────────────

cmd_list() {
  echo "TDD 验证支持的实现文件扩展名："
  echo ""
  echo "  js, ts, tsx   → Jest/Mocha 测试 (.test.js, .spec.js, .test.ts 等)"
  echo "  py            → pytest/unittest (test_*.py, *_test.py)"
  echo "  go            → Go testing (*_test.go)"
  echo "  java          → JUnit (*Test.java)"
  echo "  rb            → RSpec (spec/*_spec.rb)"
  echo "  rs            → Rust (*test*.rs, tests/*.rs)"
  echo "  swift         → XCUnit (*Test.swift)"
  echo "  kt            → Kotest (*Test.kt)"
  echo "  cs            → NUnit (*Tests.cs, *Test.cs)"
  echo ""
  echo "验证规则："
  echo "  1. 实现文件必须有对应的测试文件"
  echo "  2. 测试文件必须存在于相同或相邻目录"
  echo "  3. 测试文件修改时间 >= 实现文件修改时间"
  echo ""
  echo "在 executing 阶段，每次标记 checkbox 完成前必须运行："
  echo "  ./scripts/speccoding-tdd.sh verify <实现文件1> [实现文件2]"
}

# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

CMD="${1:-}"
shift || true

case "$CMD" in
  verify)       cmd_verify "$@" ;;
  check-commit) cmd_check_commit ;;
  list)         cmd_list ;;
  *)            echo "用法: $0 {verify|check-commit|list}"; exit 1 ;;
esac
