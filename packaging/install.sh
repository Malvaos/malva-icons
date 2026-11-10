#!/usr/bin/env sh
# Install the Malva SVG icon theme.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
exec python3 "$ROOT/tools/icons/install_theme.py" "$@"
