from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROBE_TEST = PROJECT_ROOT / "tests" / "fixtures" / "live_llm_probe.py"


def run_probe(
    tmp_path: Path,
    *,
    option_enabled: bool,
    environment_enabled: bool,
    config_path: Path | None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    probe_path = tmp_path / "probe-executed"
    environment = os.environ.copy()
    environment["ARB_LIVE_LLM_PROBE_PATH"] = str(probe_path)
    environment.pop("ARB_RUN_LIVE_LLM", None)
    environment.pop("ARB_LLM_CONFIG_PATH", None)
    if environment_enabled:
        environment["ARB_RUN_LIVE_LLM"] = "1"
    if config_path is not None:
        environment["ARB_LLM_CONFIG_PATH"] = str(config_path)

    command = [sys.executable, "-m", "pytest", "-q", "-rA", str(PROBE_TEST)]
    if option_enabled:
        command.append("--run-live-llm")

    return (
        subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            check=False,
            text=True,
        ),
        probe_path,
    )


def assert_probe_skipped(result: subprocess.CompletedProcess[str], probe_path: Path) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SKIPPED [1]" in result.stdout
    assert "live LLM smoke not explicitly authorized" in result.stdout
    assert not probe_path.exists()


@pytest.mark.parametrize(
    ("option_enabled", "environment_enabled"),
    [(False, False), (True, False), (False, True)],
)
def test_live_probe_skips_without_both_authorizations(
    tmp_path: Path,
    option_enabled: bool,
    environment_enabled: bool,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    result, probe_path = run_probe(
        tmp_path,
        option_enabled=option_enabled,
        environment_enabled=environment_enabled,
        config_path=config_path,
    )

    assert_probe_skipped(result, probe_path)


def test_live_probe_skips_when_authorized_but_config_path_is_absent(
    tmp_path: Path,
) -> None:
    result, probe_path = run_probe(
        tmp_path,
        option_enabled=True,
        environment_enabled=True,
        config_path=None,
    )

    assert_probe_skipped(result, probe_path)


def test_live_probe_runs_when_both_authorizations_and_config_path_are_present(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    result, probe_path = run_probe(
        tmp_path,
        option_enabled=True,
        environment_enabled=True,
        config_path=config_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASSED tests/fixtures/live_llm_probe.py" in result.stdout
    assert probe_path.read_text(encoding="utf-8") == "executed"


def test_live_llm_marker_is_registered() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--markers"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "live_llm" in result.stdout
