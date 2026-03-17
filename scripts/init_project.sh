#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/init_project.sh <project-slug> [project-title]

Example:
  bash scripts/init_project.sh my-story "真假千金反杀"
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 1
fi

project_slug="$1"
project_title="${2:-$project_slug}"

if [[ ! "$project_slug" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  echo "Error: project slug must match ^[A-Za-z0-9][A-Za-z0-9._-]*$" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
template_dir="$repo_root/templates/project"
output_root="$repo_root/output"
project_dir="$output_root/$project_slug"

if [[ ! -d "$template_dir" ]]; then
  echo "Error: missing template directory: $template_dir" >&2
  exit 1
fi

if [[ -e "$project_dir" ]]; then
  echo "Error: target project already exists: $project_dir" >&2
  exit 1
fi

mkdir -p "$output_root"
cp -R "$template_dir/." "$project_dir"

cat > "$project_dir/PROJECT_INFO.md" <<EOF
# Project Info

- Project slug: $project_slug
- Project title: $project_title
- Created at: $(date '+%Y-%m-%d %H:%M:%S %z')

## Notes

- 从 \`00_Brainstorm.md\` 开始
- 当前项目产物目录：\`output/$project_slug/\`
EOF

python3 "$repo_root/scripts/guard.py" init-state "$project_slug" --title "$project_title" >/dev/null

echo "Created project: $project_dir"
echo "Next:"
echo "1. Tell Claude Code which project to work on"
echo "2. Start from intake or idea fission"
echo "3. Keep total files and stage_logs in sync"
