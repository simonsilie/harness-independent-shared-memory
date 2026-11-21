"""Configuration shared by the approval gate and owner CLI."""

import json
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError, field_validator

from . import ProposalError


def _expanduser(value: Any) -> Any:
    return Path(value).expanduser() if isinstance(value, (str, Path)) else value


class Config(BaseModel):
    model_config = ConfigDict(frozen=True)

    native_command: list[str] = Field(min_length=1)
    proposals_dir: Annotated[Path, BeforeValidator(_expanduser)]
    audit_log: Annotated[Path, BeforeValidator(_expanduser)]
    ttl_hours: int = Field(default=24, gt=0)
    env: dict[str, str] | None = None

    @field_validator("native_command")
    @classmethod
    def expand_native_executable(cls, command: list[str]) -> list[str]:
        if command[0].startswith("~"):
            return [str(Path(command[0]).expanduser()), *command[1:]]
        return command


def load_config(path: Path) -> Config:
    try:
        return Config.model_validate(json.loads(path.read_text()))
    except ValidationError as error:
        raise ProposalError(f"Invalid config {path}: {error}") from error
