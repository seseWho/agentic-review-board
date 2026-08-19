from importlib.metadata import version


def test_installed_package_version() -> None:
    assert version("agentic-review-board") == "0.1.0"
