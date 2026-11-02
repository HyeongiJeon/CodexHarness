#!/usr/bin/env bash
# Usage: ./CodexHarness/start.sh <dev|explain|optimize|qa|preview> [harness start options, e.g. --project DIR --dry-run]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$#" -lt 1 ]; then echo "usage: $0 <dev|explain|optimize|qa|preview> [--project DIR] [--dry-run] [--exam]" >&2; exit 2; fi
export PYTHONPATH="$HERE${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m harness start "$@"
