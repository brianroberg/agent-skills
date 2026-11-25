"""Runs the bash suites for the cmux sidebar scripts in ``cmux/``.

Each suite in ``cmux/tests/`` takes the path of the script under test as its first
argument, prints one ``ok`` or ``FAIL`` line per case and exits with the number of
failures. The suites run the script under ``env -i`` with a fake ``cmux`` that records
its arguments, so no real cmux, Claude Code session or settings file is involved. They
need ``bash`` and ``jq`` (in ``/usr/bin``, ``/opt/homebrew/bin`` or ``/usr/local/bin``); one
fixture uses ``git`` when it is there.
"""

import subprocess
from pathlib import Path

import pytest

CMUX_DIR = Path(__file__).resolve().parent.parent / "cmux"

# script under test -> its suite in cmux/tests/
SUITES = {
    "cmux-model-status.sh": "test_cmux_model_status.sh",
    "cmux-clear-answered.sh": "test_cmux_clear_answered.sh",
    "drop-idle-notice.sh": "test_drop_idle_notice.sh",
}


def test_every_script_has_a_suite():
    assert sorted(p.name for p in CMUX_DIR.glob("*.sh")) == sorted(SUITES)


@pytest.mark.parametrize("script,suite", sorted(SUITES.items()))
def test_bash_suite_passes(script, suite):
    proc = subprocess.run(
        ["bash", str(CMUX_DIR / "tests" / suite), str(CMUX_DIR / script)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    report = proc.stdout + proc.stderr
    assert proc.returncode == 0, report
    assert "FAIL" not in report, report
    # A suite that ran no cases must not count as a pass.
    assert any(line.startswith("ok ") for line in proc.stdout.splitlines()), report
