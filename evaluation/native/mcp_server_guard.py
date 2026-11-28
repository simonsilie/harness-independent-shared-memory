import atexit
import importlib.abc
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any

guard_path = Path(os.environ["NATIVE_MCP_GUARD_PATH"])
events: dict[str, Any] = {"blocked_imports": [], "blocked_connections": 0}


def record():
    guard_path.write_text(json.dumps(events, indent=2) + "\n")


atexit.register(record)


class UnavailableInference(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        # Simulate missing sqlite-vec to exercise keyword-only fallback.
        if fullname.split(".")[0] in {
            "fastembed",
            "onnxruntime",
            "torch",
            "transformers",
            "litellm",
            "sqlite_vec",
        }:
            events["blocked_imports"].append(fullname)
            record()
            raise ModuleNotFoundError(f"Inference unavailable in this probe: {fullname}", name=fullname)


def block_network(event, args):
    if event == "socket.connect" and args[0].family in {socket.AF_INET, socket.AF_INET6}:
        events["blocked_connections"] += 1
        record()
        raise OSError("Network unavailable in this probe")


sys.meta_path.insert(0, UnavailableInference())
sys.addaudithook(block_network)

import basic_memory  # noqa: E402
from basic_memory.cli.main import app  # noqa: E402

events["basic_memory_source"] = basic_memory.__file__

app()
