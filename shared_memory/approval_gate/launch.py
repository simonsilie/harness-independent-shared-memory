"""Start the local Basic Memory MCP server behind the approval gate."""

import os
from pathlib import Path

import configargparse

from . import ProposalError
from .config import add_config_argument, load_config
from .proxy import run_proxy


def gate_main(argv: list[str] | None = None) -> int:
    parser = configargparse.ArgumentParser(description=__doc__)
    add_config_argument(parser)
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        config = load_config(args.config)
    except (OSError, ProposalError) as error:
        parser.error(str(error))
    state = (config.env or {}).get("BASIC_MEMORY_CONFIG_DIR")
    if state is None or not (Path(state).expanduser() / "config.json").is_file():
        parser.error(f"Shared memory is not configured at {state}")
    return run_proxy(config, args.config)


mcp_main = gate_main
