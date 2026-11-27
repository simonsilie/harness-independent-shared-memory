"""Helpers shared by the evaluation runners."""

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

import configargparse


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def corpus_hashes(corpus: Path) -> dict[str, str]:
    """Hash every Markdown note directly in `corpus`, keyed by file name."""
    return {path.name: sha256_file(path) for path in corpus.glob("*.md")}


def run_directory(script: str | Path) -> Path:
    """Return a new timestamped path under the script's `runs` folder; the caller creates it."""
    return Path(script).resolve().parent / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def client_environment(*excluded_prefixes: str) -> dict[str, str]:
    """Copy the current environment without variables that start with any excluded prefix."""
    return {key: value for key, value in os.environ.items() if not key.startswith(excluded_prefixes)}


def check(condition: object, message: str) -> None:
    """Fail an evaluation check; unlike `assert`, this still runs under `python -O`."""
    if not condition:
        raise RuntimeError(message)


def runner_options(description: str, argv: list[str] | None = None) -> configargparse.Namespace:
    """Parse the mode flags shared by the Claude Code, Codex and OpenCode runners."""
    parser = configargparse.ArgumentParser(description=description)
    parser.add_argument("--verify-only", action="store_true", help="stop after verifying the live tool inventory")
    parser.add_argument("--startup", action="store_true", help="send the startup retrieval prompt instead of recall")
    parser.add_argument("--outage", action="store_true", help="replace the Basic Memory server with a failing command")
    return parser.parse_args(argv)
