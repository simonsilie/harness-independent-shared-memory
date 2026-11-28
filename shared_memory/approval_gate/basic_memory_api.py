"""The only place the approval gate imports Basic Memory internals.

These modules are not a public API and can change in any release. Keeping the
imports here lets `tests/shared_memory/approval_gate/test_basic_memory_api.py` pin the
behavior the gate relies on, so an upgrade fails there with a targeted test.
"""

from basic_memory.file_utils import ParseError, has_frontmatter, parse_frontmatter
from basic_memory.mcp.project_context_identifiers import split_project_permalink_prefix
from basic_memory.mcp.tool_params import ProjectById, parse_project
from basic_memory.runtime.storage import RUNTIME_MARKDOWN_FILE_SUFFIXES
from basic_memory.schemas.memory import memory_url_path
from basic_memory.utils import coerce_dict, generate_permalink, resolve_path_within_root, valid_project_path_value

__all__ = [
    "RUNTIME_MARKDOWN_FILE_SUFFIXES",
    "ParseError",
    "ProjectById",
    "coerce_dict",
    "generate_permalink",
    "has_frontmatter",
    "memory_url_path",
    "parse_frontmatter",
    "parse_project",
    "resolve_path_within_root",
    "split_project_permalink_prefix",
    "valid_project_path_value",
]
