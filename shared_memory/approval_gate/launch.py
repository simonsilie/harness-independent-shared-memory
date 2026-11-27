"""Start the model-free native Basic Memory MCP server, directly or behind the approval gate."""

import os
from pathlib import Path

import configargparse

from . import ProposalError
from .basic_memory_api import BasicMemoryConfig
from .config import Config, add_config_argument, load_config
from .proxy import run_proxy

# ADR 0007: these override the configuration so the store never uses a model or external service.
MODEL_FREE_ENV = {
    "BASIC_MEMORY_FORCE_LOCAL": "true",
    "BASIC_MEMORY_SEMANTIC_SEARCH_ENABLED": "false",
    "BASIC_MEMORY_AUTO_UPDATE": "false",
    "BASIC_MEMORY_LOGFIRE_ENABLED": "false",
    "WATCHFILES_FORCE_POLLING": "true",
}


def prepare_launch(argv: list[str] | None, description: str) -> tuple[Config, Path]:
    parser = configargparse.ArgumentParser(description=description)
    add_config_argument(parser)
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        config = load_config(args.config)
    except (OSError, ProposalError) as error:
        parser.error(str(error))
    env = (config.env or {}) | MODEL_FREE_ENV
    state = env.get("BASIC_MEMORY_CONFIG_DIR")
    if state is None or not (Path(state).expanduser() / "config.json").is_file():
        parser.error(f"Shared memory is not configured at {state}")
    if "semantic_search_enabled" not in BasicMemoryConfig.model_fields:
        parser.error("Shared memory requires the semantic-disable patch; reapply it before connecting.")
    return config.model_copy(update={"env": env}), args.config


def mcp_main(argv: list[str] | None = None) -> int:
    config, _ = prepare_launch(argv, "Start the model-free native Basic Memory MCP server.")
    os.execvpe(config.native_command[0], config.native_command, os.environ | (config.env or {}))


def gate_main(argv: list[str] | None = None) -> int:
    config, path = prepare_launch(argv, "Start the approval gate in front of the model-free native server.")
    return run_proxy(config, path)
