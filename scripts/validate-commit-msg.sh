# Validate commit message format
# Format: <emoji> <type>: <description>

commit_msg_file=$1
commit_msg=$(cat "$commit_msg_file")

# Allowed emojis and their corresponding types
declare -A valid_patterns=(
  ["✨"]="feat"
  ["🐛"]="fix"
  ["📚"]="docs"
  ["💄"]="style"
  ["♻️"]="refactor"
  ["⚡"]="perf"
  ["✅"]="test"
  ["🔧"]="chore"
  ["🚀"]="deploy"
  ["🔒"]="security"
  ["🗃️"]="db"
  ["🎨"]="ui"
)

# Skip validation for merge commits
if echo "$commit_msg" | grep -qE "^Merge (branch|remote-tracking branch)"; then
  exit 0
fi

# Skip validation for commits created by tools (e.g., Claude Code)
if echo "$commit_msg" | grep -qE "🤖 Generated with \[Claude Code\]"; then
  exit 0
fi

# Check if message matches pattern: <emoji> <type>: <description>
valid=false
for emoji in "${!valid_patterns[@]}"; do
  type="${valid_patterns[$emoji]}"
  if echo "$commit_msg" | grep -qE "^$emoji $type: .+"; then
    valid=true
    break
  fi
done

if [ "$valid" = false ]; then
  echo "❌ Invalid commit message format!"
  echo ""
  echo "Format: <emoji> <type>: <description>"
  echo ""
  echo "Valid patterns (on Mac: Ctrl+Cmd+Space to open emoji picker):"
  echo "  ✨ feat: Add new feature"
  echo "  🐛 fix: Fix a bug"
  echo "  📚 docs: Update documentation"
  echo "  💄 style: Format code"
  echo "  ♻️ refactor: Refactor code"
  echo "  ⚡ perf: Performance improvement"
  echo "  ✅ test: Add/update tests"
  echo "  🔧 chore: Maintenance task"
  echo "  🚀 deploy: Deployment-related"
  echo "  🔒 security: Security improvement"
  echo "  🗃️ db: Database changes"
  echo "  🎨 ui: UI/UX improvement"
  echo ""
  echo "Your commit message:"
  echo "  $commit_msg"
  echo ""
  exit 1
fi

exit 0
