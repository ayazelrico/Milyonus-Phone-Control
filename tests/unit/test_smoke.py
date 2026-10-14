"""Every workspace package imports and reports the same version (A0.01)."""

import importlib

import pytest

PACKAGES = [
    "mphone_protocol",
    "mphone_core",
    "mphone_backends",
    "mphone_cli",
    "mphone_mcp",
    "mphone_node",
    "mphone_gateway",
    "mphone_runner",
    "mphone_sdk",
]


@pytest.mark.parametrize("name", PACKAGES)
def test_package_imports(name: str) -> None:
    module = importlib.import_module(name)
    assert module.__version__ == "0.1.0"


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    from mphone_cli.main import main

    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "mphone 0.1.0"
