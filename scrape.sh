#!/usr/bin/env bash
set -u

SELF_DIR="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd)"
HELPER="$SELF_DIR/helper.sh"

if [ ! -f "$HELPER" ]; then
  printf 'error: helper script not found: %s\n' "$HELPER" >&2
  exit 2
fi

# shellcheck source=./helper.sh
. "$HELPER"

usage() {
  cat <<'EOF'
Usage:
  ./scrape.sh <td-scrape-command> [args...]
  ./scrape.sh --help
  ./scrape.sh help

Wrapper over:
  python3 -m TD-Scrape ...

Examples:
  ./scrape.sh scrape --instructions --opcodes
  ./scrape.sh scrape --mnemonics
  ./scrape.sh scrape --all
  ./scrape.sh scrape --help
EOF
}

need_cmd python3 || exit $?

if [ "$#" -eq 0 ]; then
  usage >&2
  exit 2
fi

case "${1:-}" in
  -h|--help|help)
    usage
    exit 0
    ;;
esac

run_td_scrape "$@"
exit $?
