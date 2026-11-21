import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from approval_gate.proposals import ProposalError, load_config

BASE: dict[str, Any] = {
    "native_command": ["basic-memory", "mcp", "--transport", "stdio"],
    "proposals_dir": "approvals",
    "audit_log": "audit.jsonl",
}


def write_config(tmp_path: Path, **overrides: Any) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(BASE | overrides))
    return path


def test_missing_required_field_is_a_proposal_error(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"native_command": BASE["native_command"]}))
    with pytest.raises(ProposalError, match="proposals_dir"):
        load_config(path)


@pytest.mark.parametrize(
    "overrides",
    [{"native_command": []}, {"ttl_hours": 0}, {"env": "not a mapping"}],
)
def test_invalid_values_are_proposal_errors(tmp_path: Path, overrides: dict[str, Any]) -> None:
    with pytest.raises(ProposalError):
        load_config(write_config(tmp_path, **overrides))


def test_load_config_expands_paths_and_stays_frozen(tmp_path: Path) -> None:
    config = load_config(
        write_config(tmp_path, proposals_dir="~/approvals", native_command=["~/example/bin/native-mcp", "~/arg"])
    )
    assert config.proposals_dir == Path.home() / "approvals"
    assert config.native_command == [str(Path.home() / "example/bin/native-mcp"), "~/arg"]
    with pytest.raises(ValidationError):
        config.ttl_hours = 12  # type: ignore[misc]
