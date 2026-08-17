#!/usr/bin/env bash
# One command, twice the same way.
#
#   bench/run.sh                 # everything, default rounds
#   bench/run.sh --rounds 20     # longer
#   bench/run.sh --only RestAlchemy Flask
#   bench/run.sh --stop          # put the database away
#
# Brings up a PostgreSQL of its own under bench/.pgdata unless DATABASE_URL
# is set, seeds the same rows every time, and leaves the cluster running for
# the next run.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--stop" ]; then
  bench/.venv/bin/python -c "from bench import database; database.stop()"
  echo "database stopped"
  exit 0
fi

if [ ! -x bench/.venv/bin/python ]; then
  echo "creating the virtualenv"
  uv venv --python 3.12 bench/.venv
  uv pip install --python bench/.venv/bin/python -r bench/requirements.txt
fi

bench/.venv/bin/python - <<'PY'
from bench import database
started = database.start()
rows = database.seed()
print("database ready (%s), %d rows" % ("started by us" if started else "already up", len(rows)))
PY

exec bench/.venv/bin/python -m bench.run "$@"
