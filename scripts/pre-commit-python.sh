#!/usr/bin/env bash
set -e

STAGED_PY=$(git diff --cached --name-only --diff-filter=ACMR | grep '\.py$' || true)

if [ -z "$STAGED_PY" ]; then
  exit 0
fi

run_pyright() {
  local svc_dir="$1"
  local manager="$2"

  if echo "$STAGED_PY" | grep -q "^${svc_dir}/"; then
    echo "🔍 pyright: ${svc_dir}"
    if [ "$manager" = "uv" ]; then
      (cd "$svc_dir" && uv run pyright .)
    else
      (cd "$svc_dir" && poetry run pyright .)
    fi
  fi
}

run_pyright "packages/question-generation-service" "uv"
run_pyright "packages/learning-engine-service" "poetry"
run_pyright "packages/shared-python" "uv"
