#!/bin/bash

# Validate branch name format
# Format: <type>/<description>

branch_name=$(git symbolic-ref --short HEAD 2>/dev/null)

# Skip validation for main branches
if [[ "$branch_name" =~ ^(main|develop|master)$ ]]; then
  exit 0
fi

# Valid branch types
valid_types="feat|fix|docs|style|refactor|perf|test|chore"

# Check if branch name matches pattern
if ! [[ "$branch_name" =~ ^($valid_types)/.+ ]]; then
  echo "❌ Invalid branch name: $branch_name"
  echo ""
  echo "Branch name format: <type>/<description>"
  echo ""
  echo "Valid types:"
  echo "  feat/      - New feature"
  echo "  fix/       - Bug fix"
  echo "  docs/      - Documentation"
  echo "  style/     - Code style/formatting"
  echo "  refactor/  - Code refactoring"
  echo "  perf/      - Performance improvement"
  echo "  test/      - Adding/updating tests"
  echo "  chore/     - Maintenance tasks"
  echo ""
  echo "Examples:"
  echo "  feat/user-authentication"
  echo "  fix/quiz-scoring-bug"
  echo "  docs/api-endpoints"
  echo ""
  exit 1
fi

exit 0
