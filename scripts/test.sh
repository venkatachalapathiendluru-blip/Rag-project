#!/usr/bin/env bash
# Usage: scripts/test.sh offline|db|frontend|e2e|external|benchmark-replay
# offline, db, frontend and benchmark-replay make no external API calls.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-venv/bin/python}"

# Some older test_*.py files are live scripts, so only TestCase modules are listed.
offline_modules() {
  for file in test_*.py; do
    grep -q 'unittest.TestCase' "$file" && echo "${file%.py}"
  done
  echo tests.test_platform_unit
  echo tests.test_live_depth_eval
  echo tests.test_no_network
}

case "${1:-offline}" in
  offline)
    "$PY" -m unittest $(offline_modules)
    ;;
  db)
    # Needs a disposable database. The tests refuse port 5433.
    : "${RAG_TEST_DB_PORT:?Set RAG_TEST_DB_PORT to a disposable database port}"
    "$PY" -m unittest tests.test_platform_integration
    ;;
  frontend)
    (cd frontend && npx tsc -b && npx vitest run && npx vite build)
    ;;
  e2e)
    # Live stack with real model calls: about 4 chat turns.
    (cd frontend && node e2e/acceptance.mjs)
    ;;
  external)
    # Live NVIDIA calls: small but not free.
    "$PY" test_nvidia.py
    "$PY" test_reranker.py
    ;;
  benchmark-replay)
    "$PY" -m backend.replay_golden_retrieval "${2:-platform_retrieval_replay.json}"
    ;;
  *)
    echo "Unknown suite: $1" >&2
    exit 2
    ;;
esac
