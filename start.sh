#!/usr/bin/env bash
# Usage: ./CodexHarness/start.sh <dev|explain|optimize|qa|preview> [harness start options, e.g. --project DIR --dry-run]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$#" -lt 1 ]; then echo "usage: $0 <dev|explain|optimize|qa|preview> [--project DIR] [--dry-run] [--exam]" >&2; exit 2; fi
export PYTHONPATH="$HERE${PYTHONPATH:+:$PYTHONPATH}"
# Git Bash on Korean Windows may default to CP949, while Git/Codex and this repo use UTF-8.
# Force UTF-8 only for the launcher and its child Python processes (no system setting changes).
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
# Some local Codex environments expose Python as `python`, not `python3`.
# Prefer a working Python 3.11+ interpreter; no package installation is needed.
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && \
     "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
    exec "$candidate" -m harness start "$@"
  fi
done
echo "Python 3.11+ not found (checked python3 and python). Run: python --version or python3 --version" >&2
exit 127
