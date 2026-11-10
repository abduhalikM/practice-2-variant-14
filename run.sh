#!/usr/bin/env sh
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then
    exec .venv/bin/python -B -m src.server "$@"
fi
exec python3 -B -m src.server "$@"
