# Python coding guidelines

## Error handling

- Do not swallow exceptions or fail silently. Catch exceptions only when handling them meaningfully; otherwise, let them propagate.
- Make failures visible to callers or users, preserving the original error and its context.

## Filesystem paths

- Prefer `pathlib.Path` and its methods over `os.path` and other filesystem APIs wherever possible.

## Unit testing

- All unit tests shall follow the AAA pattern: Arrange, Act, Assert.
- Unit tests shall test a unit in isolation.
  - Mock or fake external boundaries (filesystem/network/time/process), not internal implementation details.
  - Do not call real external services in unit tests.
- Prefer dependency injection over patching/mocking global functions or modules.
  - Design code so dependencies can be provided explicitly in tests.
- Test behavior and outcomes, not implementation details.
- If a test mainly validates calls on mocks, reconsider the test design and prefer asserting observable behavior.
- Tests must be deterministic and isolated.
  - Keep unit tests independent of the filesystem, network, clock, environment, and local configuration.
  - Avoid hidden dependencies on wall-clock time, timezones, randomness, or network, unless explicitly marked as integration tests.
  - Use fixed seeds for tests involving random behavior.
  - Real external service calls are only allowed in explicit integration tests.

## Running tests

Tests live in `tests/`, mirroring the active `ops/`, `build/` and `evaluation/`
responsibilities. Historical workflow tests are retained only at the archive
revision documented in [the custom-code decision](archive/custom-code-decision.md).
Pytest uses importlib collection and the repository root as its Python path,
so tests do not depend on source and test files sharing a directory.

- Name integration test files `test_*_integration.py`. In mixed suites, prefix individual integration test names with `test_integration_`.
- The repository's `tests/conftest.py` applies the `integration` marker to these names, including tests written with the standard library's `unittest`.
- Run isolated unit tests with `uv run --locked pytest -m "not integration"` and integration tests with `uv run --locked pytest -m integration`.
- Run both suites with `uv run --locked pytest`.

## Required checks

- Before finishing Python changes, run `uv run --locked ruff check .`, `uv run --locked ruff format --check .`, `uv run --locked pyrefly check`, and both pytest suites described above.
