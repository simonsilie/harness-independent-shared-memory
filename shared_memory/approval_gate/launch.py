"""Start the local Basic Memory MCP server, directly or behind the approval gate."""

import os
from pathlib import Path

import configargparse

from . import ProposalError
from .basic_memory_api import BasicMemoryConfig
from .config import Config, add_config_argument, load_config
from .native import native_environment
from .proxy import run_proxy


def prepare_launch(argv: list[str] | None, description: str) -> tuple[Config, Path]:
    parser = configargparse.ArgumentParser(description=description)
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
    if "enable_mcp_project_create" not in BasicMemoryConfig.model_fields:
        parser.error("Shared memory requires the patched runtime for MCP project creation; run uv sync --locked.")
    return config, args.config


def mcp_main(argv: list[str] | None = None) -> int:
    config, _ = prepare_launch(argv, "Start the local Basic Memory MCP server.")
    os.execvpe(config.native_command[0], config.native_command, native_environment(config))


def gate_main(argv: list[str] | None = None) -> int:
    config, path = prepare_launch(argv, "Start the approval gate in front of the local Basic Memory server.")
    return run_proxy(config, path)
