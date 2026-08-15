#!/usr/bin/env bash
#
# Personal login shortcut: logs in as ifthikarali20@gmail.com via
# scripts/login.sh. Defaults to prod; pass 'local' to hit
# http://localhost:8000 instead. The password is always prompted
# silently, never stored or passed on the command line.
#
# Usage:
#   scripts/login_ifthikar.sh          # prod
#   scripts/login_ifthikar.sh local    # local dev server

exec "$(dirname "$0")/login.sh" "${1:-prod}" "ifthikarali20@gmail.com"
