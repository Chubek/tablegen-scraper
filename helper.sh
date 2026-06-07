#!/usr/bin/env bash
# Support utilities for scrape.sh. Prefer running via ./scrape.sh.

err() {
  printf 'error: %s\n' "$*" >&2
}

info() {
  printf '%s\n' "$*" >&2
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    err "missing required command: $1"
    return 127
  }
}

script_dir() {
  local src="${BASH_SOURCE[0]}"
  cd "$(dirname "$src")" >/dev/null 2>&1 && pwd
}

project_root() {
  local dir
  dir="$(script_dir)"
  if [ -d "$dir/TD-Scrape" ] && [ -f "$dir/TD-Scrape/__main__.py" ]; then
    printf '%s\n' "$dir"
    return 0
  fi
  if [ -d "$dir/../TD-Scrape" ] && [ -f "$dir/../TD-Scrape/__main__.py" ]; then
    (cd "$dir/.." >/dev/null 2>&1 && pwd)
    return 0
  fi
  return 1
}

run_td_scrape() {
  local root
  root="$(project_root)" || {
    err "failed to resolve project root containing TD-Scrape/__main__.py"
    return 2
  }
  (
    cd "$root" >/dev/null 2>&1 || exit 2
    exec python3 -m TD-Scrape "$@"
  )
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  printf '%s\n' "helper.sh is a support script. Use ./scrape.sh."
fi
