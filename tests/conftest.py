import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.path.name.endswith("_integration.py") or item.name.startswith("test_integration_"):
            item.add_marker(pytest.mark.integration)
