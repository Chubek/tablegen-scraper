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
  ./grab.sh --arch <ARCH> [--output <FILE>]
  ./grab.sh --list-arches
  ./grab.sh --help

Examples:
  ./grab.sh --arch AArch64 --output AArch64.grab.json
  ./grab.sh --list-arches
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
  --list-arches)
    run_td_scrape arch list
    exit $?
    ;;
esac

run_td_scrape grab "$@"
exit $?
