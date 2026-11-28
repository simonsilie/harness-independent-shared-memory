#!/bin/sh
set -eu
umask 077

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python="$project_dir/.venv/bin/python"
basic_memory="$project_dir/.venv/bin/basic-memory"
store="$HOME/SharedMemory"

if [ ! -x "$python" ] || [ ! -x "$basic_memory" ]; then
  echo "Set up the repository environment as described in README.md first." >&2
  exit 1
fi

mkdir "$store"
mkdir -p "$store/state" "$store/observations" \
  "$store/notes/personal" "$store/notes/projects/example"
: > "$store/state/.bmignore"
: > "$store/observations/observations.jsonl"

"$python" - "$store" <<'PY'
import json
import sys
from pathlib import Path

store = Path(sys.argv[1])
config = {
    "projects": {
        "personal": {"path": str(store / "notes/personal"), "mode": "local"},
        "example": {"path": str(store / "notes/projects/example"), "mode": "local"},
    },
    "default_project": "personal",
    "database_backend": "sqlite",
    "default_search_type": "hybrid",
    "semantic_embedding_provider": "fastembed",
    "auto_update": False,
    "logfire_enabled": False,
}
(store / "state/config.json").write_text(json.dumps(config, indent=2) + "\n")
PY

BASIC_MEMORY_CONFIG_DIR="$store/state" BASIC_MEMORY_FORCE_LOCAL=true \
  exec "$basic_memory" project list --local
